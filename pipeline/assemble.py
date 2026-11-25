import json
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
    ]
    for path in candidates:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size=size)
            except OSError:
                continue
    return ImageFont.load_default()


def render_subtitle_overlay(text, width, height, out_path):
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    is_vertical = height > width
    font_size = 30 if is_vertical else 28
    max_chars = 34 if is_vertical else 54
    font = load_font(font_size)

    lines = textwrap.wrap(text, width=max_chars)
    line_gap = 8
    bboxes = [draw.textbbox((0, 0), line, font=font) for line in lines]
    line_heights = [b[3] - b[1] for b in bboxes]
    line_widths = [b[2] - b[0] for b in bboxes]

    block_w = max(line_widths) if line_widths else 0
    block_h = sum(line_heights) + line_gap * max(0, len(lines) - 1)

    # Safe area positioning (above bottom UI controls on 9:16 vertical feeds)
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


def render_end_card_image(title, width, height, out_path):
    img = Image.new("RGB", (width, height), (20, 22, 34))
    draw = ImageDraw.Draw(img)

    title_font = load_font(38 if width >= height else 34)
    sub_font = load_font(26 if width >= height else 24)
    small_font = load_font(20 if width >= height else 18)

    lines = [
        (title, title_font, (255, 236, 179)),
        ("ኮኮቤ • Kokobe", sub_font, (240, 240, 245)),
        ("Made with AI", sub_font, (255, 210, 120)),
        ("Narrated with Gemini TTS • Illustrated with FLUX.1", small_font, (190, 195, 210)),
        ("Assembled with FFmpeg from storyboard.json", small_font, (190, 195, 210)),
    ]

    total_h = len(lines) * 52
    curr_y = (height - total_h) // 2
    for text, font, color in lines:
        bbox = draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        draw.text(((width - tw) // 2, curr_y), text, font=font, fill=color)
        curr_y += th + 24

    img.save(out_path, "PNG")


def build_master_audio(board):
    tempo = board["voice"].get("tempo", 1.08)
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

    # Silence segment for end card
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

    total_dur = sum(s["duration_s"] for s in board["shots"]) + END_CARD_DURATION_S
    master_audio = BUILD_DIR / "master_audio.wav"

    # Sidechain ducking (Appendix B: threshold=0.02, ratio=6, attack=300ms, release=1500ms)
    # followed by EBU R128 loudness normalization to -14 LUFS, -1.0 dB true peak
    filter_complex = (
        "[0:a]asplit=2[vo_sc][vo_mix];"
        "[1:a]volume=0.55[music_pre];"
        "[music_pre][vo_sc]sidechaincompress=threshold=0.02:ratio=6:attack=300:release=1500[music_ducked];"
        "[vo_mix][music_ducked]amix=inputs=2:duration=first:dropout_transition=0:weights='1.25 0.75',"
        "loudnorm=I=-14:TP=-1.0:LRA=11[aout]"
    )
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-i", str(voice_stem),
            "-stream_loop", "-1", "-i", str(MUSIC_PATH),
            "-filter_complex", filter_complex,
            "-map", "[aout]",
            "-t", f"{total_dur:.2f}",
            "-c:a", "pcm_s16le",
            str(master_audio),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    return master_audio, total_dur


def build_radio_cut(board, master_audio, total_dur):
    radio_path = OUT_DIR / "radio_cut.mp4"
    width, height = ASPECT_DIMS["16:9"]
    seg_clips = []

    for shot in board["shots"]:
        shot_id = shot["id"]
        dur = shot["duration_s"]
        sub_png = BUILD_DIR / f"radio_sub_{shot_id:02d}.png"
        render_subtitle_overlay(shot["subtitle"], width, height, sub_png)
        seg_mp4 = BUILD_DIR / f"radio_seg_{shot_id:02d}.mp4"
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-f", "lavfi", "-i", f"color=c=black:s={width}x{height}:r={FPS}:d={dur:.2f}",
                "-i", str(sub_png),
                "-filter_complex", "[0:v][1:v]overlay=0:0,format=yuv420p",
                "-t", f"{dur:.2f}",
                "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23", "-an",
                str(seg_mp4),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        seg_clips.append(seg_mp4)

    end_png = BUILD_DIR / "end_card_16x9.png"
    render_end_card_image(board["title"], width, height, end_png)
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
        dur = shot["duration_s"]
        shot_mp4 = SHOTS_DIR / f"shot_{shot_id:02d}_{aspect_tag}.mp4"
        if not shot_mp4.exists():
            raise SystemExit(f"Missing moving shot: {shot_mp4}")

        sub_png = BUILD_DIR / f"sub_{shot_id:02d}_{aspect_tag}.png"
        render_subtitle_overlay(shot["subtitle"], width, height, sub_png)
        sub_mp4 = BUILD_DIR / f"sub_shot_{shot_id:02d}_{aspect_tag}.mp4"

        subprocess.run(
            [
                "ffmpeg", "-y",
                "-i", str(shot_mp4),
                "-i", str(sub_png),
                "-filter_complex", "[0:v][1:v]overlay=0:0,format=yuv420p",
                "-t", f"{dur:.2f}",
                "-c:v", "libx264", "-preset", "fast", "-crf", "20", "-an",
                str(sub_mp4),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        seg_clips.append(sub_mp4)

    end_png = BUILD_DIR / f"end_card_{aspect_tag}.png"
    render_end_card_image(board["title"], width, height, end_png)
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
    master_audio, total_dur = build_master_audio(board)
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
            "model": "ffmpeg-sidechain-loudnorm-overlay",
            "params": {
                "aspect_ratios": board["aspect_ratios"],
                "loudnorm_target_lufs": -14.0,
                "true_peak_db": -1.0,
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
