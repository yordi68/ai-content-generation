import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = REPO_ROOT / "schema" / "storyboard.schema.json"
END_CARD_DURATION_S = 2.6


def _flag_value(name):
    argv = sys.argv[1:]
    for index, arg in enumerate(argv):
        if arg == name and index + 1 < len(argv):
            return argv[index + 1]
        if arg.startswith(name + "="):
            return arg.split("=", 1)[1]
    return None


def _resolve_project_root():
    raw = os.environ.get("PROJECT_ROOT") or _flag_value("--project")
    if not raw:
        return REPO_ROOT
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    return path.resolve()


ROOT = _resolve_project_root()
STORYBOARD_PATH = ROOT / "storyboard.json"


def load_storyboard(path=STORYBOARD_PATH):
    return json.loads(path.read_text(encoding="utf-8"))


def selected_shots():
    """Return the set of shot ids requested with --shots, or None for every shot."""
    raw = _flag_value("--shots")
    if not raw:
        return None
    ids = set()
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start, end = part.split("-", 1)
            ids.update(range(int(start), int(end) + 1))
        else:
            ids.add(int(part))
    return ids or None


def selected_aspects():
    raw = _flag_value("--aspect")
    if not raw:
        return None
    return [part.strip() for part in raw.split(",") if part.strip()]


def validate(board):
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    errors = list(sorted(validator.iter_errors(board), key=lambda e: list(e.path)))

    shots = board.get("shots", [])
    expected_ids = list(range(1, len(shots) + 1))
    actual_ids = [s.get("id") for s in shots]
    if actual_ids != expected_ids:
        errors.append(
            SimpleNamespace(
                path=["shots", "id"],
                message=f"Shot IDs must be sequential 1..{len(shots)}, got {actual_ids}",
            )
        )

    character_map = board.get("characters", {})
    for shot in shots:
        unknown = [key for key in shot.get("characters", []) if key not in character_map]
        if unknown:
            errors.append(
                SimpleNamespace(
                    path=["shots", shot.get("id"), "characters"],
                    message=f"Unknown character keys {unknown}; define them in the film-level characters map",
                )
            )

    for idx, cue in enumerate(board.get("music", [])):
        start_s = cue.get("start_shot", 1)
        end_s = cue.get("end_shot", 1)
        if start_s > end_s or end_s > len(shots):
            errors.append(
                SimpleNamespace(
                    path=["music", idx],
                    message=f"Music cue {cue.get('id')} bounds ({start_s}..{end_s}) exceed shot count {len(shots)}",
                )
            )

    durations = [s.get("duration_s") for s in shots]
    if shots and all(isinstance(d, (int, float)) for d in durations):
        total_s = round(sum(durations) + END_CARD_DURATION_S, 1)
        if not (60.0 <= total_s <= 90.0):
            errors.append(
                SimpleNamespace(
                    path=["shots", "duration_s"],
                    message=f"Total film duration ({total_s}s incl. {END_CARD_DURATION_S}s end card) must be 60.0..90.0s",
                )
            )

    return errors


def format_errors(errors):
    return [f"{list(error.path)}: {error.message}" for error in errors]


def runtime_errors_only(errors):
    return all(list(error.path) == ["shots", "duration_s"] for error in errors)


def print_errors(errors):
    for error in errors:
        print(f"ERROR {list(error.path)}: {error.message}")


def main():
    board = load_storyboard()
    errors = validate(board)
    if errors:
        print_errors(errors)
        return 1
    durations = [s.get("duration_s") for s in board["shots"]]
    if all(isinstance(d, (int, float)) for d in durations):
        total_s = round(sum(durations) + END_CARD_DURATION_S, 1)
        print(f"{STORYBOARD_PATH} is valid: {len(board['shots'])} shots, {total_s}s total runtime")
    else:
        print(f"{STORYBOARD_PATH} is valid: {len(board['shots'])} shots (durations pending TTS)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
