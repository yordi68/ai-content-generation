import hashlib
import json
import math
import struct
import sys
import time
import wave

from runlog import log_run
from validate import ROOT, load_storyboard, validate

OUT_DIR = ROOT / "outputs" / "music"
SAMPLE_RATE = 44100
CODE_VERSION = "music-v2"


def cache_key(cue, duration_s, source_tag):
    payload = {
        "code_version": CODE_VERSION,
        "cue": cue,
        "duration_s": round(duration_s, 1),
        "source": source_tag,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def synthesize_pentatonic_lullaby(duration_s, wav_path):
    """Generate a gentle Tizita-inspired warm ambient pentatonic harp/pad underscore."""
    total_samples = int(duration_s * SAMPLE_RATE)
    notes = [261.63, 293.66, 329.63, 392.00, 440.00, 523.25]
    pattern = [0, 2, 3, 4, 3, 2, 1, 0, 2, 4, 5, 4, 3, 2, 1, 0]
    note_len = 2.2

    frames = bytearray()
    for i in range(total_samples):
        t = i / SAMPLE_RATE
        pad = 0.08 * math.sin(2 * math.pi * 130.81 * t) + 0.05 * math.sin(2 * math.pi * 196.00 * t)
        pad *= 0.75 + 0.25 * math.sin(2 * math.pi * 0.12 * t)

        idx = int(t / note_len) % len(pattern)
        note_t = t % note_len
        freq = notes[pattern[idx]]
        env = math.exp(-2.4 * note_t) * min(1.0, note_t / 0.03)
        pluck = env * (
            0.12 * math.sin(2 * math.pi * freq * note_t)
            + 0.04 * math.sin(2 * math.pi * freq * 2 * note_t)
            + 0.015 * math.sin(2 * math.pi * freq * 3 * note_t)
        )

        fade = 1.0
        if t < 1.5:
            fade = t / 1.5
        elif duration_s - t < 2.5:
            fade = max(0.0, (duration_s - t) / 2.5)

        sample = max(-0.95, min(0.95, (pad + pluck) * fade))
        pcm = int(sample * 32767)
        frames.extend(struct.pack("<hh", pcm, pcm))

    with wave.open(str(wav_path), "wb") as wav:
        wav.setnchannels(2)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)
        wav.writeframes(bytes(frames))


def main():
    board = load_storyboard()
    errors = validate(board)
    if errors:
        for error in errors:
            print(f"ERROR {list(error.path)}: {error.message}")
        return 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cue = board["music"][0]
    shot_total = sum((s.get("duration_s") or 6.0) for s in board["shots"])
    duration_s = round(shot_total + 3.0, 1)

    wav_path = OUT_DIR / "score.wav"
    meta_path = OUT_DIR / "score.json"
    ace_override = OUT_DIR / "ace_step_chosen.wav"
    source_tag = (
        f"ace-step:{hashlib.sha256(ace_override.read_bytes()).hexdigest()[:12]}"
        if ace_override.exists()
        else "local-tizita-lullaby-synth-v1"
    )
    key = cache_key(cue, duration_s, source_tag)

    if wav_path.exists() and meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if meta.get("cache_key") == key:
            print(f"music: cached ({meta['duration_s']}s, {meta['model']})")
            return 0

    start = time.monotonic()
    if ace_override.exists():
        wav_path.write_bytes(ace_override.read_bytes())
        model_name = "ace-step-1.5-override"
    else:
        synthesize_pentatonic_lullaby(duration_s, wav_path)
        model_name = "local-tizita-lullaby-synth-v1"
    latency = time.monotonic() - start

    meta_path.write_text(
        json.dumps(
            {
                "cache_key": key,
                "code_version": CODE_VERSION,
                "duration_s": duration_s,
                "model": model_name,
                "cue_id": cue["id"],
                "caption": cue["caption"],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    log_run(
        {
            "stage": "music",
            "provider": "local",
            "model": model_name,
            "params": {"cue_id": cue["id"], "caption": cue["caption"], "duration_s": duration_s, "seed": 1},
            "latency_s": round(latency, 2),
            "status": "ok",
            "output": {"file": "outputs/music/score.wav", "seconds": duration_s},
            "cost": {"free_tier": True, "list_price_usd": 0.0},
            "cache_key": key,
        }
    )
    print(f"music: generated ({duration_s}s, {latency:.2f}s, {model_name})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
