# Costs, Latencies, and Free-Tier Quota Measurements

All numbers below are aggregated directly from `runs.jsonl` across our development, iterations, and final 12-shot film build (*Abigiya and the Little Star*, 70.0s runtime).

---

## 1. Free-Tier Limits Actually Discovered (November 2026)

| Provider & Model | Published / Discovered Free-Tier Limit | What I Observed in Practice |
|---|---|---|
| **Google AI Studio (`gemini-3.8-flash-tts`)** | **3 RPM** (requests/minute), **10 RPD** (requests/day), **10K TPM** | A 12-shot film cannot finish on one model in a single day without hitting HTTP 429 on shot 11. Failed 429 retries also increment the counter on the rate-limit dashboard (`13 / 10 RPD` observed). Resets at midnight Pacific Time (~10:00–11:00 EAT). |
| **Google AI Studio (`gemini-3.8-flash-lite-tts`)** | **3 RPM**, **10 RPD**, **10K TPM** (independent bucket) | Separate 10 RPD bucket from `gemini-3.8-flash-tts`. Generated 9 shots at `3.80s` avg latency before hitting its own 10 RPD limit. |
| **Google AI Studio (`gemini-2.5-flash-preview-tts`)** | **3 RPM**, **10 RPD**, **10K TPM** (independent bucket) | Separate 10 RPD bucket. Returns raw 24 kHz 16-bit mono PCM (`audio/L16;rate=24000`) without a RIFF WAV header. |
| **Google AI Studio (`gemini-3.8-flash`)** | **5 RPM**, **20 RPD**, **250K TPM** | First smoke-test call experienced a `137.51s` cold-start/queue spike. |
| **Cloudflare Workers AI (`@cf/black-forest-labs/flux-1-schnell`)** | **10,000 Neurons / day** free (~50–170 images/day at 4 steps) | Fast and reliable (`3.61s` average per 1024×1024 image at 4 steps). Rejects `/seed` in the JSON body with HTTP 400 (`code: 5006`). |
| **Edge Neural TTS (`am-ET-MekdesNeural`)** | Free endpoint, no 10 RPD cap | Generated all 12 Amharic shots in `41.79s` total (`3.48s` avg per shot) with native Ethiopian Amharic pronunciation. |
| **Local CPU TTS (`piper-tts` `en_US-lessac-medium`)** | Unlimited (runs locally on CPU) | Synthesized all 12 English shots in `2.85s` total wall time on Apple Silicon CPU ($0.00). |

---

## 2. Measured Latency and Compute Time per Stage (Single Full 12-Shot Film Run)

| Stage | Model / Tool | Calls per Film | Total Model Latency (s) | Avg Latency per Call (s) | Hosted GPU / CPU Minutes | Actual Out-of-Pocket Cost | List-Price Equivalent (USD) |
|---|---|---|---|---|---|---|---|
| **1. Narration (Primary + Failover)** | `gemini-3.8-flash-lite-tts` (9 shots) + `gemini-2.5-flash-preview-tts` (3 shots) | 12 | `48.20s` (+ `220s` RPM pacing wait) | `4.02s` | `0.80` hosted GPU min | **$0.00** (Free Tier) | ~$0.015 (at ~$15 / 1M audio tokens) |
| **1b. Narration Benchmark (Ethiopian Amharic)** | `am-ET-MekdesNeural` (`edge-tts`) | 12 | `41.79s` (no pacing wait needed) | `3.48s` | `0.70` cloud TTS min | **$0.00** (Free) | ~$0.012 (at $16 / 1M chars, ~750 chars) |
| **2. Keyframes (Ref sheet + 12 shots)** | Cloudflare `@cf/black-forest-labs/flux-1-schnell` (4 steps) | 13 | `46.93s` | `3.61s` | `0.78` hosted GPU min | **$0.00** (Free Tier) | ~$0.039 (13 images × $0.003/image) |
| **3. Moving Shots (12 shots × 2 ratios)** | Local FFmpeg `zoompan` (720×1280 & 1280×720, 24 fps) | 24 | `29.44s` | `1.23s` | `0.49` local CPU min | **$0.00** (Local) | ~$0.002 (equivalent cloud CPU encode) |
| **4. Original Score (70.4s track)** | `local-tizita-lullaby-synth-v1` (or ACE-Step 1.5 override) | 1 | `3.36s` | `3.36s` | `0.06` local CPU min | **$0.00** (Local) | ~$0.001 |
| **5. Final Assembly (`radio_cut`, `9:16`, `16:9`)** | FFmpeg (`sidechaincompress` + `loudnorm` + Pillow subtitle/card overlays) | 1 run (3 MP4s) | `46.68s` | `46.68s` | `0.78` local CPU min | **$0.00** (Local) | ~$0.005 |
| **Total (One Full Film Build)** | **End-to-End Pipeline (`make film`)** | **50 stage units** | **`174.61s` active compute** | — | **`1.58` hosted GPU min + `1.33` local CPU min** | **$0.00** | **~$0.060 / film** |

