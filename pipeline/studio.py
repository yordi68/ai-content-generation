import json
import re
import shutil
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

from validate import REPO_ROOT, END_CARD_DURATION_S, validate

PROJECTS_DIR = REPO_ROOT / "projects"
SHOWCASE_SLUG = "showcase"
META_NAME = "project.json"

STYLE_BLOCKS = {
    "storybook": "soft hand-painted storybook illustration, warm gentle light, pastel colours, painterly texture",
    "cinematic": "cinematic digital painting, warm volumetric light, rich shadows, gentle film grain",
    "papercut": "layered paper-cut illustration, textured cardstock, soft shadows, warm earthy palette",
}

VOICE_PRESETS = {
    "am": {
        "provider": "edge-tts",
        "models": [
            "am-ET-MekdesNeural",
            "gemini-3.8-flash-tts",
            "gemini-3.8-flash-lite-tts",
            "gemini-2.5-flash-preview-tts",
        ],
        "voice_name": "am-ET-MekdesNeural",
        "style": "editorial note only (not sent in prompt): calm, warm Ethiopian Amharic bedtime storyteller",
        "tempo": 1.0,
    },
    "en": {
        "provider": "edge-tts",
        "models": [
            "en-US-AriaNeural",
            "gemini-3.8-flash-tts",
            "gemini-3.8-flash-lite-tts",
            "gemini-2.5-flash-preview-tts",
        ],
        "voice_name": "en-US-AriaNeural",
        "style": "editorial note only (not sent in prompt): calm, warm bedtime storyteller",
        "tempo": 1.0,
    },
}

MUSIC_CAPTIONS = {
    "am": "gentle warm Ethiopian Tizita pentatonic krar and soft ambient pad lullaby, peaceful bedtime story underscore, slow tempo, instrumental, no vocals, soft dynamics leaving space for voice narration",
    "en": "gentle warm lullaby underscore, soft piano and ambient pad, peaceful bedtime story, slow tempo, instrumental, no vocals, soft dynamics leaving space for voice narration",
}

LANGUAGES = {"am": "Amharic (Ge'ez script)", "en": "English"}
CANONICAL_STAGES = ["script", "narration", "keyframes", "shots", "music", "assemble"]
EDITABLE_FIELDS = {"narration", "subtitle", "picture", "characters", "motion", "seed", "reason"}


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def slugify(text):
    normalised = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", normalised.lower()).strip("-")[:40]
    return slug or "film"


def unique_slug(base):
    candidate = slugify(base)
    if candidate == SHOWCASE_SLUG:
        candidate = "film"
    existing = {p.name for p in PROJECTS_DIR.iterdir()} if PROJECTS_DIR.exists() else set()
    if candidate not in existing and candidate != SHOWCASE_SLUG:
        return candidate
    index = 2
    while f"{candidate}-{index}" in existing:
        index += 1
    return f"{candidate}-{index}"


def project_root(slug):
    if slug == SHOWCASE_SLUG:
        return REPO_ROOT
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,47}", slug or ""):
        raise KeyError(slug)
    path = PROJECTS_DIR / slug
    if not path.is_dir():
        raise KeyError(slug)
    return path


def read_meta(slug):
    root = project_root(slug)
    if slug == SHOWCASE_SLUG:
        board = storyboard(slug) or {}
        return {
            "slug": slug,
            "title": board.get("title", "Showcase film"),
            "created_at": "",
            "updated_at": "",
            "read_only": True,
            "inputs": {},
            "job": {"status": "idle", "stage": None, "error": None, "stages": []},
        }
    path = root / META_NAME
    if path.exists():
        meta = json.loads(path.read_text(encoding="utf-8"))
    else:
        meta = {"slug": slug, "title": slug, "created_at": "", "updated_at": ""}
    meta.setdefault("slug", slug)
    meta.setdefault("read_only", False)
    meta.setdefault("inputs", {})
    meta.setdefault("job", {"status": "idle", "stage": None, "error": None, "stages": []})
    return meta


def write_meta(slug, meta):
    if slug == SHOWCASE_SLUG:
        raise PermissionError("the showcase film is read-only")
    meta["updated_at"] = now_iso()
    write_json(project_root(slug) / META_NAME, meta)


def create_project(title, mode, story_prompt, script, language, style):
    if language not in LANGUAGES:
        raise ValueError(f"language must be one of {sorted(LANGUAGES)}")
    if style not in STYLE_BLOCKS:
        raise ValueError(f"style must be one of {sorted(STYLE_BLOCKS)}")
    seed_text = title or story_prompt or script or "film"
    slug = unique_slug(seed_text)
    root = PROJECTS_DIR / slug
    root.mkdir(parents=True, exist_ok=False)
    meta = {
        "slug": slug,
        "title": (title or "").strip(),
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "read_only": False,
        "inputs": {
            "mode": mode,
            "story_prompt": story_prompt.strip(),
            "script": script.strip(),
            "language": language,
            "style": style,
        },
        "job": {"status": "queued", "stage": None, "error": None, "stages": []},
    }
    write_json(root / META_NAME, meta)
    return slug


def storyboard(slug):
    path = project_root(slug) / "storyboard.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def save_storyboard(slug, board):
    write_json(project_root(slug) / "storyboard.json", board)


