"""Draft a storyboard from a story prompt or a finished script.

This is the sixth stage named in the brief. It is the only stage that writes
storyboard.json from human input instead of from artifacts. Everything it
produces is validated against the same schema every other stage trusts.
"""

import hashlib
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from runlog import log_run, requests_today
from studio import (
    LANGUAGES,
    MUSIC_CAPTIONS,
    STYLE_BLOCKS,
    VOICE_PRESETS,
    now_iso,
    slugify,
    write_json,
)
from validate import REPO_ROOT, ROOT, STORYBOARD_PATH, _flag_value, format_errors, validate

MODEL = "gemini-3.8-flash"
# Free-tier availability moves: 3.8 can return 503 while 3.5 is healthy. The
# chain is tried in order; a model that is down costs one request, not a film.
MODEL_CHAIN = ["gemini-3.8-flash", "gemini-3.5-flash", "gemini-3.7-flash", "gemini-3.5-flash-lite"]
TIMEOUT_S = 240
DAILY_LIMIT = 20
CODE_VERSION = "script-v1"
ENV_PATH = REPO_ROOT / ".env"


def load_api_key():
    if not ENV_PATH.exists():
        return ""
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        if line.startswith("GEMINI_API_KEY="):
            return line.split("=", 1)[1].strip()
    return ""


def load_inputs():
    meta_path = ROOT / "project.json"
    if meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    else:
        meta = {"slug": ROOT.name, "title": "", "inputs": {}}

    inputs = meta.setdefault("inputs", {})
    prompt = _flag_value("--prompt")
    script = _flag_value("--script-text")
    if prompt:
        inputs.update({"mode": "prompt", "story_prompt": prompt})
    if script:
        inputs.update({"mode": "script", "script": script})
    if _flag_value("--title"):
        meta["title"] = _flag_value("--title")
    if _flag_value("--language"):
        inputs["language"] = _flag_value("--language")
    if _flag_value("--style"):
        inputs["style"] = _flag_value("--style")

    inputs.setdefault("mode", "prompt")
    inputs.setdefault("story_prompt", "")
    inputs.setdefault("script", "")
    inputs.setdefault("language", "am")
    inputs.setdefault("style", "storybook")
    if inputs["mode"] == "prompt" and not inputs["story_prompt"].strip():
        raise SystemExit("This project needs a story prompt before it can be drafted.")
    if inputs["mode"] == "script" and not inputs["script"].strip():
        raise SystemExit("This project needs a script before it can be drafted.")
    if inputs["language"] not in LANGUAGES:
        raise SystemExit(f"Unknown language {inputs['language']!r}; choose am or en.")
    if inputs["style"] not in STYLE_BLOCKS:
        raise SystemExit(f"Unknown style {inputs['style']!r}; choose {sorted(STYLE_BLOCKS)}.")
    return meta, inputs


def word_budget(language):
    if language == "am":
        return "12-20 Amharic words (about 5-9 seconds spoken)"
    return "15-25 English words (about 5-9 seconds spoken)"


