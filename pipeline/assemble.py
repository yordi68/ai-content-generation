import json
import re
import subprocess
import sys
import textwrap
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from runlog import log_run
from validate import ROOT, load_storyboard, validate

NARRATION_DIR = ROOT / "outputs" / "narration"
MUSIC_PATH = ROOT / "outputs" / "music" / "score.wav"
SHOTS_DIR = ROOT / "outputs" / "shots"
BUILD_DIR = ROOT / "outputs" / "build"
OUT_DIR = ROOT / "outputs"
FPS = 24
END_CARD_DURATION_S = 2.6
ASPECT_DIMS = {
    "9:16": (720, 1280),
    "16:9": (1280, 720),
}


def load_font(size):
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/Library/Fonts/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size=size)
            except OSError:
                continue
    return ImageFont.load_default()


def split_subtitle_cues(text, duration_s):
    """Split subtitles longer than 85 chars into two timed cues so each cue stays <= 3 lines."""
    if len(text) <= 85:
        return [(text, 0.0, duration_s)]
    if ". " in text:
        first, second = text.split(". ", 1)
        first = first + "."
    else:
        words = text.split()
        mid = len(words) // 2
        first = " ".join(words[:mid])
        second = " ".join(words[mid:])
    ratio = max(0.30, min(0.70, len(first) / max(1, len(text))))
    split_t = round(duration_s * ratio, 2)
    return [(first, 0.0, split_t), (second, split_t, duration_s)]


def render_subtitle_overlay(text, width, height, out_path):
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    is_vertical = height > width
    base_chars = 36 if is_vertical else 54
    chosen = None
    for size in (28, 25, 22, 20):
        font = load_font(size)
        max_chars = max(18, int(base_chars * 28 / size))
        lines = textwrap.wrap(text, width=max_chars)
        if len(lines) <= 3:
            chosen = (font, lines)
            break
    if chosen is None:
        font = load_font(20)
        chosen = (font, textwrap.wrap(text, width=max(18, int(base_chars * 28 / 20)))[:3])
    font, lines = chosen

    line_gap = 8
    bboxes = [draw.textbbox((0, 0), line, font=font) for line in lines]
    line_heights = [b[3] - b[1] for b in bboxes]
    line_widths = [b[2] - b[0] for b in bboxes]

    block_w = max(line_widths) if line_widths else 0
    block_h = sum(line_heights) + line_gap * max(0, len(lines) - 1)

    bottom_margin = int(height * 0.16) if is_vertical else int(height * 0.09)
    box_y1 = height - bottom_margin - block_h
    box_x1 = (width - block_w) // 2
    pad_x, pad_y = 22, 14

    draw.rounded_rectangle(
        [box_x1 - pad_x, box_y1 - pad_y, box_x1 + block_w + pad_x, box_y1 + block_h + pad_y],
        radius=14,
        fill=(15, 15, 22, 195),
    )

    curr_y = box_y1
    for line, lw, lh in zip(lines, line_widths, line_heights):
        lx = (width - lw) // 2
        draw.text((lx, curr_y), line, font=font, fill=(255, 252, 240, 255))
        curr_y += lh + line_gap

    img.save(out_path, "PNG")


