import json
import sys
from pathlib import Path
from types import SimpleNamespace

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = ROOT / "schema" / "storyboard.schema.json"
STORYBOARD_PATH = ROOT / "storyboard.json"
END_CARD_DURATION_S = 2.6


def load_storyboard(path=STORYBOARD_PATH):
    return json.loads(path.read_text(encoding="utf-8"))


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


def main():
    board = load_storyboard()
    errors = validate(board)
    if errors:
        for error in errors:
            print(f"ERROR {list(error.path)}: {error.message}")
        return 1
    durations = [s.get("duration_s") for s in board["shots"]]
    if all(isinstance(d, (int, float)) for d in durations):
        total_s = round(sum(durations) + END_CARD_DURATION_S, 1)
        print(f"storyboard.json is valid: {len(board['shots'])} shots, {total_s}s total runtime")
    else:
        print(f"storyboard.json is valid: {len(board['shots'])} shots (durations pending TTS)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