def build_prompt(meta, inputs):
    language = inputs["language"]
    style = inputs["style"]
    source = inputs["story_prompt"] if inputs["mode"] == "prompt" else inputs["script"]
    source_label = "STORY PROMPT" if inputs["mode"] == "prompt" else "FINISHED SCRIPT TO DIVIDE INTO SHOTS"
    requested_title = meta.get("title") or "(none, choose one)"

    return f"""You write storyboards for a 60-90 second animated short film.

Return ONE JSON object and nothing else. No markdown fences, no commentary.

Required keys: title, title_local, aspect_ratios, style_block, character, characters, voice, music, shots.

Film-level rules:
- title: a short English title.
- title_local: the same title in {LANGUAGES[language]}.
- aspect_ratios: exactly ["9:16", "16:9"].
- style_block: copy exactly: {STYLE_BLOCKS[style]!r}
- characters: an object mapping 1-3 lowercase keys (for example "abigiya") to a stable description of that character's age, hair and clothing. Keep each under 30 words. Clothing must never change between shots.
- character: one sentence combining every character description, used for a reference sheet.
- voice: copy exactly this object: {json.dumps(VOICE_PRESETS[language], ensure_ascii=False)}
- music: exactly one cue: {{"id": "cue_01", "start_shot": 1, "end_shot": N, "caption": "<mood> instrumental underscore, no vocals, leaves space for narration"}}.

Shot rules (8-12 shots, ids 1..N in order):
- narration: {word_budget(language)} of natural spoken {LANGUAGES[language]}. No stage directions, no quotation marks, no speaker labels.
- subtitle: an English translation, at most 80 characters, no line breaks.
- picture: one clear visual scene with setting, action, light and composition. Do NOT name characters here; they are injected from the characters map. No text, letters, numbers or signs in the image.
- characters: array of character keys actually visible in this shot. Use [] for establishing shots of landscape, sky or empty rooms.
- motion: {{"type": one of "push-in", "pull-out", "pan-left", "pan-right", "none", "amount": "slow" or "gentle"}}. Vary it, and use "none" for the final shot.
- duration_s: null
- seed: a unique integer, 101, 102, 103, ...
- reason: one sentence about the narrative or emotional job of this shot.

Story rules:
- Tell one continuous story with a beginning, a turn and a warm ending. Write the whole narrative in your head first, then divide it into shots.
- Total spoken narration must be 55-75 seconds. Roughly {word_budget(language)} per shot.
- Every shot must advance the story. No filler and no repeated lines.
- Suitable for children and families: no violence, no frightening imagery, no real people.
- If the input is a finished script, keep its story, characters and wording as close as possible while fitting 8-12 shots and the time budget.

Requested title: {requested_title}

{source_label}:
{source.strip()}
"""


def repair_prompt(original_prompt, draft_text, errors):
    return f"""{original_prompt}

Your previous answer was invalid. Errors from the storyboard schema:
{chr(10).join('- ' + error for error in errors)}

Previous answer:
{draft_text[:12000]}

Return the corrected JSON object only. Keep every valid field, fix the errors, and do not add commentary.
"""


def call_gemini(api_key, prompt, temperature, model=MODEL):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": temperature, "responseMimeType": "application/json"},
    }
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=TIMEOUT_S) as response:
        data = json.load(response)
    text = data["candidates"][0]["content"]["parts"][0]["text"]
    return text, data.get("usageMetadata", {})


def extract_json(text):
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned
        cleaned = cleaned.rsplit("```", 1)[0]
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("the model did not return a JSON object")
    return json.loads(cleaned[start : end + 1])


def normalise(draft, meta, inputs):
    if not isinstance(draft, dict):
        raise ValueError("storyboard must be a JSON object")
    language = inputs["language"]
    draft["aspect_ratios"] = ["9:16", "16:9"]
    draft["style_block"] = STYLE_BLOCKS[inputs["style"]]
    draft["voice"] = VOICE_PRESETS[language]

    title = draft.get("title")
    if not isinstance(title, str) or not title.strip():
        title = meta.get("title") or "Untitled Film"
    draft["title"] = title.strip()
    if not isinstance(draft.get("title_local"), str) or not draft["title_local"].strip():
        draft["title_local"] = draft["title"]

    characters = draft.get("characters")
    if not isinstance(characters, dict):
        characters = {}
    cleaned_characters = {}
    for key, description in characters.items():
        if isinstance(key, str) and key.strip() and isinstance(description, str) and description.strip():
            cleaned_characters[slugify(key)] = description.strip()
    draft["characters"] = cleaned_characters

    shots = draft.get("shots")
    if not isinstance(shots, list):
        shots = []
    for index, shot in enumerate(shots, start=1):
        if not isinstance(shot, dict):
            continue
        shot["id"] = index
        shot["duration_s"] = None
        keys = shot.get("characters")
        shot["characters"] = (
            list(dict.fromkeys(slugify(key) for key in keys if slugify(key) in cleaned_characters))
            if isinstance(keys, list)
            else []
        )
        if not isinstance(shot.get("seed"), int) or shot["seed"] < 0:
            shot["seed"] = 100 + index
        shot.setdefault("motion", {"type": "push-in", "amount": "slow"})
    draft["shots"] = shots

    if not isinstance(draft.get("character"), str) or not draft["character"].strip():
        draft["character"] = "; ".join(cleaned_characters.values()) or "a single storybook protagonist"

    caption = MUSIC_CAPTIONS[language]
    music = draft.get("music")
    cue = music[0] if isinstance(music, list) and music and isinstance(music[0], dict) else {}
    draft["music"] = [
        {
            "id": cue.get("id") or "cue_01",
            "start_shot": 1,
            "end_shot": max(1, len(shots)),
            "caption": cue.get("caption") if isinstance(cue.get("caption"), str) and cue["caption"].strip() else caption,
        }
    ]
    return draft


