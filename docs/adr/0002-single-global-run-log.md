# 2. Keep one global run log, tagged by project

- Status: Accepted
- Date: 2026-11-26

## Context

`runs.jsonl` is the audit trail the documentation cites line by line, and
`runlog.requests_today()` counts free-tier usage from it. With many project
workspaces, a per-project log would make both jobs harder: the audit would
fragment, and daily quota would be counted once per film even though the limit
belongs to the API key.

## Decision

There is exactly one `runs.jsonl`, at the repository root. `runlog.log_run()`
injects a `project` field when `PROJECT_SLUG` is set (the studio sets it for
every stage subprocess) and omits the field for the original root runs, so
existing line numbers and records do not change.

Quota accounting stays global: `requests_today(model, key_id)` counts every
line with that model and key prefix regardless of project, because Gemini and
Cloudflare limits are enforced per key, not per film.

## Consequences

- The audit remains a single chronological file; `project` makes studio runs
  filterable with `jq 'select(.project=="lantern-keeper")'`.
- Free-tier exhaustion is reported correctly when several films share a key.
- Concurrent stage subprocesses append to one file. Appends are line-sized and
  `log_run()` opens in append mode, which is atomic enough for this local
  single-user studio; a multi-user deployment would need a writer process or a
  database.
- The log grows without bound. Rotation is out of scope; the studio reads only
  the last 400 lines of a project's `job.log`, not `runs.jsonl`.
