import json
import os
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
RUNS_PATH = ROOT / "runs.jsonl"
QUOTA_TIMEZONE = ZoneInfo("America/Los_Angeles")


def current_project():
    """Slug of the film being generated, set by the studio for every stage subprocess."""
    return os.environ.get("PROJECT_SLUG", "").strip()


def log_run(entry):
    project = current_project()
    record = {"timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    if project:
        record["project"] = project
    record.update(entry)
    with RUNS_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def requests_today(model, key_id):
    """Count today's calls for one model and API key across every project.

    Quota belongs to the key, not the film, so this deliberately reads the one
    global run log rather than a per-project log.
    """
    if not RUNS_PATH.exists():
        return 0
    today = datetime.now(QUOTA_TIMEZONE).date()
    count = 0
    for line in RUNS_PATH.read_text(encoding="utf-8").splitlines():
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if record.get("model") != model or record.get("key_id") != key_id or "timestamp" not in record:
            continue
        stamp = datetime.strptime(record["timestamp"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        if stamp.astimezone(QUOTA_TIMEZONE).date() == today:
            count += 1
    return count
