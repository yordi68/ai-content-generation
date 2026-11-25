# Costs, Latencies, and Free-Tier Quota Measurements

All numbers below are computed directly from the **215 lines** in `runs.jsonl` (`195 ok`, `20 error`, `1,368.89s` total logged active latency) across our development, iterations, and final 12-shot film build (*Abigiya and the Little Star*, **`65.0s`** finished film runtime, **`62.4s`** across the 12 shots + **`2.6s`** AI disclosure end card, **`65.4s`** musical score).

---

## 1. Free-Tier Limits Actually Discovered (November 2026)

| Provider & Model | Published / Discovered Free-Tier Limit | What I Observed in Practice (`runs.jsonl` Evidence) |
|---|---|---|
| **Google AI Studio (`gemini-3.8-flash-tts`)** | **3 RPM** (requests/minute), **10 RPD** (requests/day), **10K TPM** | A 12-shot film cannot finish on one model in a single day without hitting HTTP 429 on Shot 7–11 (`runs.jsonl` lines 10–12, `07:36:18Z`, and lines 32–34, `07:58:11Z`). Failed 429 retries also increment the counter on the rate-limit dashboard (`13 / 10 RPD` observed). Resets at midnight Pacific Time (~10:00–11:00 EAT). |
| **Google AI Studio (`gemini-3.8-flash-lite-tts`)** | **3 RPM**, **10 RPD**, **10K TPM** (independent bucket) | Separate 10 RPD bucket from `gemini-3.8-flash-tts`. Generated Shots 1–9 (`runs.jsonl` lines 71–79, `13:01:40Z`–`13:04:19Z`, `3.80s` avg latency) before hitting its own 10 RPD limit on Shot 10 (line 80, `13:04:37Z`). |
| **Google AI Studio (`gemini-2.5-flash-preview-tts`)** | **3 RPM**, **10 RPD**, **10K TPM** (independent bucket) | Separate 10 RPD bucket. Completed Shots 10–12 (`runs.jsonl` lines 81–83, `13:05:01Z`–`13:05:40Z`). Returns raw 24 kHz 16-bit mono PCM (`audio/L16;rate=24000`) without a RIFF WAV header. |
| **Google AI Studio (`gemini-3.8-flash`)** | **5 RPM**, **20 RPD**, **250K TPM** | First smoke-test call experienced a `137.51s` cold-start/queue spike (`runs.jsonl` line 1, `04:12:00Z`). |
| **Cloudflare Workers AI (`@cf/black-forest-labs/flux-1-schnell`)** | **10,000 Neurons / day** free (~50–170 images/day at 4 steps) | Rejects `/seed` in the JSON body with HTTP 400 (`code: 5006`, `runs.jsonl` lines 85–87, `13:50:03Z`–`13:50:13Z`). Pass 1 (13 images, lines 88–100) averaged `3.61s`/image (`46.93s` total); Pass 2 (13 images during peak queue, lines 177–189) averaged `36.15s`/image (`469.96s` total). |
| **Edge Neural TTS (`am-ET-MekdesNeural`)** | Free endpoint, no 10 RPD cap | Generated all 12 Amharic shots under `stage: "narration"` in `27.65s` total (`2.30s` avg per shot, `runs.jsonl` lines 165–176, `16:50:01Z`–`16:50:26Z`) with native Ethiopian Amharic pronunciation. |
| **Local CPU TTS (`piper-tts` `en_US-lessac-medium`)** | Unlimited (runs locally on CPU) | Synthesized all 12 English shots on the `local-voice` branch (`commit 522ad2a`) in `2.85s` total wall time on Apple Silicon CPU ($0.00). |

---

## 2. Measured Latency and Compute Time per Stage (Final `v2` 12-Shot Film Build)

The table below shows the exact measured numbers from the final `v2` build (`runs.jsonl` **lines 165–215**) that produced the shipped **`65.0s`** film (`outputs/film_9x16.mp4`, `outputs/film_16x9.mp4`, and `outputs/radio_cut.mp4`):