def main():
    if ROOT == REPO_ROOT:
        print("Refusing to draft over the showcase film. Pass --project projects/<slug>.")
        return 2

    meta, inputs = load_inputs()
    api_key = load_api_key()
    if not api_key:
        print("GEMINI_API_KEY is missing from .env; the drafting stage needs it.")
        return 1

    key_id = hashlib.sha256(api_key.encode("utf-8")).hexdigest()[:8]
    models = [model for model in MODEL_CHAIN if requests_today(model, key_id) < DAILY_LIMIT]
    if not models:
        print(f"Every drafting model has used its {DAILY_LIMIT} requests for today; try again after the quota reset.")
        return 1

    prompt = build_prompt(meta, inputs)
    draft_text = ""
    errors = []
    board = None
    used_model = None

    for model in models:
        model_errors = []
        for attempt in (1, 2):
            request_prompt = prompt if attempt == 1 else repair_prompt(prompt, draft_text, model_errors)
            temperature = 0.9 if attempt == 1 else 0.2
            start = time.monotonic()
            try:
                draft_text, usage = call_gemini(api_key, request_prompt, temperature, model)
                draft = extract_json(draft_text)
                candidate = normalise(draft, meta, inputs)
                model_errors = format_errors(validate(candidate))
            except (urllib.error.URLError, TimeoutError, OSError, KeyError, ValueError, json.JSONDecodeError) as exc:
                model_errors = [f"{type(exc).__name__}: {exc}"]
                latency = time.monotonic() - start
                log_run(
                    {
                        "stage": "script",
                        "provider": "google",
                        "model": model,
                        "key_id": key_id,
                        "attempt": attempt,
                        "params": {"mode": inputs["mode"], "language": inputs["language"], "style": inputs["style"], "chars": len(request_prompt)},
                        "latency_s": round(latency, 2),
                        "status": "error",
                        "error": model_errors[0][:500],
                    }
                )
                print(f"script: {model} attempt {attempt} failed: {model_errors[0]}")
                break

            latency = time.monotonic() - start
            log_run(
                {
                    "stage": "script",
                    "provider": "google",
                    "model": model,
                    "key_id": key_id,
                    "attempt": attempt,
                    "params": {"mode": inputs["mode"], "language": inputs["language"], "style": inputs["style"], "chars": len(request_prompt), "shots": len(candidate.get("shots", []))},
                    "latency_s": round(latency, 2),
                    "status": "ok" if not model_errors else "error",
                    "error": "; ".join(model_errors)[:500] if model_errors else None,
                    "output": {"shots": len(candidate.get("shots", [])), "title": candidate.get("title")},
                    "cost": {"free_tier": True, "list_price_usd": 0.0},
                    "cache_key": hashlib.sha256(json.dumps({"code_version": CODE_VERSION, "model": model, "prompt": prompt}, sort_keys=True).encode("utf-8")).hexdigest(),
                }
            )
            if not model_errors:
                board = candidate
                used_model = model
                break
            print(f"script: {model} attempt {attempt} produced an invalid storyboard:")
            for error in model_errors:
                print(f"  ERROR {error}")

        errors = model_errors
        if board is not None:
            break

    if board is None:
        (ROOT / "draft_error.txt").write_text(
            "Every drafting model failed. Last errors:\n"
            + "\n".join(errors)
            + f"\n\nModels tried: {', '.join(models)}\n\nRaw output:\n"
            + draft_text,
            encoding="utf-8",
        )
        print("script: drafting failed; see draft_error.txt for the raw output")
        return 1

    STORYBOARD_PATH.write_text(json.dumps(board, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if not meta.get("title"):
        meta["title"] = board["title"]
    meta["storyboard_updated_at"] = now_iso()
    meta["updated_at"] = now_iso()
    write_json(ROOT / "project.json", meta)

    print(f"script: drafted {len(board['shots'])} shots for {board['title']!r} with {used_model} ({inputs['language']}, {inputs['style']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