def mark_shot_edited(slug, shot_id, needs_media=True):
    """Record that a saved edit is waiting for regeneration and/or assembly."""
    if slug == SHOWCASE_SLUG:
        return
    meta = read_meta(slug)
    dirty = {int(value) for value in meta.get("dirty_shots", [])}
    if needs_media:
        dirty.add(int(shot_id))
    meta["dirty_shots"] = sorted(dirty)
    meta["film_stale"] = True
    write_meta(slug, meta)


def clear_build_state(slug, shot_ids=None):
    """Clear build marks after success; None clears every shot and the cuts."""
    if slug == SHOWCASE_SLUG:
        return
    meta = read_meta(slug)
    if shot_ids is None:
        meta["dirty_shots"] = []
        meta["film_stale"] = False
    else:
        dirty = {int(value) for value in meta.get("dirty_shots", [])} - {
            int(value) for value in shot_ids
        }
        meta["dirty_shots"] = sorted(dirty)
    write_meta(slug, meta)


def artifact(path):
    if not path.exists():
        return {"exists": False, "mtime": 0, "bytes": 0}
    stat = path.stat()
    return {"exists": True, "mtime": int(stat.st_mtime), "bytes": stat.st_size}


def project_summary(slug):
    root = project_root(slug)
    meta = read_meta(slug)
    board = storyboard(slug)
    shots = []
    total_seconds = None

    if board:
        dirty_shots = {int(shot_id) for shot_id in meta.get("dirty_shots", [])}
        for shot in board.get("shots", []):
            shot_id = shot["id"]
            artifacts = {
                "narration": artifact(root / "outputs" / "narration" / f"shot_{shot_id:02d}.wav"),
                "keyframe": artifact(root / "outputs" / "keyframes" / f"shot_{shot_id:02d}.jpg"),
                "shot_9x16": artifact(root / "outputs" / "shots" / f"shot_{shot_id:02d}_9x16.mp4"),
                "shot_16x9": artifact(root / "outputs" / "shots" / f"shot_{shot_id:02d}_16x9.mp4"),
            }
            missing = any(not item["exists"] for item in artifacts.values())
            shots.append(
                {
                    **shot,
                    "artifacts": artifacts,
                    "missing": missing,
                    "stale": shot_id in dirty_shots,
                }
            )
        durations = [shot.get("duration_s") for shot in board.get("shots", [])]
        if durations and all(isinstance(value, (int, float)) for value in durations):
            total_seconds = round(sum(durations) + END_CARD_DURATION_S, 1)

    films = {
        name: artifact(root / "outputs" / f"{name}.mp4")
        for name in ("film_9x16", "film_16x9", "radio_cut")
    }
    film_meta = {key: value for key, value in board.items() if key != "shots"} if board else None

    return {
        "slug": slug,
        "meta": meta,
        "film": film_meta,
        "shots": shots,
        "films": films,
        "total_seconds": total_seconds,
        "read_only": slug == SHOWCASE_SLUG,
        "storyboard_exists": board is not None,
        "film_stale": bool(meta.get("film_stale")),
    }


def list_projects():
    projects = []
    if PROJECTS_DIR.exists():
        for path in PROJECTS_DIR.iterdir():
            if not path.is_dir():
                continue
            try:
                projects.append(project_summary(path.name))
            except (KeyError, json.JSONDecodeError):
                continue
    projects.sort(key=lambda item: item["meta"].get("updated_at", ""), reverse=True)
    return [project_summary(SHOWCASE_SLUG)] + projects


def plan_stages(old_shot, new_shot):
    stages = set()
    if old_shot.get("narration") != new_shot.get("narration"):
        stages.update({"narration", "shots", "music"})
    if any(old_shot.get(key) != new_shot.get(key) for key in ("picture", "characters", "seed")):
        stages.update({"keyframes", "shots"})
    if old_shot.get("motion") != new_shot.get("motion"):
        stages.add("shots")
    return [stage for stage in CANONICAL_STAGES if stage in stages]


def apply_shot_edit(slug, shot_id, fields):
    if slug == SHOWCASE_SLUG:
        raise PermissionError("the showcase film is read-only; create a new film to edit")
    board = storyboard(slug)
    if board is None:
        raise ValueError("this film has no storyboard yet")
    unknown = set(fields) - EDITABLE_FIELDS
    if unknown:
        raise ValueError(f"fields cannot be edited here: {sorted(unknown)}")
    shot = next((item for item in board["shots"] if item["id"] == shot_id), None)
    if shot is None:
        raise ValueError(f"shot {shot_id} does not exist")
    old_shot = json.loads(json.dumps(shot))
    shot.update(fields)
    errors = validate(board)
    if errors:
        raise ValueError("; ".join(f"{list(error.path)}: {error.message}" for error in errors))
    save_storyboard(slug, board)
    stages = plan_stages(old_shot, shot)
    changed = {key for key in fields if old_shot.get(key) != shot.get(key)}
    if changed - {"reason"}:
        mark_shot_edited(slug, shot_id, needs_media=bool(stages))
    return board, stages


def delete_project(slug):
    if slug == SHOWCASE_SLUG:
        raise PermissionError("the showcase film cannot be deleted")
    shutil.rmtree(project_root(slug))
