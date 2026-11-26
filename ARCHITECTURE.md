# Architecture

## Overview

This repository is a code-driven short-film studio built around a single contract file: `storyboard.json`. Every stage in `pipeline/` reads `storyboard.json`, validates it against `schema/storyboard.schema.json` (plus semantic invariants in `pipeline/validate.py`), checks its local SHA-256 content cache (`outputs/<stage>/*.json`) **before** loading any API credentials, calls its model or tool only for shots whose inputs or `CODE_VERSION` changed, logs every call to `runs.jsonl`, and writes its outputs to `outputs/`.

Because our team did not have a phone-verified Kaggle GPU session or Colab GPU quota available within the sprint window, the moving-shots and score stages use the brief's documented zero-GPU deterministic floor path (`ffmpeg-zoompan` Ken Burns camera motion on FLUX.1-schnell keyframes and `local-tizita-lullaby-synth-v1` Ethiopian pentatonic lullaby synthesis), while providing drop-in file override hooks if Wan 2.2 (`outputs/wan/shot_XX.mp4`) or ACE-Step 1.5 (`outputs/music/ace_step_chosen.wav`) files are supplied later.

```
                       +-------------------------------+
                       |        storyboard.json        |
                       |  (Validated by validate.py)   |
                       +---------------+---------------+
                                       |
         +--------------+--------------+--------------+--------------+
         |              |              |              |              |
         v              v              v              v              v
  +-------------+ +-------------+ +-------------+ +-------------+    |
  | narration.py| | keyframes.py| |   shots.py  | |   music.py  |    |
  | Edge Neural | | Cloudflare  | | FFmpeg      | | Local Tizita|    |
  | Mekdes +    | | FLUX.1      | | zoompan     | | Pentatonic  |    |
  | 3-Model     | | schnell     | | (push/pull/ | | Lullaby     |    |
  | Gemini TTS  | | (selective  | |  pan/none)  | | Synth       |    |
  | Failover    | |  characters)| |             | |             |    |
  +------+------+ +------+------+ +------+------+ +------+------+    |
         |               |               |               |           |
         +---------------+-------+-------+---------------+           |
                                 |                                   |
                                 v                                   |
                         +---------------+                           |
                         |  assemble.py  |<--------------------------+
                         | Sidechain duck|
                         | 2-pass -14LUFS|
                         | 2-cue subs +  |
                         | AI End Card   |
                         +-------+-------+
                                 |
            +--------------------+--------------------+
            |                    |                    |
            v                    v                    v
   outputs/radio_cut.mp4  outputs/film_9x16.mp4  outputs/film_16x9.mp4
         (65.0s)                (65.0s)                (65.0s)
```

---

## Studio Layer, Project Roots, and Drafting

The pipeline has two front doors with one engine behind them:

- `make film` validates and renders the repository root: the graded Abigiya film.
- `make web` starts `pipeline/web.py`, a FastAPI app that drafts new films and
  runs the same stages against `projects/<slug>/` workspaces.

`pipeline/studio.py` owns everything the web app needs that is not a stage:
slug generation, `project.json` metadata, workspace creation and deletion,
artifact summaries (exists / mtime / bytes / missing / out of date), stage
planning for a shot edit, and the read-only guard on the `showcase` workspace.
`pipeline/web.py` owns HTTP, the single-worker job queue, SSE progress, and
media serving. It never imports a stage module; it spawns
`python pipeline/<stage>.py` with `PROJECT_ROOT` and `PROJECT_SLUG` in the
environment, because every stage resolves its root at import time.

`pipeline/validate.py` exposes both `REPO_ROOT` (credentials, `runs.jsonl`,
showcase) and `ROOT` (the active project). `_resolve_project_root()` prefers
`PROJECT_ROOT`, then `--project`, then the repository root. `--shots` filters
narration, keyframes, and moving shots to the edited shot; `--aspect` filters
moving shots to one aspect. This is what makes a per-shot save cheap.

Field-level dirty tracking lives in `studio.plan_stages()`:

| Changed field | Stages re-run |
|---|---|
| `narration` | `narration`, `shots`, `music` |
| `picture`, `characters`, `seed` | `keyframes`, `shots` |
| `motion` | `shots` |
| `subtitle` | nothing (the cuts are flagged stale) |
| `reason` | nothing |

No save assembles. Every save except a reason-only edit sets `film_stale`, and
the **Assemble full film** action is the only thing that rebuilds the three
cuts. Assembly refuses to run while a shot is missing media or still waiting for
its own regeneration, so a cut can never quietly use stale media.

The queue is deliberately one worker: free-tier quotas and FFmpeg are shared, and
serial execution keeps `runs.jsonl` and cache sidecars easy to reason about.
Progress reaches the browser as Server-Sent Events; the UI also polls the project
summary so a reload or a second tab converges on the same state.

A media edit writes the shot and records it in `project.json`'s `dirty_shots`.
A successful per-shot job clears exactly the shots it rebuilt; `film_stale`
stays set until an assemble (or full generation) succeeds. The sidebar's "out of
date" chip therefore means "this shot's media is saved but not rendered", and
the film badge means "the cuts need assembly". That distinction matters because
narration legitimately rewrites `storyboard.json` after the WAVs exist.

