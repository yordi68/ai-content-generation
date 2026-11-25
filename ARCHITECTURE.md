# Architecture

## Overview

This repository is a code-driven short-film studio built around a single contract file: `storyboard.json`. Every stage in `pipeline/` reads `storyboard.json`, validates it against `schema/storyboard.schema.json`, checks its local SHA-256 content cache, calls its model or tool only for shots whose inputs changed, logs every call to `runs.jsonl`, and writes its outputs to `outputs/`.

```
                       +-------------------------------+
                       |        storyboard.json        |
                       |   (Validated against Schema)  |
                       +---------------+---------------+
                                       |
         +--------------+--------------+--------------+--------------+
         |              |              |              |              |
         v              v              v              v              v
  +-------------+ +-------------+ +-------------+ +-------------+    |
  | narration.py| | keyframes.py| |   shots.py  | |   music.py  |    |
  | Gemini TTS  | | Cloudflare  | | FFmpeg /    | | Tizita Synth|    |
  | (3-model    | | FLUX.1      | | Wan 2.2     | | / ACE-Step  |    |
  |  failover)  | | schnell     | | zoompan     | | 1.5 override|    |
  +------+------+ +------+------+ +------+------+ +------+------+    |
         |               |               |               |           |
         +---------------+-------+-------+---------------+           |
                                 |                                   |
                                 v                                   |
                         +---------------+                           |
                         |  assemble.py  |<--------------------------+
                         | Sidechain duck|
                         | -14 LUFS norm |
                         | Subtitles+Card|
                         +-------+-------+
                                 |
            +--------------------+--------------------+
            |                    |                    |
            v                    v                    v
   outputs/radio_cut.mp4  outputs/film_9x16.mp4  outputs/film_16x9.mp4
```

## Stage Boundaries and Contracts

1. **`pipeline/validate.py` — Contract Gate**
   - Validates `storyboard.json` against `schema/storyboard.schema.json` (JSON Schema Draft 2020-12) before any stage runs.
   - Enforces required film-level fields (`title`, `aspect_ratios`, `style_block`, `character`, `voice`, `music`, `shots`) and per-shot fields (`id`, `narration`, `subtitle`, `picture`, `motion`, `duration_s`, `seed`, `reason`), with 8–12 shots.

2. **`pipeline/narration.py` — Voice Synthesis and Timing Spine**
   - Reads each shot's Amharic `narration` and `voice` settings from `storyboard.json`.
   - Synthesizes one WAV file per shot (`outputs/narration/shot_XX.wav`) and measures its exact frame duration (`frames / sample_rate`).
   - Updates `shot["duration_s"]` in `storyboard.json` (`round(seconds / tempo + 0.5, 1)`) so picture cuts follow the voice track.
   - Wraps raw PCM audio streams in a standard RIFF WAV header when a fallback model returns headerless PCM.

3. **`pipeline/keyframes.py` — Character Sheet and Keyframe Generation**
   - Generates `outputs/keyframes/reference_sheet.jpg` first using the locked `style_block` and `character` descriptions.
   - Generates `outputs/keyframes/shot_01.jpg` through `shot_12.jpg` via Cloudflare Workers AI (`@cf/black-forest-labs/flux-1-schnell`, 4 steps).
   - Appends the film-level `style_block` and `character` strings to every shot's `picture` prompt and enforces center-framed square composition so both 9:16 vertical and 16:9 horizontal crops keep the subject inside safe margins.

4. **`pipeline/shots.py` — Moving Shots (Ken Burns / Wan 2.2 TI2V)**
   - For each shot and each target aspect ratio (`9:16` at `720x1280` and `16:9` at `1280x720`, 24 fps):
     - If an external Wan 2.2 clip exists at `outputs/wan/shot_XX.mp4`, scales and trims it to `shot["duration_s"]`.
     - Otherwise, animates `outputs/keyframes/shot_XX.jpg` using FFmpeg's `zoompan` filter according to `shot["motion"]["type"]` (`push-in`, `pull-out`, `pan-left`, `pan-right`, `none`).

5. **`pipeline/music.py` — Original Score**
   - Reads the music cue and total duration from `storyboard.json`.
   - If an ACE-Step 1.5 track is placed at `outputs/music/ace_step_chosen.wav`, uses it directly; otherwise synthesizes a warm Ethiopian Tizita pentatonic krar-and-pad lullaby underscore (`outputs/music/score.wav`) so `make film` succeeds deterministically on any machine without a GPU.

6. **`pipeline/assemble.py` — Mixing, Ducking, Subtitles, Loudness, and Dual Export**
   - Applies voice `tempo` (`atempo`) and pads each shot's narration to its exact `duration_s`, concatenating all 12 shots plus a 2.6-second silence tail for the end card into `outputs/build/voice_stem.wav`.
   - Ducks the musical score under the narration using FFmpeg's `sidechaincompress` (`threshold=0.02:ratio=6:attack=300:release=1500`) and normalizes the final master mix to EBU R128 `-14.0 LUFS` with `-1.0 dBTP` true peak using `loudnorm`.
   - Renders burned-in English subtitle overlays (wrapped inside vertical and horizontal safe areas) and the required `"Made with AI"` disclosure end card using `Pillow`, compositing them via FFmpeg's `overlay` filter so standard FFmpeg builds without `libass`/`drawtext` work out of the box.
   - Exports `outputs/radio_cut.mp4`, `outputs/film_9x16.mp4`, and `outputs/film_16x9.mp4`.

## Content-Addressed Caching (Partial Re-Runs)

Every stage computes a SHA-256 `cache_key` over the exact inputs that determine a shot's output and saves it in a sidecar JSON file (`shot_XX.json`):

- **Narration cache key:** `SHA256({narration, primary_model, voice_name, prompt_mode})`
- **Keyframes cache key:** `SHA256({model, composed_prompt, seed, steps})`
- **Moving shots cache key:** `SHA256({keyframe_file_sha256, motion, duration_s, aspect, fps})`
- **Music cache key:** `SHA256({cue, duration_s})`

When I edit a single shot's `picture` prompt or `narration` line in `storyboard.json` and run `make film`:
1. The other 11 shots match their sidecar `cache_key` and print `cached`.
2. Only the modified shot calls the model API and re-renders its moving clip.
3. `assemble.py` stitches the updated shot into the final MP4s.

## Quota Pacing, Daily Budget Tracking, and Multi-Model Failover

Free-tier Gemini TTS models enforce two separate rate limits:
- **3 Requests Per Minute (RPM)**
- **10 Requests Per Day (RPD)** per model per project

Because a 12-shot film exceeds a single model's 10 RPD limit, `pipeline/narration.py` and `pipeline/runlog.py` implement three safeguards:
1. **Request Pacing (`pace()`):** Enforces a minimum 20-second gap between consecutive Gemini TTS requests so the 3 RPM limit is never breached.
2. **Per-Key, Per-Model Daily Budget Tracking (`requests_today()`):** Parses `runs.jsonl` in the `America/Los_Angeles` quota timezone (tagged by an 8-character SHA-256 fingerprint of the active API key, never storing the secret key) and skips a model as soon as it reaches 10 requests for the day.
3. **Ordered Multi-Model Failover Chain (`voice.models`):** Tries `gemini-3.8-flash-tts`, then `gemini-3.8-flash-lite-tts`, then `gemini-2.5-flash-preview-tts`. On HTTP 429 daily quota exhaustion, it immediately switches to the next model without wasting quota on retries. On subsequent runs after the daily reset, it automatically upgrades fallback clips to the primary model when quota is available.
