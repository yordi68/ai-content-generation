import asyncio
import base64
import hashlib
import io
import json
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import wave
from pathlib import Path

import edge_tts

from runlog import log_run, requests_today
from validate import ROOT, STORYBOARD_PATH, load_storyboard, validate

ENV_PATH = ROOT / ".env"
OUT_DIR = ROOT / "outputs" / "narration"
TAIL_PAUSE_S = 0.5
MAX_ATTEMPTS = 3
TIMEOUT_S = 180
MIN_GAP_S = 20
MINUTE_RETRY_WAIT_S = 25
DAILY_LIMIT = 10
LAST_CALL = {"at": 0.0}
KEY_ID = {"value": ""}


class QuotaExhausted(Exception):
    pass


def load_api_key():
    if not ENV_PATH.exists():
        return ""
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        if line.startswith("GEMINI_API_KEY="):
            return line.split("=", 1)[1].strip()
    return ""


def cache_key(shot, voice):
    payload = {
        "narration": shot["narration"],
        "model": voice["models"][0],
        "voice": voice["voice_name"],
        "prompt_mode": "raw_text",
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def pace():
    wait = MIN_GAP_S - (time.monotonic() - LAST_CALL["at"])
    if wait > 0:
        time.sleep(wait)
    LAST_CALL["at"] = time.monotonic()


def synthesize_edge_tts(model_voice, narration):
    with tempfile.TemporaryDirectory() as tmpdir:
        mp3_path = Path(tmpdir) / "out.mp3"
        wav_path = Path(tmpdir) / "out.wav"
        asyncio.run(edge_tts.Communicate(narration, model_voice).save(str(mp3_path)))
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(mp3_path), "-ar", "24000", "-ac", "1", str(wav_path)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        return "audio/wav", wav_path.read_bytes()


def synthesize_gemini(api_key, model, voice, narration):
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is missing from .env")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    gemini_voice = voice["voice_name"] if not voice["voice_name"].endswith("Neural") else "Kore"
    body = {
        "contents": [{"parts": [{"text": narration}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": gemini_voice}}},
        },
    }
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=TIMEOUT_S) as response:
        data = json.load(response)
    part = data["candidates"][0]["content"]["parts"][0]["inlineData"]
    return part["mimeType"], base64.b64decode(part["data"])


def to_wav(mime, audio):
    if audio[:4] == b"RIFF":
        return audio
    rate = int(mime.split("rate=")[1].split(";")[0]) if "rate=" in mime else 24000
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        wav.writeframes(audio)
    return buffer.getvalue()


def wav_seconds(path):
    with wave.open(str(path), "rb") as wav:
        return wav.getnframes() / wav.getframerate()


def fetch_audio(shot, voice, api_key, name, models):
    for model in models:
        is_edge = model.endswith("Neural")
        provider = "edge-tts" if is_edge else "gemini"
        if not is_edge and requests_today(model, KEY_ID["value"]) >= DAILY_LIMIT:
            print(f"{name}: {model} has used its {DAILY_LIMIT} requests for today, skipping")
            continue
        for attempt in range(1, MAX_ATTEMPTS + 1):
            if not is_edge:
                pace()
            start = time.monotonic()
            try:
                if is_edge:
                    mime, audio = synthesize_edge_tts(model, shot["narration"])
                else:
                    mime, audio = synthesize_gemini(api_key, model, voice, shot["narration"])
                return provider, model, attempt, time.monotonic() - start, to_wav(mime, audio)
            except (urllib.error.URLError, KeyError, ValueError, RuntimeError, subprocess.CalledProcessError) as exc:
                latency = time.monotonic() - start
                detail = str(exc)
                if isinstance(exc, urllib.error.HTTPError):
                    detail = f"{exc}: {exc.read().decode('utf-8', 'ignore')[:500]}"
                log_run({
                    "stage": "narration", "provider": provider, "model": model, "key_id": KEY_ID["value"],
                    "shot": shot["id"], "attempt": attempt, "latency_s": round(latency, 2),
                    "status": "error", "error": detail,
                })
                if getattr(exc, "code", None) == 429:
                    if "per day" in detail.lower():
                        print(f"{name}: {model} is out for today, trying the next model")
                        break
                    if attempt == MAX_ATTEMPTS:
                        break
                    print(f"{name}: per-minute limit on {model}, waiting {MINUTE_RETRY_WAIT_S}s")
                    time.sleep(MINUTE_RETRY_WAIT_S)
                    continue
                if attempt == MAX_ATTEMPTS:
                    break
                print(f"{name}: attempt {attempt} on {model} failed, retrying")
                time.sleep(3 * attempt)
    raise QuotaExhausted(name)


def store(shot, voice, name, key, provider, model, attempt, latency, audio):
    wav_path = OUT_DIR / f"{name}.wav"
    meta_path = OUT_DIR / f"{name}.json"
    wav_path.write_bytes(audio)
    seconds = wav_seconds(wav_path)
    meta_path.write_text(
        json.dumps({"cache_key": key, "seconds": seconds, "model": model, "provider": provider}, indent=2),
        encoding="utf-8",
    )
    log_run({
        "stage": "narration", "provider": provider, "model": model, "key_id": KEY_ID["value"],
        "shot": shot["id"], "attempt": attempt,
        "params": {"voice": voice["voice_name"], "style": voice["style"], "seed": None},
        "latency_s": round(latency, 2), "status": "ok",
        "output": {"file": f"outputs/narration/{name}.wav", "seconds": round(seconds, 2)},
        "cost": {"free_tier": True, "list_price_usd": 0.0},
        "cache_key": key,
    })
    print(f"{name}: generated ({seconds:.2f}s, {latency:.1f}s, {model})")
    return seconds


def generate(shot, voice, api_key, state):
    name = f"shot_{shot['id']:02d}"
    meta_path = OUT_DIR / f"{name}.json"
    key = cache_key(shot, voice)
    primary = voice["models"][0]

    if (OUT_DIR / f"{name}.wav").exists() and meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if meta["cache_key"] == key:
            if meta["model"] == primary or not state["upgrade"]:
                print(f"{name}: cached ({meta['seconds']:.2f}s, {meta['model']})")
                return meta["seconds"]
            try:
                provider, model, attempt, latency, audio = fetch_audio(shot, voice, api_key, name, [primary])
                print(f"{name}: upgraded from {meta['model']} to {primary}")
                return store(shot, voice, name, key, provider, model, attempt, latency, audio)
            except QuotaExhausted:
                state["upgrade"] = False
                print(f"{name}: primary still over quota, keeping {meta['model']} clip")
                return meta["seconds"]

    models = voice["models"][:1] if state["primary_only"] else voice["models"]
    try:
        provider, model, attempt, latency, audio = fetch_audio(shot, voice, api_key, name, models)
    except QuotaExhausted:
        raise SystemExit(f"{name}: every model is out for today; run again tomorrow, finished shots are cached")
    return store(shot, voice, name, key, provider, model, attempt, latency, audio)


def main():
    board = load_storyboard()
    errors = validate(board)
    if errors:
        for error in errors:
            print(f"ERROR {list(error.path)}: {error.message}")
        return 1

    api_key = load_api_key()
    KEY_ID["value"] = hashlib.sha256(api_key.encode("utf-8")).hexdigest()[:8] if api_key else "nokey"
    voice = board["voice"]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    state = {"upgrade": True, "primary_only": "--primary-only" in sys.argv}

    for shot in board["shots"]:
        seconds = generate(shot, voice, api_key, state)
        shot["duration_s"] = round(seconds / voice["tempo"] + TAIL_PAUSE_S, 1)

    errors = validate(board)
    if errors:
        for error in errors:
            print(f"ERROR {list(error.path)}: {error.message}")
        return 1

    STORYBOARD_PATH.write_text(json.dumps(board, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    total = sum(shot["duration_s"] for shot in board["shots"])
    print(f"storyboard.json updated: total {total:.1f}s across {len(board['shots'])} shots")
    return 0


if __name__ == "__main__":
    sys.exit(main())
