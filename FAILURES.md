# Failure Journal — What Broke, What I Tried, and What Fixed It

---

## 0. Generating 12 Isolated Shot Statements Instead of a Connected Story

When I first started drafting the script to match the brief's 8–12 shot requirement, I went with 12 shots and generated 12 separate one-line statements. When I read and listened to those 12 statements back-to-back, they did not tell a unified story—they sounded like 12 disconnected bullet points. If the story is fragmented, no amount of visual polish makes a good film.
- **What I changed:** I wrote the entire narrative as a single continuous story paragraph first, read it aloud to verify the emotional bridges between beats, and only then divided it into 12 connected shots in `storyboard.json` (`commit 522ad2a` on `local-voice` and `commit d32e9de` on `main`).

---

## 1. Narration Stage: Plain-Language Summary of the Quota & Voice Journey

I wanted the narrator to sound like one steady storyteller from the first line to the last. The free Google Gemini voice (`gemini-3.8-flash-tts`, voice `Kore`) sounded warm on English, but I hit a hard wall halfway through generating the 12 shots: the requests failed with `HTTP 429 Too Many Requests` (`runs.jsonl` line 10, `2026-11-25T07:36:18Z`).

Here is the thought process I went through and the trade-offs of each solution I tested:

1. **Adjusting delivery pace and tempo (`unhurried` → `a little brisker` + `atempo`):**
   - My first English narration run projected to ~100 seconds (`runs.jsonl` lines 4–9, `07:35:50Z`–`07:36:18Z`), exceeding the brief's 90-second maximum. Switching the style prompt to `"calm, warm, a little brisker"` (`runs.jsonl` lines 13–17, `07:39:54Z`–`07:40:14Z`) and applying `atempo=1.08` brought the duration inside the 60–90 second target.
2. **Evaluating Cross-Provider Voice Cloning vs. Multi-Model Failover:**
   - When `gemini-3.8-flash-tts` ran out of quota after 6–10 shots, I considered cross-provider voice cloning (cloning one reference voice across ElevenLabs, Cartesia, and Gemini). I rejected voice cloning for four reasons:
     - **Consent gate:** Cloning requires recording a real person's voice and documenting written consent in `ETHICS.md`, whereas my film was designed around fictional characters and synthetic voices.
     - **Cost:** Free tiers on commercial voice-cloning APIs do not support custom Amharic voice clones without paid billing.
     - **Voice mismatch:** Even trained on the same sample, different providers' prosody and Amharic phoneme handling differ.
     - **Time:** Setting up and verifying multi-provider clones would take days rather than hours.
3. **Testing a Local Open-Weight CPU Voice (`piper-tts` on the `local-voice` branch):**
   - To eliminate cloud quotas completely, I created the `local-voice` git branch and ran `piper-tts` (`en_US-lessac-medium.onnx`) locally on CPU. It synthesized all 12 English shots in `2.85s` total with zero quota limits, but its default speech was only `36.49s` (too fast for a 60–90s film), slowing `length_scale` to `1.7–2.3` sounded noticeably stretched, and Piper has no open-weight Amharic model.
4. **Solving the Gemini Quota with Pacing + 3-Model Failover, Then Solving Amharic Phonology:**
   - By inspecting the full 429 JSON error body (`runs.jsonl` line 32, `07:58:11Z`) and the Google AI Studio rate-limit dashboard, I discovered that each Gemini TTS model enforces **3 requests per minute (RPM)** and **10 requests per day (RPD)** independently.
   - Adding a 20-second pacing delay between calls (`pace()`) eliminated RPM 429 errors, and chaining `gemini-3.8-flash-tts` → `gemini-3.8-flash-lite-tts` → `gemini-2.5-flash-preview-tts` allowed all 12 shots to finish in one run (`runs.jsonl` lines 71–83, `13:01:40Z`–`13:05:40Z`).
   - Finally, when native listening revealed that Gemini TTS spoke Amharic with an American English accent, I integrated native Ethiopian Amharic neural TTS (`am-ET-MekdesNeural` via `edge-tts`, logged under `stage: "narration"` in `runs.jsonl` lines 165–176, `16:50:01Z`–`16:50:26Z`) as the primary voice in `storyboard.json` while keeping the 3-model Gemini TTS failover chain intact.

---

## 2. Detailed Technical Log of Failures and Resolutions