| Stage | Model / Tool | `runs.jsonl` Lines | Calls | Total Measured Latency (s) | Avg Latency / Call (s) | Hosted GPU / Local CPU Minutes | Actual Out-of-Pocket Cost | Logged `list_price_usd` (+ Commercial Estimate) |
|---|---|---|---|---|---|---|---|---|
| **1. Narration (`narration-v2`)** | `am-ET-MekdesNeural` (`edge-tts`) | `L165–L176` | 12 | `27.65s` (`56.27s` audio; `62.4s` with `0.5s` pauses) | `2.30s` | `0.46` cloud TTS min | **$0.00** | `$0.000` logged (~$0.012 est. at $16/1M chars) |
| **1b. Narration (Gemini Failover Run)** | `gemini-3.8-flash-lite-tts` (9) + `gemini-2.5-flash-preview-tts` (3) | `L71–L79`, `L81–L83` | 12 | `48.13s` (+ `220s` RPM pacing wait) | `4.01s` | `0.80` hosted GPU min | **$0.00** | `null` logged (~$0.015 est. at $15/1M audio tokens) |
| **2. Keyframes (`keyframes-v2`)** | Cloudflare `@cf/black-forest-labs/flux-1-schnell` (4 steps) | `L177–L189` (v1: `L88–L100`) | 13 | `469.96s` (v1 fast queue: `46.93s`) | `36.15s` (v1: `3.61s`) | `7.83` queue+GPU min (v1: `0.78` min) | **$0.00** | **`$0.039`** logged (`13 × $0.003`) |
| **3. Moving Shots (`shots-v2`)** | Local FFmpeg `zoompan` (`9:16` & `16:9`, 24 fps) | `L190–L213` | 24 | `34.35s` | `1.43s` | `0.57` local CPU min | **$0.00** | `$0.000` logged (~$0.002 est. cloud CPU) |
| **4. Original Score (`music-v2`, `65.4s`)** | `local-tizita-lullaby-synth-v1` | `L214` | 1 | `3.12s` | `3.12s` | `0.05` local CPU min | **$0.00** | `$0.000` logged (~$0.001 est.) |
| **5. Final Assembly (`65.0s` MP4s)** | `ffmpeg-sidechain-2pass-loudnorm-overlay` | `L215` | 1 (3 MP4s) | `50.06s` | `50.06s` | `0.83` local CPU min | **$0.00** | `$0.000` logged (~$0.005 est.) |
| **Total (Final `v2` Build, `L165–L215`)** | **End-to-End Pipeline (`make film`)** | **`L165–L215`** | **51 calls** | **`585.14s` (or `162.11s` at v1 FLUX speed)** | — | **`0.46` TTS + `7.83` FLUX + `1.45` local CPU min** | **$0.00** | **`$0.039` logged (~$0.059 est. commercial)** |

---

## 3. Exact Cumulative Totals Across All 215 Lines in `runs.jsonl`

Every row below is verified directly by grouping all **215 lines** (`195 ok`, `20 error`) of `runs.jsonl` by `(stage, model, status)`:

| Stage | Model / Tool | Status | Line Range in `runs.jsonl` | Call Count | Total Latency (s) | Avg Latency (s) | Sum of `cost.list_price_usd` Stored in `runs.jsonl` |
|---|---|---|---|---|---|---|---|
| `smoke_test` | `gemini-3.8-flash` | `ok` | `L1` | 1 | `137.51s` | `137.51s` | `$0.000` (`null`) |
| `smoke_test` | `gemini-3.8-flash-tts` | `ok` | `L2` | 1 | `4.29s` | `4.29s` | `$0.000` (`null`) |
| `smoke_test` | `@cf/black-forest-labs/flux-1-schnell` | `ok` | `L3` | 1 | `3.41s` | `3.41s` | `$0.000` (`null`) |
| `narration` | `gemini-3.8-flash-tts` | `ok` | `L4–L70` | 45 | `249.76s` | `5.55s` | `$0.000` (`null`) |
| `narration` | `gemini-3.8-flash-tts` | `error` | `L10–L60` | 15 | `14.75s` | `0.98s` | `$0.000` |
| `narration` | `gemini-2.5-flash-preview-tts` | `ok` | `L20–L83` | 9 | `40.53s` | `4.50s` | `$0.000` (`null`) |
| `narration` | `gemini-2.5-flash-preview-tts` | `error` | `L30` | 1 | `0.52s` | `0.52s` | `$0.000` |
| `narration` | `gemini-3.8-flash-lite-tts` | `ok` | `L71–L79` | 9 | `34.23s` | `3.80s` | `$0.000` (`null`) |
| `narration` | `gemini-3.8-flash-lite-tts` | `error` | `L80` | 1 | `0.79s` | `0.79s` | `$0.000` |
| `narration_benchmark` | `am-ET-MekdesNeural` | `ok` | `L127–L138` | 12 | `41.79s` | `3.48s` | `$0.000` |
| `narration` | `am-ET-MekdesNeural` | `ok` | `L165–L176` | 12 | `27.65s` | `2.30s` | `$0.000` |
| `keyframes` | `@cf/black-forest-labs/flux-1-schnell` | `error` | `L85–L87` | 3 | `2.21s` | `0.74s` | `$0.000` |
| `keyframes` | `@cf/black-forest-labs/flux-1-schnell` | `ok` | `L88–L100`, `L177–L189` | 26 | `516.89s` | `19.88s` | **`$0.078`** (`26 × $0.003`) |
| `shots` | `ffmpeg-zoompan-push-in` | `ok` | `L101–L211` | 36 | `60.25s` | `1.67s` | `$0.000` |
| `shots` | `ffmpeg-zoompan-pan-right` | `ok` | `L102–L212` | 12 | `15.98s` | `1.33s` | `$0.000` |
| `shots` | `ffmpeg-zoompan-pan-left` | `ok` | `L105–L210` | 12 | `13.77s` | `1.15s` | `$0.000` |
| `shots` | `ffmpeg-zoompan-pull-out` | `ok` | `L107–L208` | 6 | `5.69s` | `0.95s` | `$0.000` |
| `shots` | `ffmpeg-zoompan-none` | `ok` | `L112–L213` | 6 | `3.68s` | `0.61s` | `$0.000` |
| `music` | `local-tizita-lullaby-synth-v1` | `ok` | `L84`, `L163`, `L214` | 3 | `9.62s` | `3.21s` | `$0.000` |
| `assemble` | `ffmpeg-sidechain-loudnorm-overlay` | `ok` | `L125`, `L126`, `L164` | 3 | `135.51s` | `45.17s` | `$0.000` |
| `assemble` | `ffmpeg-sidechain-2pass-loudnorm-overlay` | `ok` | `L215` | 1 | `50.06s` | `50.06s` | `$0.000` |
| **Grand Total** | **All 215 lines in `runs.jsonl`** | **`195 ok`, `20 error`** | **`L1–L215`** | **215** | **`1,368.89s` (`22.81 min`)** | — | **`$0.078` stored in file (~$0.195 est. with TTS)** |

---

## 4. Open / Local vs. Commercial Frontier Comparison (Measured vs. Estimated)

- **Moving Shots — Measured Local FFmpeg `zoompan` vs. Estimated Wan 2.2 / Frontier Video APIs:**
  - *Measured in this repo (`runs.jsonl` lines 190–213):* Generating 24 moving clips (12 shots × 2 aspect ratios) via FFmpeg `zoompan` took `34.35s` total on local CPU (`1.43s`/clip) with deterministic framing and zero intra-shot morphing.
  - *Estimated GPU / Frontier equivalent (not run in `runs.jsonl`):* Generating twelve 5-second 720p clips with Wan 2.2 TI2V-5B on a free Kaggle T4 GPU requires ~6–10 GPU minutes per clip (~75–120 GPU minutes total), and commercial frontier video APIs (Runway Gen-3 / Veo / Omni Flash) list at ~$0.25–$0.50 per 5-second clip (~$3.00–$6.00 for a 12-shot film).
- **Amharic Narration — Measured 3-Way Comparison:**
  - *Gemini TTS (`runs.jsonl` lines 71–83):* Free up to 10 RPD per model (`4.01s` avg latency + `20s` RPM pacing wait), reads Amharic script after stripping English style prefixes, but speaks with an American English phonological accent.
  - *Edge Neural TTS `am-ET-MekdesNeural` (`runs.jsonl` lines 165–176):* Faster (`2.30s` avg latency, `27.65s` total for all 12 shots, no 20s pacing delay needed), and speaks Amharic with a native Ethiopian accent.
  - *Local CPU `piper-tts` (`local-voice` branch, `commit 522ad2a`):* `2.85s` total wall time for all 12 English shots on CPU (`0.24s`/shot, 100% offline), but currently has no open-weight Amharic voice checkpoint.
