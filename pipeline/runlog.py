import json
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
RUNS_PATH = ROOT / "runs.jsonl"
QUOTA_TIMEZONE = ZoneInfo("America/Los_Angeles")


def log_run(entry):
    record = {"timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), **entry}
    with RUNS_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def requests_today(model, key_id):
    if not RUNS_PATH.exists():
        return 0
    today = datetime.now(QUOTA_TIMEZONE).date()
    count = 0
    for line in RUNS_PATH.read_text(encoding="utf-8").splitlines():
        record = json.loads(line)
        if record.get("model") != model or record.get("key_id") != key_id or "timestamp" not in record:
            continue
        stamp = datetime.strptime(record["timestamp"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        if stamp.astimezone(QUOTA_TIMEZONE).date() == today:
            count += 1
    return count