---

## 3. Cumulative Development & Experimentation Totals (All Calls in `runs.jsonl`)

Across all story iterations, language switches, quota failover tests, and full assemblies logged in `runs.jsonl`:

| Stage | Model / Tool | Successful Calls | Error / Quota 429 Calls | Total Active Latency (s) | List-Price Equivalent (USD) |
|---|---|---|---|---|---|
| `smoke_test` | `gemini-3.8-flash` | 1 | 0 | `137.51s` | $0.0001 |
| `smoke_test` | `gemini-3.8-flash-tts` | 1 | 0 | `4.29s` | $0.001 |
| `smoke_test` | `@cf/black-forest-labs/flux-1-schnell` | 1 | 0 | `3.41s` | $0.003 |
| `narration` | `gemini-3.8-flash-tts` | 45 | 15 (HTTP 429) | `264.51s` | $0.056 |
| `narration` | `gemini-3.8-flash-lite-tts` | 9 | 1 (HTTP 429) | `35.02s` | $0.011 |
| `narration` | `gemini-2.5-flash-preview-tts` | 9 | 1 (HTTP 429) | `41.05s` | $0.011 |
| `narration_benchmark` | `am-ET-MekdesNeural` | 12 | 0 | `41.79s` | $0.012 |
| `keyframes` | `@cf/black-forest-labs/flux-1-schnell` | 13 | 3 (HTTP 400 `/seed`) | `49.14s` | $0.039 |
| `shots` | `ffmpeg-zoompan-*` | 24 | 0 | `29.44s` | $0.002 |
| `music` | `local-tizita-lullaby-synth-v1` | 1 | 0 | `3.36s` | $0.001 |
| `assemble` | `ffmpeg-sidechain-loudnorm-overlay` | 2 | 0 | `93.36s` | $0.010 |
| **Grand Total** | **All logged runs** | **118 ok** | **20 errors** | **`702.88s` (`11.71 min`)** | **~$0.146 USD** |

---

## 4. Open vs. Commercial / Frontier Comparison

- **Moving Shots (FFmpeg Ken Burns `zoompan` vs. Wan 2.2 TI2V-5B / Frontier Video API):**
  - Generating 24 clips (12 shots × 2 aspect ratios) via FFmpeg `zoompan` took `29.44s` total on local CPU (`1.23s`/clip) with deterministic framing and zero identity drift.
  - By comparison, generating twelve 5-second 720p clips on Wan 2.2 TI2V-5B on a free T4 GPU takes ~6–10 minutes per clip (~75–120 GPU minutes total), and commercial frontier video APIs (Runway Gen-3 / Veo / Omni Flash) cost ~$0.25–$0.50 per 5-second clip (~$3.00–$6.00 for a 12-shot film).
- **Amharic Narration (Gemini 3.8/2.5 TTS vs. `am-ET-MekdesNeural` vs. Local `piper-tts`):**
  - Gemini TTS is free up to 10 RPD per model (`4.02s` avg latency), speaks Amharic script after stripping English style prefixes, but exhibits an American English phonological accent.
  - `am-ET-MekdesNeural` (`edge-tts`) is slightly faster (`3.48s` avg latency), has no 10 RPD cap, and pronounces Amharic with a native Ethiopian accent.
  - Local `piper-tts` on CPU is 15× faster (`0.24s`/shot, `2.85s` for 12 shots) and completely offline, but currently lacks an open-weight Amharic voice checkpoint.
