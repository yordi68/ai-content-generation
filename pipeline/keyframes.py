import base64
import hashlib
import json
import sys
import time
import urllib.error
import urllib.request

from runlog import log_run
from validate import ROOT, load_storyboard, validate

ENV_PATH = ROOT / ".env"
OUT_DIR = ROOT / "outputs" / "keyframes"
MODEL = "@cf/black-forest-labs/flux-1-schnell"
STEPS = 4
MAX_ATTEMPTS = 3
TIMEOUT_S = 120


def load_cf_credentials():
    account_id = None
    token = None
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        if line.startswith("CLOUDFLARE_ACCOUNT_ID="):
            account_id = line.split("=", 1)[1].strip()
        elif line.startswith("CLOUDFLARE_API_TOKEN="):
            token = line.split("=", 1)[1].strip()
    if not account_id or not token:
        raise SystemExit("CLOUDFLARE_ACCOUNT_ID or CLOUDFLARE_API_TOKEN is missing from .env")
    return account_id, token


def compose_shot_prompt(board, shot):
    return (
        f"{board['style_block']}. "
        f"Characters: {board['character']}. "
        f"Scene: {shot['picture']} "
        "Centered subject composition, balanced framing for both 9:16 vertical and 16:9 horizontal crops, "
        "no text, no letters, no watermark."
    )


def compose_reference_prompt(board):
    return (
        f"Character and style reference sheet: {board['style_block']}. "
        f"{board['character']}. "
        "Warm Ethiopian village setting at dusk, clear consistent facial features and clothing, "
        "centered composition, no text, no watermark."
    )


def cache_key(prompt, seed):
    payload = {"model": MODEL, "prompt": prompt, "seed": seed, "steps": STEPS}
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def call_flux(account_id, token, prompt, seed):
    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{MODEL}"
    body = {"prompt": prompt, "steps": STEPS}
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=TIMEOUT_S) as response:
        data = json.load(response)
    image_b64 = data["result"]["image"]
    return base64.b64decode(image_b64)


def generate_image(name, shot_id, prompt, seed, account_id, token):
    img_path = OUT_DIR / f"{name}.jpg"
    meta_path = OUT_DIR / f"{name}.json"
    key = cache_key(prompt, seed)

    if img_path.exists() and meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if meta.get("cache_key") == key:
            print(f"{name}: cached ({MODEL}, seed={seed})")
            return

    for attempt in range(1, MAX_ATTEMPTS + 1):
        start = time.monotonic()
        try:
            img_bytes = call_flux(account_id, token, prompt, seed)
            latency = time.monotonic() - start
            img_path.write_bytes(img_bytes)
            meta_path.write_text(
                json.dumps(
                    {
                        "cache_key": key,
                        "model": MODEL,
                        "seed": seed,
                        "steps": STEPS,
                        "prompt": prompt,
                        "bytes": len(img_bytes),
                    },
                    indent=2,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            log_run(
                {
                    "stage": "keyframes",
                    "provider": "cloudflare",
                    "model": MODEL,
                    "shot": shot_id,
                    "attempt": attempt,
                    "params": {"steps": STEPS, "seed": seed, "prompt_chars": len(prompt)},
                    "latency_s": round(latency, 2),
                    "status": "ok",
                    "output": {"file": f"outputs/keyframes/{name}.jpg", "bytes": len(img_bytes)},
                    "cost": {"free_tier": True, "list_price_usd": 0.003},
                    "cache_key": key,
                }
            )
            print(f"{name}: generated ({len(img_bytes)} bytes, {latency:.1f}s)")
            return
        except (urllib.error.URLError, KeyError, ValueError) as exc:
            latency = time.monotonic() - start
            detail = str(exc)
            if isinstance(exc, urllib.error.HTTPError):
                detail = f"{exc}: {exc.read().decode('utf-8', 'ignore')[:400]}"
            log_run(
                {
                    "stage": "keyframes",
                    "provider": "cloudflare",
                    "model": MODEL,
                    "shot": shot_id,
                    "attempt": attempt,
                    "latency_s": round(latency, 2),
                    "status": "error",
                    "error": detail,
                }
            )
            if attempt == MAX_ATTEMPTS:
                raise
            print(f"{name}: attempt {attempt} failed, retrying")
            time.sleep(3 * attempt)


def main():
    board = load_storyboard()
    errors = validate(board)
    if errors:
        for error in errors:
            print(f"ERROR {list(error.path)}: {error.message}")
        return 1

    account_id, token = load_cf_credentials()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    ref_prompt = compose_reference_prompt(board)
    generate_image("reference_sheet", 0, ref_prompt, 42, account_id, token)

    for shot in board["shots"]:
        prompt = compose_shot_prompt(board, shot)
        generate_image(f"shot_{shot['id']:02d}", shot["id"], prompt, shot["seed"], account_id, token)

    print(f"keyframes: all {len(board['shots'])} shots + reference_sheet ready")
    return 0


if __name__ == "__main__":
    sys.exit(main())
