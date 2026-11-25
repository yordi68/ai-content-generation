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


def cache_key(cue, duration_s):
    payload = {"cue": cue, "duration_s": round(duration_s, 1)}
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def synthesize_pentatonic_lullaby(duration_s, wav_path):
    """Generate a gentle Tizita-inspired warm ambient pentatonic harp/pad underscore."""
    total_samples = int(duration_s * SAMPLE_RATE)
    # Tizita major pentatonic frequencies (C4, D4, E4, G4, A4, C5)
    notes = [261.63, 293.66, 329.63, 392.00, 440.00, 523.25]
    pattern = [0, 2, 3, 4, 3, 2, 1, 0, 2, 4, 5, 4, 3, 2, 1, 0]
    note_len = 2.2  # seconds per plucked arpeggio note

    frames = bytearray()
    for i in range(total_samples):
        t = i / SAMPLE_RATE
        # Warm low pad drone (C3 + G3)
        pad = 0.08 * math.sin(2 * math.pi * 130.81 * t) + 0.05 * math.sin(2 * math.pi * 196.00 * t)
        # Slow breathing LFO on pad
        pad *= 0.75 + 0.25 * math.sin(2 * math.pi * 0.12 * t)

        # Gentle plucked krar/harp note with exponential decay
        idx = int(t / note_len) % len(pattern)
        note_t = t % note_len
        freq = notes[pattern[idx]]
        env = math.exp(-2.4 * note_t) * min(1.0, note_t / 0.03)
        pluck = env * (
            0.12 * math.sin(2 * math.pi * freq * note_t)
            + 0.04 * math.sin(2 * math.pi * freq * 2 * note_t)
            + 0.015 * math.sin(2 * math.pi * freq * 3 * note_t)
        )

        # Fade in first 1.5s, fade out last 2.5s
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
    cues = board.get("music") or [
        {
            "id": "cue_01_lullaby",
            "start_shot": 1,
            "end_shot": len(board["shots"]),
            "caption": "gentle warm Ethiopian krar and soft ambient pad lullaby",
        }
    ]
    cue = cues[0]
    shot_total = sum((s.get("duration_s") or 6.0) for s in board["shots"])
    duration_s = round(shot_total + 3.0, 1)

    wav_path = OUT_DIR / "score.wav"
    meta_path = OUT_DIR / "score.json"
    ace_override = OUT_DIR / "ace_step_chosen.wav"
    key = cache_key(cue, duration_s)

    if ace_override.exists():
        wav_path.write_bytes(ace_override.read_bytes())
        print(f"music: using ACE-Step 1.5 chosen track ({ace_override.name})")
        return 0

    if wav_path.exists() and meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if meta.get("cache_key") == key:
            print(f"music: cached ({meta['duration_s']}s, {meta['model']})")
            return 0

    start = time.monotonic()
    synthesize_pentatonic_lullaby(duration_s, wav_path)
    latency = time.monotonic() - start
    model_name = "local-tizita-lullaby-synth-v1"

    meta_path.write_text(
        json.dumps(
            {
                "cache_key": key,
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
    print(f"music: generated ({duration_s}s, {latency:.2f}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