def render_end_card_image(board, width, height, out_path):
    img = Image.new("RGB", (width, height), (20, 22, 34))
    draw = ImageDraw.Draw(img)

    is_vertical = height > width
    title_font = load_font(34 if is_vertical else 40)
    sub_font = load_font(23 if is_vertical else 26)
    small_font = load_font(17 if is_vertical else 19)

    active_voice = board["voice"]["models"][0]
    provider_label = {"edge-tts": "Edge TTS", "gemini": "Gemini TTS"}.get(
        board["voice"].get("provider"), "TTS"
    )

    entries = [(board["title"], title_font, (255, 236, 179), 18)]
    if board.get("title_local"):
        entries.append((board["title_local"], sub_font, (240, 240, 245), 14))
    entries.extend(
        [
            ("Made with AI", sub_font, (255, 210, 120), 18),
            (f"Narrated with {active_voice} ({provider_label})", small_font, (190, 195, 210), 8),
            ("Illustrated with FLUX.1-schnell • Assembled with FFmpeg", small_font, (190, 195, 210), 8),
        ]
    )

    rendered = []
    for text, font, color, gap in entries:
        font_size = getattr(font, "size", 20)
        max_chars = max(18, int(width / (font_size * 0.56)))
        for part in textwrap.wrap(text, width=max_chars) or [text]:
            rendered.append((part, font, color, gap))

    bboxes = [draw.textbbox((0, 0), text, font=font) for text, font, _, _ in rendered]
    heights = [b[3] - b[1] for b in bboxes]
    total_h = sum(heights) + sum(gap for *_, gap in rendered) - rendered[-1][3]
    curr_y = max(24, (height - total_h) // 2)

    for (text, font, color, gap), bbox, line_h in zip(rendered, bboxes, heights):
        text_w = bbox[2] - bbox[0]
        draw.text(((width - text_w) // 2, curr_y - bbox[1]), text, font=font, fill=color)
        curr_y += line_h + gap

    img.save(out_path, "PNG")


def build_master_audio(board):
    tempo = board["voice"].get("tempo", 1.0)
    seg_paths = []

    for shot in board["shots"]:
        shot_id = shot["id"]
        dur = shot["duration_s"]
        raw_wav = NARRATION_DIR / f"shot_{shot_id:02d}.wav"
        if not raw_wav.exists():
            raise SystemExit(f"Missing narration clip: {raw_wav}")
        seg_wav = BUILD_DIR / f"voice_seg_{shot_id:02d}.wav"
        af = (
            f"atempo={tempo:.2f},"
            f"aformat=sample_fmts=s16:sample_rates=44100:channel_layouts=stereo,"
            f"apad=whole_dur={dur:.2f}"
        )
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(raw_wav), "-af", af, "-t", f"{dur:.2f}", str(seg_wav)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        seg_paths.append(seg_wav)

    end_silence = BUILD_DIR / "voice_end_silence.wav"
    subprocess.run(
        [
            "ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
            "-t", f"{END_CARD_DURATION_S:.2f}", "-c:a", "pcm_s16le", str(end_silence),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    seg_paths.append(end_silence)

    concat_list = BUILD_DIR / "voice_concat.txt"
    concat_list.write_text(
        "\n".join(f"file '{p.resolve()}'" for p in seg_paths) + "\n",
        encoding="utf-8",
    )
    voice_stem = BUILD_DIR / "voice_stem.wav"
    subprocess.run(
        [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list),
            "-c:a", "pcm_s16le", str(voice_stem),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )

    total_dur = round(sum(s["duration_s"] for s in board["shots"]) + END_CARD_DURATION_S, 1)
    premix_audio = BUILD_DIR / "premix_ducked.wav"
    master_audio = BUILD_DIR / "master_audio.wav"

    # Step 1: Sidechain compression ducking
    duck_filter = (
        "[0:a]asplit=2[vo_sc][vo_mix];"
        "[1:a]volume=0.55[music_pre];"
        "[music_pre][vo_sc]sidechaincompress=threshold=0.02:ratio=6:attack=300:release=1500[music_ducked];"
        "[vo_mix][music_ducked]amix=inputs=2:duration=first:dropout_transition=0:weights='1.25 0.75'[aout]"
    )
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-i", str(voice_stem),
            "-stream_loop", "-1", "-i", str(MUSIC_PATH),
            "-filter_complex", duck_filter,
            "-map", "[aout]",
            "-t", f"{total_dur:.2f}",
            "-c:a", "pcm_s16le",
            str(premix_audio),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )

    # Step 2: Two-pass EBU R128 loudness normalization (-14.0 LUFS, -1.0 dBTP)
    pass1 = subprocess.run(
        [
            "ffmpeg", "-y", "-i", str(premix_audio),
            "-af", "loudnorm=I=-14:TP=-1.0:LRA=11:print_format=json",
            "-f", "null", "-",
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    match = re.search(r"\{\s*\"input_i\"[\s\S]*?\}", pass1.stderr)
    loud_stats = json.loads(match.group(0)) if match else {}

    if loud_stats:
        ln_pass2 = (
            f"loudnorm=I=-14:TP=-1.0:LRA=11:"
            f"measured_I={loud_stats['input_i']}:"
            f"measured_TP={loud_stats['input_tp']}:"
            f"measured_LRA={loud_stats['input_lra']}:"
            f"measured_thresh={loud_stats['input_thresh']}:"
            f"offset={loud_stats['target_offset']}:linear=true"
        )
    else:
        ln_pass2 = "loudnorm=I=-14:TP=-1.0:LRA=11"

    subprocess.run(
        [
            "ffmpeg", "-y", "-i", str(premix_audio),
            "-af", ln_pass2,
            "-ar", "44100", "-ac", "2",
            "-c:a", "pcm_s16le",
            str(master_audio),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    return master_audio, total_dur, loud_stats


def overlay_subtitles_on_video(input_args, shot, width, height, tag_prefix, out_mp4, preset="fast"):
    shot_id = shot["id"]
    dur = shot["duration_s"]
    cues = split_subtitle_cues(shot["subtitle"], dur)
    png_inputs = []
    filter_parts = []
    last_label = "[0:v]"

    for idx, (cue_text, t0, t1) in enumerate(cues, start=1):
        sub_png = BUILD_DIR / f"{tag_prefix}_sub_{shot_id:02d}_part{idx}.png"
        render_subtitle_overlay(cue_text, width, height, sub_png)
        png_inputs.extend(["-i", str(sub_png)])
        next_label = f"[v{idx}]"
        filter_parts.append(
            f"{last_label}[{idx}:v]overlay=0:0:enable='between(t,{t0:.2f},{t1:.2f})'{next_label}"
        )
        last_label = next_label

    filter_complex = ";".join(filter_parts) + f";{last_label}format=yuv420p[vout]"
    cmd = (
        ["ffmpeg", "-y"]
        + input_args
        + png_inputs
        + [
            "-filter_complex", filter_complex,
            "-map", "[vout]",
            "-t", f"{dur:.2f}",
            "-c:v", "libx264", "-preset", preset, "-crf", "20", "-an",
            str(out_mp4),
        ]
    )
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def build_radio_cut(board, master_audio, total_dur):
    radio_path = OUT_DIR / "radio_cut.mp4"
    width, height = ASPECT_DIMS["16:9"]
    seg_clips = []

    for shot in board["shots"]:
        shot_id = shot["id"]
        dur = shot["duration_s"]
        seg_mp4 = BUILD_DIR / f"radio_seg_{shot_id:02d}.mp4"
        input_args = ["-f", "lavfi", "-i", f"color=c=black:s={width}x{height}:r={FPS}:d={dur:.2f}"]
        overlay_subtitles_on_video(input_args, shot, width, height, "radio", seg_mp4, preset="ultrafast")
        seg_clips.append(seg_mp4)

    end_png = BUILD_DIR / "end_card_16x9.png"
    render_end_card_image(board, width, height, end_png)
    end_mp4 = BUILD_DIR / "radio_end.mp4"
    subprocess.run(
        [
            "ffmpeg", "-y", "-loop", "1", "-i", str(end_png),
            "-t", f"{END_CARD_DURATION_S:.2f}",
            "-vf", f"fps={FPS},format=yuv420p",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "22", "-an",
            str(end_mp4),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    seg_clips.append(end_mp4)

    concat_txt = BUILD_DIR / "radio_concat.txt"
    concat_txt.write_text(
        "\n".join(f"file '{p.resolve()}'" for p in seg_clips) + "\n",
        encoding="utf-8",
    )
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0", "-i", str(concat_txt),
            "-i", str(master_audio),
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-t", f"{total_dur:.2f}",
            "-movflags", "+faststart",
            str(radio_path),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    return radio_path


def build_aspect_film(board, aspect, master_audio, total_dur):
    aspect_tag = aspect.replace(":", "x")
    width, height = ASPECT_DIMS[aspect]
    seg_clips = []

    for shot in board["shots"]:
        shot_id = shot["id"]
        shot_mp4 = SHOTS_DIR / f"shot_{shot_id:02d}_{aspect_tag}.mp4"
        if not shot_mp4.exists():
            raise SystemExit(f"Missing moving shot: {shot_mp4}")

        sub_mp4 = BUILD_DIR / f"sub_shot_{shot_id:02d}_{aspect_tag}.mp4"
        overlay_subtitles_on_video(["-i", str(shot_mp4)], shot, width, height, aspect_tag, sub_mp4, preset="fast")
        seg_clips.append(sub_mp4)

    end_png = BUILD_DIR / f"end_card_{aspect_tag}.png"
    render_end_card_image(board, width, height, end_png)
    end_mp4 = BUILD_DIR / f"end_card_{aspect_tag}.mp4"
    subprocess.run(
        [
            "ffmpeg", "-y", "-loop", "1", "-i", str(end_png),
            "-t", f"{END_CARD_DURATION_S:.2f}",
            "-vf", f"fps={FPS},fade=t=in:st=0:d=0.4,format=yuv420p",
            "-c:v", "libx264", "-preset", "fast", "-crf", "20", "-an",
            str(end_mp4),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    seg_clips.append(end_mp4)

    concat_txt = BUILD_DIR / f"film_concat_{aspect_tag}.txt"
    concat_txt.write_text(
        "\n".join(f"file '{p.resolve()}'" for p in seg_clips) + "\n",
        encoding="utf-8",
    )
    out_mp4 = OUT_DIR / f"film_{aspect_tag}.mp4"
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0", "-i", str(concat_txt),
            "-i", str(master_audio),
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-t", f"{total_dur:.2f}",
            "-movflags", "+faststart",
            str(out_mp4),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    return out_mp4


def main():
    board = load_storyboard()
    errors = validate(board)
    if errors:
        for error in errors:
            print(f"ERROR {list(error.path)}: {error.message}")
        return 1

    BUILD_DIR.mkdir(parents=True, exist_ok=True)

    start = time.monotonic()
    master_audio, total_dur, loud_stats = build_master_audio(board)
    radio_path = build_radio_cut(board, master_audio, total_dur)
    print(f"assemble: radio_cut.mp4 ready ({total_dur:.1f}s)")

    outputs = {"radio_cut": str(radio_path.relative_to(ROOT))}
    for aspect in board["aspect_ratios"]:
        film_path = build_aspect_film(board, aspect, master_audio, total_dur)
        outputs[aspect] = str(film_path.relative_to(ROOT))
        print(f"assemble: {film_path.name} ready ({total_dur:.1f}s)")

    latency = time.monotonic() - start
    log_run(
        {
            "stage": "assemble",
            "provider": "local-ffmpeg",
            "model": "ffmpeg-sidechain-2pass-loudnorm-overlay",
            "params": {
                "aspect_ratios": board["aspect_ratios"],
                "loudnorm_target_lufs": -14.0,
                "true_peak_db": -1.0,
                "loudnorm_pass1_measured": {
                    "input_i": loud_stats.get("input_i"),
                    "input_tp": loud_stats.get("input_tp"),
                    "input_lra": loud_stats.get("input_lra"),
                },
                "sidechain": {"threshold": 0.02, "ratio": 6, "attack_ms": 300, "release_ms": 1500},
                "end_card_s": END_CARD_DURATION_S,
            },
            "latency_s": round(latency, 2),
            "status": "ok",
            "output": {"files": outputs, "seconds": round(total_dur, 1)},
            "cost": {"free_tier": True, "list_price_usd": 0.0},
        }
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
