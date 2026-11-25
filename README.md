# AI Content Generation — *Abigiya and the Little Star* (`ኮኮቤ`)

A reproducible, contract-driven multi-model AI film pipeline that turns a single validated JSON storyboard (`storyboard.json`) into a 70.0-second short film narrated in **Amharic** with burned-in **English subtitles**, an original Tizita pentatonic lullaby score ducked under the voice, a visible **Made with AI** disclosure end card, and dual exports in **vertical (9:16)** and **horizontal (16:9)** aspect ratios.

---

## One-Command Quickstart

A stranger can clone this repository, provide free-tier Gemini and Cloudflare Workers AI keys in `.env`, and run a single command (`make film`) to validate the schema and generate the complete film from `storyboard.json`:

```bash
git clone https://github.com/yordi68/ai-content-generation.git
cd ai-content-generation
cp .env.example .env
# Edit .env and fill in GEMINI_API_KEY, CLOUDFLARE_ACCOUNT_ID, CLOUDFLARE_API_TOKEN
make film
```

### Prerequisites

- **Python 3.10+** (`make film` automatically creates `.venv` and installs `requirements.txt`: `jsonschema==4.26.0`, `pillow==13.0.0`)
- **FFmpeg** (`brew install ffmpeg` on macOS or `apt install ffmpeg` on Linux)
- **Free API keys in `.env`:**
  - `GEMINI_API_KEY` — from [Google AI Studio](https://aistudio.google.com/) (Free Tier, no payment card required)
  - `CLOUDFLARE_ACCOUNT_ID` and `CLOUDFLARE_API_TOKEN` — from [Cloudflare Workers AI](https://dash.cloudflare.com/) (Free daily allowance)

---

## What `make film` Produces

Running `make film` executes the pipeline stages in order around `storyboard.json`:

| Stage Command | Script | Model / Tool | Output Files |
|---|---|---|---|
| `make validate` | `pipeline/validate.py` | JSON Schema Draft 2020-12 (`jsonschema`) | Validates `storyboard.json` against `schema/storyboard.schema.json` |
| `make narration` | `pipeline/narration.py` | `gemini-3.8-flash-tts` → `gemini-3.8-flash-lite-tts` → `gemini-2.5-flash-preview-tts` | `outputs/narration/shot_01.wav` .. `shot_12.wav` + updates `duration_s` in `storyboard.json` |
| `make keyframes` | `pipeline/keyframes.py` | Cloudflare `@cf/black-forest-labs/flux-1-schnell` (4 steps) | `outputs/keyframes/reference_sheet.jpg` + `shot_01.jpg` .. `shot_12.jpg` |
| `make shots` | `pipeline/shots.py` | FFmpeg `zoompan` (or Wan 2.2 override in `outputs/wan/`) | `outputs/shots/shot_01_9x16.mp4` .. `shot_12_16x9.mp4` (24 clips, 24 fps) |
| `make music` | `pipeline/music.py` | Local Tizita pentatonic lullaby synth (or ACE-Step 1.5 override) | `outputs/music/score.wav` (70.4s stereo WAV) |
| `make assemble` | `pipeline/assemble.py` | FFmpeg (`sidechaincompress` + `loudnorm` -14 LUFS) + Pillow overlays | `outputs/radio_cut.mp4`, `outputs/film_9x16.mp4`, `outputs/film_16x9.mp4` |

---

## Regenerating a Single Shot (Content-Addressed Caching)

Every stage caches its output by a SHA-256 hash of that shot's inputs in a sidecar `.json` file (`outputs/<stage>/shot_XX.json`). If you edit **one** shot's `picture` prompt, `seed`, or `narration` line in `storyboard.json` and re-run `make film`:

1. Unchanged shots print `cached` and make **zero API calls**.
2. Only the modified shot is regenerated and logged to `runs.jsonl`.
3. `pipeline/assemble.py` rebuilds the final MP4s with the updated shot.

---

## Repository Structure

```
.
├── README.md                        # One-command run instructions, overview, and cost summary
├── Makefile                         # Single-command orchestration (`make film`)
├── requirements.txt                 # Pinned Python dependencies (jsonschema, pillow)
├── .env.example                     # Environment variable template (no secrets committed)
├── storyboard.json                  # The contract between all stages (12 shots, prompts, cues)
├── schema/
│   └── storyboard.schema.json       # JSON Schema validated before every stage run
├── pipeline/
│   ├── validate.py                  # Validates storyboard.json against schema/storyboard.schema.json
│   ├── runlog.py                    # Appends every model call to runs.jsonl + tracks daily quota
│   ├── narration.py                 # Gemini TTS synthesis with 20s RPM pacing & 3-model failover
│   ├── keyframes.py                 # Reference sheet + 12 FLUX.1-schnell keyframes on Cloudflare
│   ├── shots.py                     # Moving shots in 9:16 and 16:9 via FFmpeg zoompan / Wan 2.2
│   ├── music.py                     # Tizita pentatonic lullaby score / ACE-Step 1.5 loader
│   └── assemble.py                  # Sidechain ducking, -14 LUFS loudnorm, subtitles, AI end card
├── runs.jsonl                       # Complete structured log of every model call, latency & cost
├── outputs/                         # Generated audio, keyframes, shots, and final MP4 exports
├── DESIGN.md                        # Audience, intent, story arc, and user test records
├── ARCHITECTURE.md                  # Stage contracts, SHA-256 caching, and quota failover design
├── EXPERIMENTS.md                   # 11 logged hypothesis -> change -> result experiments
├── FAILURES.md                      # Real blockers encountered (quotas, language, headers) & fixes
├── COSTS.md                         # Measured latency, compute minutes, quotas & list-price costs
└── ETHICS.md                        # Consent record, model licences, privacy & AI labelling plan
```

---

## Cost Summary

- **Actual out-of-pocket cost:** **$0.00** (runs entirely on Google AI Studio Free Tier, Cloudflare Workers AI Free Tier, and local FFmpeg/Python).
- **Active compute time for one full 12-shot build:** `174.6s` (`1.58` hosted GPU minutes + `1.33` local CPU minutes), plus `220s` of 3-RPM rate-limit pacing during uncached Gemini TTS synthesis.
- **Commercial list-price equivalent:** **~$0.060 USD** per full 12-shot film regeneration (`~$0.146 USD` across all 118 logged development calls in `runs.jsonl`). See [`COSTS.md`](COSTS.md) for the full stage-by-stage breakdown.