### Entry 1: Cold-Start Latency Spike on `gemini-3.8-flash` (`137.51s`)
- **Evidence:** `runs.jsonl` line 1 (`2026-11-25T04:12:00Z`).
- **What broke:** The initial smoke-test text generation call to `gemini-3.8-flash` took `137.51s` (`2m 17.5s`) to return the single word `"ready"`.
- **Resolution:** Added explicit HTTP timeouts (`TIMEOUT_S = 180` in `narration.py`, `120` in `keyframes.py`) and structured retry handling so a stalled request never hangs the pipeline indefinitely.

### Entry 2: Gemini TTS HTTP 429 Quota Exhaustion (3 RPM and 10 RPD Limits)
- **Evidence:** `runs.jsonl` lines 10–12 (`2026-11-25T07:36:18Z`–`07:36:36Z`) and lines 32–34 (`07:58:11Z`–`07:58:36Z`).
- **What broke:** After 6 clips, `gemini-3.8-flash-tts` rejected Shot 7 with `HTTP Error 429: Too Many Requests`. Blind retries failed in `0.62s–1.25s` and burned daily quota on the AI Studio dashboard (`13 / 10 RPD` and `5 / 3 RPM` recorded).
- **Resolution:**
  1. Logged the full HTTP 429 response body (`runs.jsonl` line 32), which revealed: `Quota exceeded for metric: generativelanguage.googleapis.com/generate_content_free_tier_requests, limit: 10, model: gemini-3.8-flash-tts, description: Generate content requests per day limit exceeded on Free Tier.`
  2. Added `pace()` (`MIN_GAP_S = 20`) in `pipeline/narration.py` to stay under 3 RPM.
  3. Added `requests_today(model, key_id)` in `pipeline/runlog.py` (using `America/Los_Angeles` quota reset boundaries and an 8-char SHA-256 key fingerprint) to skip any model at 10/10 RPD and immediately switch models on `"per day"` 429 errors without retrying.

### Entry 3: Headerless Raw PCM Audio from `gemini-2.5-flash-preview-tts` Crashed `wave.open()`
- **Evidence:** `pipeline/narration.py` (`to_wav()`).
- **What broke:** When Shot 6 failed over from `gemini-3.8-flash-tts` to `gemini-2.5-flash-preview-tts`, the API returned raw 16-bit mono PCM audio (`audio/L16;rate=24000`) without a `RIFF` WAV header, crashing `wave.open()` with `wave.Error: file does not start with RIFF id`.
- **Resolution:** Added `to_wav(mime, audio)` in `pipeline/narration.py`, which checks `if audio[:4] == b"RIFF":` and wraps raw PCM bytes in a valid 16-bit mono RIFF WAV container at the sample rate parsed from `mimeType` (`24000 Hz`).

### Entry 4: Voice Pacing Discrepancy Between Primary (`3.8-flash-tts`) and Fallback (`2.5-flash-preview-tts`)
- **Evidence:** `runs.jsonl` lines 13–17 (`3.8-flash-tts`: `6.36s–9.64s`/shot) vs. lines 20–28 (`2.5-flash-preview-tts`: `3.17s–5.21s`/shot).
- **What broke:** When a run split across `3.8-flash-tts` (Shots 1–5) and `2.5-flash-preview-tts` (Shots 6–10), the fallback model spoke ~35% faster, causing a noticeable shift in cadence mid-film.
- **Resolution:** Added automatic primary-upgrade logic in `generate()` so cached fallback clips upgrade to the primary model when quota is available (`runs.jsonl` lines 35–45, `08:41:28Z`–`08:43:29Z`), and ultimately unified all 12 shots on `am-ET-MekdesNeural` (`runs.jsonl` lines 165–176).

### Entry 5: First Unified Single-Model Run Exceeded 90 Seconds (`96.8s` / `112.6s`)
- **Evidence:** `runs.jsonl` lines 35–45 (`08:41:28Z`–`08:43:29Z`, English draft `96.8s` with pauses) and lines 59–70 (`12:44:02Z`–`12:50:13Z`, first Abigiya Amharic draft `112.6s` across Shots 1–10 alone, with Shot 8 taking `20.46s` at line 68, `12:49:36Z`).
- **What broke:** Both the unhurried English narration and the first verbose Amharic Abigiya draft exceeded the brief's 60–90 second runtime ceiling.
- **Resolution:** Tightened the Amharic sentence phrasing across Shots 1, 2, 5, 6, and 8 in `storyboard.json` and added `validate.py` runtime enforcement (`60.0s <= total_s <= 90.0s`). The final film runs exactly **`65.0s`** (`62.4s` across 12 shots + `2.6s` end card).

