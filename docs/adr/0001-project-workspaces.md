# 1. Isolate every film in its own project workspace

- Status: Accepted
- Date: 2026-11-26

## Context

The repository began as one film. `storyboard.json`, `outputs/`, and every cache
sidecar sit at the repository root, and every stage reads `ROOT` from
`pipeline/validate.py`. The studio must let many people draft unrelated films
without one film's narration, keyframes, cache keys, or final cuts overwriting
another's. It must also keep the graded Abigiya film intact as the showcase.

## Decision

Every film created through the studio lives in `projects/<slug>/` and owns a
complete copy of the pipeline layout:

```
projects/<slug>/
  project.json        # title, inputs, language, style, last job
  storyboard.json
  outputs/...
  job.log
```

`pipeline/validate.py` resolves the active root from `PROJECT_ROOT` (set by the
studio when it spawns a stage) or `--project projects/<slug>`, falling back to
the repository root. Credentials always come from `REPO_ROOT/.env`; no project
directory may hold secrets. Stages stay subprocesses so their import-time root
resolution matches `make film`.

The repository root remains the read-only `showcase` workspace. `studio.py`
refuses edits and deletion there, and the API returns `403` for any mutating
request against it. `projects/` is git-ignored because generated media is large
and personal.

## Consequences

- Two films can run the same stage with different roots in parallel without
  sharing cache sidecars or artifacts.
- `make film` keeps working unchanged at the root, so the graded output and its
  documented line numbers stay reproducible.
- Per-project disk use grows with every generated film; deleting a project is a
  single `rmtree` of its folder.
- Stage scripts cannot import project state at module scope; they must read the
  root through `validate.ROOT` after the environment is set.