---

## Stage Boundaries and Contracts

0. **`pipeline/script.py` — Drafting a Validated Storyboard**
   - Reads `project.json` inputs (prompt or pasted script, language, style) and
     asks `gemini-3.8-flash` (falling back to `gemini-3.5-flash`,
     `gemini-3.7-flash`, then `gemini-3.5-flash-lite` when a model returns 503)
     for one JSON object, then validates it with the same `validate()` every
     other stage trusts.
   - On failure it makes exactly one repair call with the schema errors and the
     previous answer, then writes `draft_error.txt` instead of a bad storyboard.
   - `normalise()` forces the fields the studio owns rather than trusting the
     model: both aspect ratios, the chosen style block, the language's voice
     preset, `duration_s: null` (timing belongs to narration), sequential shot
     IDs, unique seeds, known character keys, and one normalised music cue.
   - Refuses to run at the repository root so the showcase storyboard cannot be
     overwritten.

1. **`pipeline/validate.py` — Contract and Invariant Gate**
   - Validates `storyboard.json` against `schema/storyboard.schema.json` (JSON Schema Draft 2020-12) before every stage run.
   - Enforces required film-level fields (`title`, `aspect_ratios` requiring both `"9:16"` and `"16:9"`, `style_block`, `character`, `characters`, `voice`, `music`, `shots`) and per-shot fields (`id`, `narration`, `subtitle`, `picture`, `characters`, `motion`, `duration_s`, `seed`, `reason`).
   - Enforces semantic invariants beyond static JSON Schema:
     - Sequential, unique shot IDs `1..N` (`8 <= N <= 12`).
     - Music cue shot boundaries (`1 <= start_shot <= end_shot <= N`).
     - Total runtime check: once `duration_s` is populated on all shots, `sum(duration_s) + 2.6s` (end card) must fall strictly within **`60.0s..90.0s`** (current film runtime: **`65.0s`**).

2. **`pipeline/narration.py` — Voice Synthesis and Timing Spine**
   - Reads each shot's Amharic `narration` and `voice.models` list from `storyboard.json`.
   - Synthesizes one WAV file per shot (`outputs/narration/shot_XX.wav`) and measures its exact frame duration (`frames / sample_rate`).
   - Updates `shot["duration_s"]` in `storyboard.json` (`round(seconds / tempo + 0.5, 1)`) so picture cuts follow the voice track (`62.4s` across 12 shots + `2.6s` end card = `65.0s` total film runtime).
   - **Why `voice.style` is not sent in the prompt:** During Experiment 5 (`FAILURES.md`, Entry 8), prefixing Amharic text with an English style instruction (`"Say in a ... voice:"`) caused Gemini TTS to speak English instead of Amharic. Therefore, `narration.py` sends raw Amharic text only (`"prompt_mode": "raw_text"`), and `voice.style` is retained purely as an editorial note in `storyboard.json`.
   - Wraps raw 24 kHz 16-bit mono PCM audio streams (`audio/L16;rate=24000`) in a standard RIFF WAV header (`to_wav()`) when a Gemini 2.5 fallback model returns headerless PCM.

3. **`pipeline/keyframes.py` — Reference Sheet and Selective-Character Keyframe Generation**
   - Checks the local SHA-256 cache (`outputs/keyframes/*.json`) **before** reading `.env`, so a fully cached re-run succeeds even without API credentials.
   - Generates `outputs/keyframes/reference_sheet.jpg` first, then `outputs/keyframes/shot_01.jpg` through `shot_12.jpg` via Cloudflare Workers AI (`@cf/black-forest-labs/flux-1-schnell`, 4 steps).
   - **Selective Character Conditioning:** Rather than blindly prepending both characters to every prompt (which in v1 injected Abigiya and her grandmother into Shot 1's village establishing shot and Shot 3's night-sky star shot), `compose_shot_prompt()` reads each shot's `characters` list (`[]`, `["abigiya"]`, or `["grandmother", "abigiya"]`) and looks up only the active characters in `board["characters"]`.
   - **Important API Constraint:** Cloudflare's `@cf/black-forest-labs/flux-1-schnell` endpoint is text-to-image only (it does not accept `reference_sheet.jpg` as an image input) and rejects `/seed` in the JSON request body with HTTP 400 (`code: 5006`, logged in `runs.jsonl` lines 85–87). Therefore, `seed` is kept inside the local SHA-256 `cache_key` to trigger intentional cache invalidation per shot, while visual continuity relies on the locked `style_block` and explicit character clothing descriptions (`"warm yellow-and-teal dress"`, `"white cotton netela shawl"`).

