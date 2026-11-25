import hashlib
import json
import subprocess
import sys
import time

from runlog import log_run
from validate import ROOT, load_storyboard, validate

KEYFRAMES_DIR = ROOT / "outputs" / "keyframes"
WAN_DIR = ROOT / "outputs" / "wan"
OUT_DIR = ROOT / "outputs" / "shots"
FPS = 24
ASPECT_DIMS = {
    "9:16": (720, 1280),
    "16:9": (1280, 720),
}


def file_sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cache_key(img_hash, motion, duration_s, aspect):
    payload = {
        "img_hash": img_hash,
        "motion": motion,
        "duration_s": round(duration_s, 2),
        "aspect": aspect,
        "fps": FPS,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def build_zoompan_filter(motion_type, duration_s, width, height):
    frames = max(1, int(round(duration_s * FPS)))
    # Pre-scale image slightly higher to avoid jitter during zoompan
    pre_w = width * 2
    pre_h = height * 2
    crop_filter = (
        f"scale={pre_w}:{pre_h}:force_original_aspect_ratio=increase,"
        f"crop={pre_w}:{pre_h}"
    )

    if motion_type == "push-in":
        z_expr = f"1.0+0.15*(on/{frames})"
        x_expr = "iw/2-(iw/zoom/2)"
        y_expr = "ih/2-(ih/zoom/2)"
    elif motion_type == "pull-out":
        z_expr = f"1.15-0.15*(on/{frames})"
        x_expr = "iw/2-(iw/zoom/2)"
        y_expr = "ih/2-(ih/zoom/2)"
    elif motion_type == "pan-right":
        z_expr = "1.14"
        x_expr = f"(iw-iw/zoom)*(on/{frames})"
        y_expr = "ih/2-(ih/zoom/2)"
    elif motion_type == "pan-left":
        z_expr = "1.14"
        x_expr = f"(iw-iw/zoom)*(1-on/{frames})"
        y_expr = "ih/2-(ih/zoom/2)"
    else:
        z_expr = "1.0"
        x_expr = "iw/2-(iw/zoom/2)"
        y_expr = "ih/2-(ih/zoom/2)"

    zp = (
        f"zoompan=z='{z_expr}':x='{x_expr}':y='{y_expr}':"
        f"d={frames}:s={width}x{height}:fps={FPS}"
    )
    return f"{crop_filter},{zp},format=yuv420p"


def render_shot(shot, aspect):
    shot_id = shot["id"]
    duration_s = shot.get("duration_s") or 6.0
    motion_type = shot["motion"]["type"]
    aspect_tag = aspect.replace(":", "x")
    width, height = ASPECT_DIMS[aspect]

    keyframe_path = KEYFRAMES_DIR / f"shot_{shot_id:02d}.jpg"
    if not keyframe_path.exists():
        raise SystemExit(f"Missing keyframe: {keyframe_path}. Run pipeline/keyframes.py first.")

    wan_path = WAN_DIR / f"shot_{shot_id:02d}.mp4"
    source_path = wan_path if wan_path.exists() else keyframe_path
    src_hash = file_sha256(source_path)

    name = f"shot_{shot_id:02d}_{aspect_tag}"
    mp4_path = OUT_DIR / f"{name}.mp4"
    meta_path = OUT_DIR / f"{name}.json"
    key = cache_key(src_hash, shot["motion"], duration_s, aspect)

    if mp4_path.exists() and meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if meta.get("cache_key") == key:
            print(f"{name}: cached ({duration_s}s, {meta['method']})")
            return

    start = time.monotonic()
    if wan_path.exists():
        method = "wan-2.2-ti2v-5b"
        vf = (
            f"scale={width}:{height}:force_original_aspect_ratio=increase,"
            f"crop={width}:{height},fps={FPS},format=yuv420p"
        )
        cmd = [
            "ffmpeg", "-y", "-stream_loop", "-1", "-i", str(wan_path),
            "-t", f"{duration_s:.2f}", "-vf", vf,
            "-c:v", "libx264", "-preset", "fast", "-crf", "20", "-an",
            str(mp4_path),
        ]
    else:
        method = f"ffmpeg-zoompan-{motion_type}"
        vf = build_zoompan_filter(motion_type, duration_s, width, height)
        cmd = [
            "ffmpeg", "-y", "-i", str(keyframe_path),
            "-vf", vf, "-t", f"{duration_s:.2f}",
            "-c:v", "libx264", "-preset", "fast", "-crf", "20", "-an",
            str(mp4_path),
        ]

    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    latency = time.monotonic() - start

    meta_path.write_text(
        json.dumps(
            {
                "cache_key": key,
                "shot_id": shot_id,
                "aspect": aspect,
                "duration_s": duration_s,
                "method": method,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    log_run(
        {
            "stage": "shots",
            "provider": "local-ffmpeg" if not wan_path.exists() else "kaggle-wan",
            "model": method,
            "shot": shot_id,
            "params": {"aspect": aspect, "motion": motion_type, "duration_s": duration_s},
            "latency_s": round(latency, 2),
            "status": "ok",
            "output": {"file": f"outputs/shots/{name}.mp4", "seconds": duration_s},
            "cost": {"free_tier": True, "list_price_usd": 0.0},
            "cache_key": key,
        }
    )
    print(f"{name}: rendered ({duration_s}s, {latency:.1f}s, {method})")


def main():
    board = load_storyboard()
    errors = validate(board)
    if errors:
        for error in errors:
            print(f"ERROR {list(error.path)}: {error.message}")
        return 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for aspect in board["aspect_ratios"]:
        for shot in board["shots"]:
            render_shot(shot, aspect)

    print("shots: all moving shots rendered for", ", ".join(board["aspect_ratios"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