### Entry 6: Single Fallback Model Also Exhausted at Shot 11
- **Evidence:** `runs.jsonl` line 30 (`2026-11-25T07:41:03Z`, `gemini-2.5-flash-preview-tts` 429 on Shot 11).
- **What broke:** A two-model chain still stalled when both models hit their rate/daily limits during iterative testing.
- **Resolution:** Following a colleague's recommendation, expanded `voice.models` to a 3-model Gemini chain (`gemini-3.8-flash-tts`, `gemini-3.8-flash-lite-tts`, `gemini-2.5-flash-preview-tts`, verified in `runs.jsonl` lines 71–83, `13:01:40Z`–`13:05:40Z`) plus `am-ET-MekdesNeural` (`edge-tts`).

### Entry 7: Partial Run Crash Left `duration_s` Unset in `storyboard.json`
- **What broke:** When an early run aborted on Shot 7 or Shot 11 due to HTTP 429, `storyboard.json` still had `duration_s: null` because `storyboard.json` is written after the loop completes.
- **Resolution:** Per-shot sidecar caching (`outputs/narration/shot_XX.json`) ensures any subsequent run immediately reuses all completed shots in milliseconds and finishes writing `duration_s` for all 12 shots once the final shot succeeds.

### Entry 8: English Style Instruction Prefix Caused Gemini TTS to Speak English Instead of Amharic
- **Evidence:** `runs.jsonl` lines 61–70 (`12:47:15Z`–`12:50:13Z`) vs. lines 71–83 (`13:01:40Z`–`13:05:40Z`).
- **What broke:** When I listened to the Abigiya clips generated in lines 61–70, the narrator spoke **English** even though `shot["narration"]` in `storyboard.json` was written in Amharic Ge'ez script. The root cause was line 67 of `pipeline/narration.py`, which sent `"Say in a calm, warm, a little brisker voice: <Amharic text>"`. Because Gemini 3.8 Flash TTS is a generative multimodal LLM rather than a phoneme-only TTS reader, starting the prompt in English steered the model into translating/speaking in English.
- **Resolution:** Removed the English prefix so `narration.py` sends only the raw Amharic `narration` string (`"prompt_mode": "raw_text"`), and documented in `schema/storyboard.schema.json` that `voice.style` is an editorial note only and is never prepended to non-English prompts.

### Entry 9: Gemini TTS Speaks Amharic with an American English Accent
- **Evidence:** `runs.jsonl` lines 71–83 (`13:01:40Z`–`13:05:40Z`, archived in `outputs/narration-gemini-archive/`) vs. lines 165–176 (`16:50:01Z`–`16:50:26Z`, `am-ET-MekdesNeural` in `outputs/narration/`).
- **What broke:** After stripping the English prefix, `gemini-3.8-flash-lite-tts` and `gemini-2.5-flash-preview-tts` read the Amharic words in Amharic, but with a heavy American English accent (English vowel coloration and flattened Amharic ejectives like `ጥ`, `ጭ`, `ቅ`).
- **Resolution:** Preserved the Gemini TTS Amharic clips in `outputs/narration-gemini-archive/` as benchmark evidence, integrated native Ethiopian Amharic neural TTS (`am-ET-MekdesNeural` via `edge-tts`) into `pipeline/narration.py` as the primary model in `storyboard.json`, and generated all 12 shots under `stage: "narration"` (`runs.jsonl` lines 165–176, `27.65s` total latency, `65.0s` final film runtime).

### Entry 10: Cloudflare Workers AI `@cf/black-forest-labs/flux-1-schnell` Rejected `/seed` with HTTP 400 and Timed Out on Long Reads
- **Evidence:** `runs.jsonl` lines 85–87 (`2026-11-25T13:50:03Z`–`13:50:13Z`).
- **What broke:** Sending `{"prompt": prompt, "steps": 4, "seed": seed}` returned `HTTP Error 400: Bad Request: AiError: Bad input: Error: Additional or unevaluated properties '/seed' at '/' not allowed (code: 5006)`. Later, during the v2 keyframe regeneration, a slow Cloudflare response raised Python 3.13's `TimeoutError` during `json.load(response)`.
- **Resolution:** Removed `seed` from the Cloudflare JSON body while keeping `seed` in the local SHA-256 `cache_key` (logged as `"seed_in_cache_key_only": seed`), and added `(TimeoutError, OSError)` to the retry exception tuple in `pipeline/keyframes.py`.