4. **`pipeline/shots.py` — Moving Shots (FFmpeg Ken Burns `zoompan`)**
   - For each shot and each target aspect ratio (`9:16` at `720x1280` and `16:9` at `1280x720`, 24 fps), animates `outputs/keyframes/shot_XX.jpg` using FFmpeg's `zoompan` filter according to `shot["motion"]["type"]` (`push-in`, `pull-out`, `pan-left`, `pan-right`, `none`) and `shot["motion"]["amount"]` (`"slow"` = `0.15` zoom delta, `"gentle"` = `0.08`, `"none"` = `0.0`).
   - If an external Wan 2.2 clip is placed at `outputs/wan/shot_XX.mp4`, scales/crops it and holds the final frame with `tpad=stop_mode=clone` (avoiding stutter loops on longer shots).

5. **`pipeline/music.py` — Original Score (Local Tizita Pentatonic Synthesizer)**
   - Reads the music cue and total duration (`62.4s` shots + `3.0s` tail = `65.4s` score) from `storyboard.json`.
   - Synthesizes a gentle Ethiopian Tizita major pentatonic krar-and-pad lullaby underscore (`outputs/music/score.wav`, model `local-tizita-lullaby-synth-v1`) in pure Python so `make film` runs deterministically on any machine with zero GPU wait. (If an external `outputs/music/ace_step_chosen.wav` track is placed in the folder, it hashes, logs, and caches the override automatically.)

6. **`pipeline/assemble.py` — Sidechain Ducking, Two-Pass `-14 LUFS` Loudness, Timed Subtitle Cues, and Dual Export**
   - Applies voice `tempo` (`atempo=1.00`) and pads each shot's narration to its exact `duration_s`, concatenating all 12 shots plus a 2.6-second silence tail for the end card into `outputs/build/voice_stem.wav` (`65.0s` total).
   - Ducks the musical score under the narration using FFmpeg's `sidechaincompress` (`threshold=0.02:ratio=6:attack=300:release=1500`).
   - Runs **two-pass EBU R128 loudness normalization** (`loudnorm=I=-14:TP=-1.0:LRA=11`): Pass 1 measures `input_i`, `input_tp`, `input_lra`, `input_thresh`, and `target_offset` in JSON mode, and Pass 2 applies linear normalization (`linear=true`) with the measured parameters and logs the Pass 1 measurements to `runs.jsonl`.
   - Splits long English subtitles (`>85` characters, such as Shot 8's 160-character lesson) at sentence boundaries into **two timed subtitle cues** (`overlay=0:0:enable='between(t,t0,t1)'`), wrapping each cue to at most 3 lines inside the vertical and horizontal safe areas using macOS or Linux TrueType fonts (`Arial` / `Helvetica` / `DejaVuSans` / `LiberationSans`).
   - Appends the 2.6-second `"Made with AI"` disclosure end card naming the active voice (`am-ET-MekdesNeural (Edge TTS) & Gemini TTS`), `FLUX.1-schnell`, and `FFmpeg`.
   - Exports `outputs/radio_cut.mp4` (`65.0s`), `outputs/film_9x16.mp4` (`65.0s`), and `outputs/film_16x9.mp4` (`65.0s`).

---

## Content-Addressed Caching (Partial Re-Runs)

Every stage computes a SHA-256 `cache_key` over the exact inputs **plus** the stage's `CODE_VERSION` and writes a committed JSON sidecar file (`outputs/<stage>/shot_XX.json`):

- **Narration cache key (`narration-v2`):** `SHA256({code_version, narration, primary_model, voice_name, prompt_mode})`
- **Keyframes cache key (`keyframes-v2`):** `SHA256({code_version, model, composed_prompt, seed, steps})`
- **Moving shots cache key (`shots-v2`):** `SHA256({code_version, keyframe_file_sha256, motion, duration_s, aspect, fps})`
- **Music cache key (`music-v2`):** `SHA256({code_version, cue, duration_s, source})`

Because the lightweight `.json` cache sidecars in `outputs/` are committed to git (while large `.wav`, `.jpg`, and `.mp4` media binaries stay git-ignored), graders can inspect the exact SHA-256 cache keys alongside `runs.jsonl`.

---

## Quota Pacing, Daily Budget Tracking, and Multi-Model Failover

Free-tier Gemini TTS models enforce **3 Requests Per Minute (RPM)** and **10 Requests Per Day (RPD)** per model per project. `pipeline/narration.py` and `pipeline/runlog.py` implement:
1. **Request Pacing (`pace()`):** Enforces a 20-second minimum gap between Gemini TTS calls so the 3 RPM limit is never breached.
2. **Per-Key, Per-Model Daily Budget Tracking (`requests_today()`):** Counts calls per model in `runs.jsonl` in the `America/Los_Angeles` quota timezone (tagged by an 8-character SHA-256 key prefix `key_id`) and skips any Gemini model at 10/10 RPD.
3. **Ordered Multi-Provider / Multi-Model Failover (`voice.models`):** Uses `am-ET-MekdesNeural` (`edge-tts`) as primary for native Ethiopian Amharic phonology (`runs.jsonl` lines 165–176), backed by the 3-model Gemini TTS failover chain (`gemini-3.8-flash-tts` → `gemini-3.8-flash-lite-tts` → `gemini-2.5-flash-preview-tts`, verified in `runs.jsonl` lines 71–83).
