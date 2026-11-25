import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = ROOT / "schema" / "storyboard.schema.json"
STORYBOARD_PATH = ROOT / "storyboard.json"


def load_storyboard(path=STORYBOARD_PATH):
    return json.loads(path.read_text(encoding="utf-8"))


def validate(board):
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    return sorted(validator.iter_errors(board), key=lambda e: list(e.path))


def main():
    board = load_storyboard()
    errors = validate(board)
    if errors:
        for error in errors:
            print(f"ERROR {list(error.path)}: {error.message}")
        return 1
    print(f"storyboard.json is valid: {len(board['shots'])} shots")
    return 0


if __name__ == "__main__":
    sys.exit(main())