### Entry 11: Homebrew `ffmpeg 9.1` Excludes `drawtext` and `subtitles` (`libass`)
- **What broke:** Homebrew's standard `ffmpeg 9.1` bottle includes `zoompan`, `sidechaincompress`, and `loudnorm`, but excludes `drawtext` and `subtitles` (moved to `ffmpeg-full`). Using `drawtext` would break `make film` on a standard macOS Homebrew install.
- **Resolution:** Used `Pillow` in `pipeline/assemble.py` to render transparent PNG subtitle overlays (splitting long subtitles `>85` chars like Shot 8 into two timed cues so vertical subtitles never exceed 3 lines) and the AI end card, compositing them with FFmpeg's built-in `overlay=0:0:enable='between(t,t0,t1)'` filter. Added both macOS and Linux TrueType font paths (`Arial`, `Helvetica`, `DejaVuSans`, `LiberationSans`).

### Entry 12: Text-Only Reference Sheet Conditioning Drift, Character Over-Injection, and Hallucinated Text (`GOCOD 30129`)
- **Evidence:** `runs.jsonl` lines 88–100 (`13:51:22Z`–`13:52:06Z`, v1 keyframes archived in `outputs/keyframes-v1-archive/`) vs. lines 177–189 (`16:52:28Z`–`17:02:14Z`, v2 keyframes in `outputs/keyframes/`).
- **What broke:** In `keyframes-v1`, I prepended the full `character` string to all 12 shots and used a vague dress description (`"a simple colourful dress"`). Because Cloudflare `flux-1-schnell` is text-to-image only (it cannot take `reference_sheet.jpg` as an image conditioning input, and rejects `/seed`), four visual defects occurred in v1:
  1. **Characters injected into landscape/sky shots:** Shot 1 (village establishing shot) and Shot 3 (the bright star in the sky) both drew close-ups of Abigiya and her grandmother in the foreground because `character` was blindly glued onto every shot prompt.
  2. **Triple-elder prompt bug in Shot 8:** Shot 8's prompt asked for the grandmother speaking *plus* a child helping an elderly neighbour, while the global character block also injected the grandmother—resulting in three elderly women in one frame.
  3. **Hallucinated text on `reference_sheet.jpg`:** Despite `"no text, no watermark"`, the v1 reference sheet rendered garbled text (`GOCOD 30129`) and a corner signature—confirming Appendix B's warning about text inside generated images.
  4. **Dress color and braid drift:** Without image conditioning or a seed parameter, `"a simple colourful dress"` drifted across shots (green/blue, orange, yellow, red vest) and braids varied between one and two.
- **Resolution:** Added an explicit per-shot `characters` array (`[]`, `["abigiya"]`, or `["grandmother", "abigiya"]`) in `storyboard.json`, locked the clothing description to `"two neat braids wearing a warm yellow-and-teal dress"` and `"traditional white cotton netela shawl"`, simplified Shot 8 to one clear visual moment, and regenerated the keyframes (`runs.jsonl` lines 177–189). Shot 1 is now a true village establishing shot, Shot 3 is a pure night-sky star shot, `reference_sheet.jpg` has zero hallucinated text, and `reference_sheet.jpg` and `shot_08.jpg` share the exact yellow-and-teal dress and white netela shawl—though minor facial/proportion drift remains across independent text-to-image calls, which is documented as a negative result in `EXPERIMENTS.md` (Experiment 10).

### Entry 13: Zero Free GPU Session for Wan 2.2 Video and ACE-Step 1.5 Music Within the Sprint Window
- **What broke:** Running Wan 2.2 TI2V-5B (12 shots × 5–10 GPU minutes per clip on a T4) and ACE-Step 1.5 requires a phone-verified Kaggle GPU session or an available Colab T4 runtime. Neither was available without interruption during our 24-hour sprint window.
- **Resolution:** Used the brief's explicitly supported zero-GPU floor fallback (line 115: *"Nobody needs to end with nothing: if video generation fails you, animating your keyframes with a slow pan-and-zoom in FFmpeg works, and a narrated, scored, subtitled sequence of stills is still a film"*):
  - `pipeline/shots.py` animates the 12 FLUX.1-schnell keyframes at 24 fps in both `9:16` and `16:9` using FFmpeg's `zoompan` filter (`push-in`, `pull-out`, `pan-left`, `pan-right`, `none`) scaled by `motion.amount`.
  - `pipeline/music.py` synthesizes a deterministic 65.4-second Ethiopian Tizita major pentatonic krar-and-pad lullaby (`local-tizita-lullaby-synth-v1`).
  - Both scripts include drop-in file override support (`outputs/wan/shot_XX.mp4` with `tpad=stop_mode=clone` and `outputs/music/ace_step_chosen.wav` with full `runs.jsonl` logging) when GPU outputs are supplied.
