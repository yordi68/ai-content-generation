# AI Content Generation — *Abigiya and the Little Star* (`ኮኮቤ`)

A reproducible, contract-driven multi-model AI film pipeline that turns a single validated JSON storyboard (`storyboard.json`) into a **65.0-second** short film (`62.4s` across 12 shots + `2.6s` AI disclosure end card) narrated in **Amharic** with burned-in **English subtitles**, an original **65.4-second** Ethiopian Tizita pentatonic lullaby score ducked under the voice, a visible **Made with AI** disclosure end card, and dual exports in **vertical (9:16)** and **horizontal (16:9)** aspect ratios.

---

## One-Command Quickstart

A stranger can clone this repository, provide free-tier Cloudflare Workers AI (and optional Gemini) keys in `.env`, and run a single command (`make film`) to validate the schema and generate the complete film from `storyboard.json`:

```bash
git clone https://github.com/yordi68/ai-content-generation.git
cd ai-content-generation
cp .env.example .env
# Edit .env and fill in CLOUDFLARE_ACCOUNT_ID, CLOUDFLARE_API_TOKEN, and GEMINI_API_KEY
make film
```

### Prerequisites

- **Python 3.10+** (`make film` automatically creates `.venv` and installs `requirements.txt`: `jsonschema==4.26.0`, `pillow==13.0.0`, `edge-tts==7.3.1`, `fastapi==0.115.6`, `uvicorn==0.34.0`)
- **FFmpeg + TrueType Font** (`brew install ffmpeg` on macOS, or `sudo apt install ffmpeg fonts-dejavu-core` on Linux)
- **Free API keys in `.env`:**
  - `CLOUDFLARE_ACCOUNT_ID` and `CLOUDFLARE_API_TOKEN` — from [Cloudflare Workers AI](https://dash.cloudflare.com/) (Free daily allowance, used by `pipeline/keyframes.py` when the keyframe cache misses)
  - `GEMINI_API_KEY` — from [Google AI Studio](https://aistudio.google.com/) (Free Tier, used by `pipeline/narration.py` when failing over from `am-ET-MekdesNeural` to the 3-model Gemini TTS failover chain)

---

## Studio: Make Your Own Film in the Browser

`make film` reproduces the graded Abigiya film. `make web` starts a local studio
where anyone can write a story prompt (or paste a script) and get their own
validated storyboard, narration, illustrations, moving shots, score, and three
finished cuts:

```bash
make web
# open http://127.0.0.1:8000
```

- **One-click generation.** Creating a film queues `script → narration →
  keyframes → shots → music → assemble` on a single background worker and streams
  progress to the page over SSE.
- **Per-shot editing.** The sidebar lists every shot with its keyframe and
  duration. The inspector previews the moving shot (9:16 and 16:9), the
  illustration, and the narration, and lets you edit narration, subtitle, picture
  prompt, active characters, camera motion, seed, and the shot's reason. Saving
  re-runs only the stages its changed fields require and flags the cuts for
  assembly. The three finished cuts are rebuilt when you press **Assemble full
  film**; per-shot saves never re-render them on their own.
- **Isolated workspaces.** Each film lives in `projects/<slug>/` with its own
  `storyboard.json` and `outputs/`. The graded Abigiya film is the read-only
  `showcase` workspace, so studio use can never overwrite it.
- **Local only.** The server binds `127.0.0.1`, reads keys from the repository
  `.env`, and keeps one global `runs.jsonl` tagged with a `project` field so
  free-tier quota is counted per key rather than per film.

The studio is a thin HTTP layer over the same stage scripts `make film` runs; see
[`ARCHITECTURE.md`](ARCHITECTURE.md) and the decisions in
[`docs/adr/`](docs/adr/). Workspace creation, stage planning, shot edits, and
script normalising are covered by `make test`.

---

## What `make film` Produces

Running `make film` executes the pipeline stages in order around `storyboard.json`:

| Stage Command | Script | Active Model / Tool | Output Files |
|---|---|---|---|
| `make validate` | `pipeline/validate.py` | JSON Schema Draft 2020-12 + semantic checks (shot IDs `1..12`, cue bounds, `60.0s..90.0s` runtime) | Validates `storyboard.json` (`12 shots, 65.0s total runtime`) |
| `make narration` | `pipeline/narration.py` | `am-ET-MekdesNeural` (`edge-tts`) primary → `gemini-3.8-flash-tts` → `gemini-3.8-flash-lite-tts` → `gemini-2.5-flash-preview-tts` failover | `outputs/narration/shot_01.wav` .. `shot_12.wav` (`56.27s` speech; `62.4s` with `0.5s` pauses) |
| `make keyframes` | `pipeline/keyframes.py` | Cloudflare `@cf/black-forest-labs/flux-1-schnell` (4 steps, selective character injection) | `outputs/keyframes/reference_sheet.jpg` + `shot_01.jpg` .. `shot_12.jpg` |
| `make shots` | `pipeline/shots.py` | FFmpeg `zoompan` (`push-in`, `pull-out`, `pan-left`, `pan-right`, `none` scaled by `motion.amount`) | `outputs/shots/shot_01_9x16.mp4` .. `shot_12_16x9.mp4` (24 clips, 24 fps) |
| `make music` | `pipeline/music.py` | `local-tizita-lullaby-synth-v1` (Ethiopian Tizita pentatonic krar-and-pad lullaby synth) | `outputs/music/score.wav` (`65.4s` stereo WAV) |
| `make assemble` | `pipeline/assemble.py` | FFmpeg (`sidechaincompress` + 2-pass `loudnorm` `-14.0 LUFS`) + Pillow 2-cue subtitle & end-card overlays | `outputs/radio_cut.mp4` (`65.0s`), `outputs/film_9x16.mp4` (`65.0s`), `outputs/film_16x9.mp4` (`65.0s`) |

---

## Regenerating a Single Shot (Content-Addressed Caching)

Every stage caches its output by a SHA-256 hash of that shot's inputs (plus the stage's `CODE_VERSION`) in a committed JSON sidecar file (`outputs/<stage>/shot_XX.json`), and checks the cache **before** loading `.env` credentials. If you edit **one** shot's `picture` prompt, `seed`, or `narration` line in `storyboard.json` and re-run `make film`:

1. Unchanged shots match their sidecar `cache_key`, print `cached`, and make **zero API calls**.
2. Only the modified shot is regenerated and logged to `runs.jsonl`.
3. `pipeline/assemble.py` rebuilds the final MP4s with the updated shot.

---

## Repository Structure

```
.
├── README.md                        # One-command run instructions, overview, and cost summary
├── Makefile                         # Single-command orchestration (`make film`, `make web`)
├── requirements.txt                 # Pinned Python dependencies (jsonschema, pillow, edge-tts, fastapi, uvicorn)
├── .env.example                     # Environment variable template (no secrets committed)
├── storyboard.json                  # The contract between all stages (12 shots, prompts, cues)
├── CONTEXT.md                       # Canonical studio vocabulary (prompt, script, storyboard, shot, cut)
├── schema/
│   └── storyboard.schema.json       # JSON Schema validated before every stage run
├── pipeline/
│   ├── validate.py                  # Resolves the active project root, then validates schema and invariants
│   ├── script.py                    # Drafts a validated storyboard from a prompt or script (Gemini)
│   ├── runlog.py                    # Appends every model call to runs.jsonl + tracks daily quota
│   ├── narration.py                 # Edge Neural TTS + 3-model Gemini TTS failover & 20s RPM pacing
│   ├── keyframes.py                 # Reference sheet + FLUX.1-schnell keyframes (selective characters)
│   ├── shots.py                     # Moving shots in 9:16 and 16:9 via FFmpeg zoompan
│   ├── music.py                     # Tizita pentatonic lullaby score synthesizer
│   ├── assemble.py                  # Sidechain ducking, 2-pass -14 LUFS loudnorm, subtitles & end card
│   ├── studio.py                    # Project workspaces, summaries, stage planning, shot edits
│   └── web.py                       # FastAPI app, SSE progress, single-worker job queue
├── web/                             # Vanilla HTML/CSS/JS studio UI (no build step)
├── projects/                        # Git-ignored per-film workspaces (`projects/<slug>/`)
├── tests/                           # unittest coverage for workspaces, stage planning, script normalising
├── docs/adr/                        # Architecture decision records (workspaces, global run log)
├── runs.jsonl                       # Complete structured log of all 215 model/stage calls, latencies & costs
├── outputs/                         # Committed *.json SHA-256 cache sidecars (+ git-ignored media binaries)
├── DESIGN.md                        # Audience, intent, per-shot reasons, and user test records
├── ARCHITECTURE.md                  # Stage contracts, SHA-256 caching, and quota failover design
├── EXPERIMENTS.md                   # 11 logged hypothesis -> change -> result experiments with line numbers
├── FAILURES.md                      # 13 real blockers encountered (quotas, language, drift) & fixes
├── COSTS.md                         # Exact measured latency, compute minutes, quotas & list-price costs
├── ETHICS.md                        # Consent record, model licences, C2PA re-encoding note & AI labelling
└── REPORT.md                        # Written reflection report for Assignment 1
```

---

## Cost Summary

- **Actual out-of-pocket cost:** **$0.00** (runs entirely on free-tier endpoints and local FFmpeg/Python).
- **Measured active compute time (`runs.jsonl` lines 165–215):** `27.65s` narration (`am-ET-MekdesNeural`) + `46.93s` keyframes (v1 fast queue; `469.96s` in v2 during peak queue) + `34.35s` moving shots + `3.12s` score synthesis + `50.06s` two-pass assembly = **`162.11s`–`585.14s`**.
- **Commercial list-price equivalent:** **`$0.039` USD** logged in `runs.jsonl` per 13-image FLUX run (`~$0.059 USD` including estimated commercial TTS/CPU rates), and **`$0.078` USD** logged across all **215 lines** (`195 ok`, `20 error`) in `runs.jsonl`. See [`COSTS.md`](COSTS.md) for the complete line-by-line audit.
