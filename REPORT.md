# Report — AI-Content Generation: *Abigiya and the Little Star* (`ኮኮቤ`)

**Repository:** `https://github.com/yordi68/ai-content-generation`  
**Author:** Yordanos Yirgu  
**Date:** 25 November 2026

---

## 1. What I Set Out to Make and for Whom

I built both a **65.0-second** short film—***Abigiya and the Little Star* (`ኮኮቤ`)** (`62.4s` across 12 shots + `2.6s` AI disclosure end card)—and a reproducible, contract-driven Python pipeline (`make film`) that turns `storyboard.json` into keyframes, moving shots, original music (`65.4s` score), Amharic narration, burned-in English subtitles, an AI disclosure end card, and finished vertical (`9:16`) and horizontal (`16:9`) MP4 exports.

The film is made for **Ethiopian families, children, and diaspora relatives** who watch short stories together at bedtime or on mobile feeds. It tells the story of **Abigiya**, an eight-year-old girl in an Ethiopian highland village who watches the night sky from her window and wishes she could shine like a bright little star. Her grandmother takes her hand and teaches her that she does not need to be a star in the sky to bring light to the world: every time she helps someone, shares kindness, or gives hope to someone who feels lonely, she shines just like that star. From that night on, Abigiya tries to bring a small light into everyone's life, and her grandmother names her **"Kokobe"** (`ኮኮቤ` — *"My Star"*).

My intent was for viewers to finish the film feeling warm and hopeful, understanding one simple truth: **even a small act of kindness makes a difference.**

---

## 2. What I Learned from My Audience and How It Visibly Changed `storyboard.json`

Testing prototypes with three target audience members (an older Ethiopian family member representing the parent/grandparent generation, a 10-year-old younger cousin representing the children's audience, and a bilingual young adult relative watching on mobile) changed both the story and the pipeline across verifiable git commits and `runs.jsonl` entries:

1. **Test 1 — From 12 Disconnected Statements to a Unified Ethiopian Bedtime Story (`commits 30fcc83` & `a215726` → `commit d32e9de`):**
   - **What the audience heard:** I first tested our initial 12-shot developer monologue (`commit 30fcc83` and `commit a215726`, *A New Life for a Software Engineer*, `runs.jsonl` lines 4–45) and its literal machine-translated Amharic version (`runs.jsonl` lines 47–58, `11:55:27Z`–`12:01:44Z`), followed by the first unedited reading of *Abigiya and the Little Star* (`runs.jsonl` lines 59–70, `12:44:02Z`–`12:50:13Z`).
   - **What they said:**
     - Our first 12 one-line statements sounded like disconnected bullet points rather than a story a family would watch twice (`FAILURES.md`, Entry 0), and literal Amharic technical terms (`ሰው ሰራሽ ብልህነት`, `ሞዴሎቹ`) sounded stiff and unnatural to native ears.
     - When listening to the first unedited Abigiya Amharic narration (`runs.jsonl` lines 59–70), they loved the grandmother-and-granddaughter story, but pointed out that Shots 1–10 alone ran `112.61s` (with Shot 8 taking `20.46s` at `runs.jsonl` **line 68**, `2026-11-25T12:49:36Z`), which dragged and exceeded the 90-second limit.
   - **How `storyboard.json` visibly changed (`git diff a215726..d32e9de storyboard.json`):**
     - Replaced the developer monologue in `storyboard.json` with the unified 12-shot Ethiopian bedtime story ***Abigiya and the Little Star* (`ኮኮቤ`)** set in an Ethiopian village (`በኢትዮጵያ ውብ መንደር`).
     - Tightened the Amharic sentences across Shots 1, 2, 5, 6, and 8 so Shot 8 dropped from `20.46s` (line 68) to `12.20s` on Gemini TTS (line 78) and `9.10s` on `am-ET-MekdesNeural` (line 172), bringing the complete 12-shot film runtime to **`65.0s`**.

2. **Test 2 — Near-Final Cut: Fixing American-Accented Amharic, Character Over-Injection in Landscape Shots, and 5-Line Vertical Subtitles (`runs.jsonl` lines 71–125 → lines 165–215):**
   - **What the audience saw and heard:** I showed the first assembled 12-shot Abigiya cut (`runs.jsonl` lines 71–125) to the same three audience reviewers.
   - **What they said:**
     - **American accent on Amharic Gemini TTS:** After I removed the English style prefix (`runs.jsonl` lines 71–83, `13:01:40Z`–`13:05:40Z`), Gemini TTS spoke Amharic, but the native speakers immediately said the voice sounded *"like someone from the USA trying to speak Amharic"* (`FAILURES.md`, Entry 9)—flattening Amharic ejectives (`ጥ`, `ጭ`, `ቅ`) and losing the grandmotherly warmth.
     - **Characters appearing in the village & star shots, three grandmothers in Shot 8, and dress color drift:** Our 10-year-old viewer pointed out that in Shot 1 (the village establishing shot) and Shot 3 (the single bright star in the sky), Abigiya and her grandmother were standing right in the frame; in Shot 8, three elderly women appeared in the same room; and Abigiya's dress changed colors from shot to shot (`FAILURES.md`, Entry 12).
     - **Shot 8 vertical subtitle overflow:** Our mobile viewer noted that Shot 8's 160-character English subtitle wrapped onto 5 lines on the `9:16` vertical cut.
   - **How `storyboard.json` and the pipeline visibly changed (`runs.jsonl` lines 165–215):**
     - Added an explicit per-shot `characters` array to `storyboard.json` (`"characters": []` on Shot 1 village and Shot 3 star; `"characters": ["abigiya"]` on solo shots; `"characters": ["grandmother", "abigiya"]` on duo shots), simplified Shot 8's `picture` prompt so it no longer asked for a second elder, locked Abigiya's outfit to `"two neat braids wearing a warm yellow-and-teal dress"` and the grandmother's to `"traditional white cotton netela shawl"`, and regenerated all keyframes (`runs.jsonl` **lines 177–189**, `16:52:28Z`–`17:02:14Z`).
     - Set `voice.models[0]` in `storyboard.json` to native Ethiopian Amharic (`am-ET-MekdesNeural` via `edge-tts`) and ran `pipeline/narration.py`, logging all 12 shots under `stage: "narration"` (`runs.jsonl` **lines 165–176**, `16:50:01Z`–`16:50:26Z`).
     - Added `split_subtitle_cues()` in `pipeline/assemble.py` to split subtitles longer than 85 characters (Shot 8) into two timed 2–3 line subtitle cards (`0.0s..3.55s` and `3.55s..9.60s`), and upgraded `loudnorm` to a true two-pass EBU R128 normalization (`runs.jsonl` **line 215**, `17:08:52Z`).

---

## 3. The Hardest Problem and How I Solved It

The hardest engineering problem was **free-tier quota exhaustion coupled with silent format and prompt-language incompatibilities across TTS models**.

When I first ran `pipeline/narration.py` against `gemini-3.8-flash-tts`, Shots 1–6 succeeded (`runs.jsonl` lines 4–9, `07:35:50Z`–`07:36:18Z`) and Shot 7 crashed with `HTTP Error 429: Too Many Requests` (`runs.jsonl` **line 10**, `2026-11-25T07:36:18Z`). Blind retries failed in `0.62s–1.25s` (lines 10–12). By logging the full HTTP 429 body (`runs.jsonl` **line 32**, `07:58:11Z`) and checking the Google AI Studio rate-limit dashboard, I uncovered three distinct problems:
1. **3 Requests Per Minute (RPM):** Sending 12 shots sequentially without pacing sent ~12 requests/minute, breaching the 3 RPM cap after 3–5 shots.
2. **10 Requests Per Day (RPD) per model:** A single Gemini TTS model allows only 10 requests per day on the Free Tier—meaning a 12-shot film **cannot** finish on one model in a single day, and failed 429 retries also incremented the dashboard counter (`13 / 10 RPD` observed).
3. **Headerless PCM on fallback:** When Shot 6 failed over to `gemini-2.5-flash-preview-tts` (`runs.jsonl` **line 20**, `07:40:38Z`), the endpoint returned raw 24 kHz 16-bit mono PCM bytes (`audio/L16;rate=24000`) without a RIFF WAV header, crashing Python's `wave.open()` with `wave.Error: file does not start with RIFF id` (`FAILURES.md`, Entry 3).

**How I solved it in code (`pipeline/narration.py` and `pipeline/runlog.py`):**
- **Rate-limit pacing (`pace()`):** Enforced a 20-second minimum gap between Gemini TTS calls so the 3 RPM limit is never breached.
- **Per-key, per-model daily budget tracking (`requests_today()`):** Tagged every `runs.jsonl` entry with an 8-character SHA-256 fingerprint of the active API key (`key_id`) and counted requests per model in the `America/Los_Angeles` quota timezone. Any model at 10/10 RPD (or returning a `"per day"` 429 error) is skipped immediately without wasting retries.
- **Ordered multi-model failover chain + RIFF WAV wrapper:** Chained `am-ET-MekdesNeural` (`edge-tts`) → `gemini-3.8-flash-tts` → `gemini-3.8-flash-lite-tts` → `gemini-2.5-flash-preview-tts` (verified in `runs.jsonl` lines 71–83 and 165–176), and added `to_wav()` to wrap raw `audio/L16` PCM bytes in a valid RIFF WAV header.

---

## 4. Suggested Practices Tested Honestly: One That Beat My Instinct, and One That Did Not

### Practice That Beat My Instinct: Timing the Narration First and Letting the Voice Track Drive Shot Durations (Plus Two-Pass `-14 LUFS` Ducking)

- **My initial instinct:** I initially planned to give all 12 shots a uniform `6.5s` duration (`78s` total) and generate the visual clips before finalizing the voice track.
- **What happened when I tested the suggested practice:**
  - Measuring actual TTS outputs in `pipeline/narration.py` and writing `shot["duration_s"]` into `storyboard.json` first (`runs.jsonl` lines 165–176) showed that natural shot lengths varied from `3.2s` (Shot 7: *"Her grandmother smiled and took her hand."*) to `9.6s` (Shot 8: the grandmother's central lesson).
  - Having `pipeline/shots.py` read each shot's voice-driven `duration_s` and having `pipeline/assemble.py` apply `sidechaincompress` (`threshold=0.02:ratio=6:attack=300:release=1500`) plus two-pass `loudnorm` (`input_i: "-28.54" LUFS` normalized to `-14.0 LUFS` at `runs.jsonl` line 215) made every cut land on the exact breathing pause of the storyteller.

### Practice That Did Not Work as Expected: Text-Only Reference Sheet Conditioning on Cloudflare FLUX.1-schnell (and Steering Amharic Gemini TTS with an English Style Instruction)

- **What the brief suggested:**
  1. Generate a character and style reference sheet first, then condition every keyframe on it with a fixed `seed` to keep the main character consistent across 12 shots (Phase 2 Step 1 & Appendix B line 694).
  2. Steer Gemini TTS with a plain-language style instruction like `"calm, warm, slow"` (Appendix A line 629 & Appendix B line 737).
- **What actually happened when I tested both honestly:**
  1. **Reference sheet + global character block on Cloudflare `flux-1-schnell` produced a negative result in Pass 1 (`EXPERIMENTS.md`, Experiment 10; `FAILURES.md`, Entry 12):**
     - Cloudflare's free `@cf/black-forest-labs/flux-1-schnell` endpoint is strictly text-to-image (it cannot accept `reference_sheet.jpg` as an image conditioning input) and rejected `/seed` in the JSON body with `HTTP Error 400: Bad Request: Additional or unevaluated properties '/seed' at '/' not allowed` (`runs.jsonl` **lines 85–87**, `13:50:03Z`–`13:50:13Z`).
     - In `keyframes-v1` (`runs.jsonl` **lines 88–100**, `13:51:22Z`–`13:52:06Z`), prepending the global `character` block to all 12 shots injected Abigiya and her grandmother into Shot 1 (village establishing shot) and Shot 3 (the bright star in the sky), created three grandmothers in Shot 8, rendered hallucinated text (`GOCOD 30129`) on `reference_sheet.jpg`, and allowed `"a simple colourful dress"` to drift across green/blue, orange, yellow, and red outfits.
     - In `keyframes-v2` (`runs.jsonl` **lines 177–189**, `16:52:28Z`–`17:02:14Z`), switching to selective per-shot character injection (`characters: []` on Shots 1 & 3) and locking the outfit string to `"warm yellow-and-teal dress"` and `"white cotton netela shawl"` fixed Shots 1, 3, and 8, removed the `GOCOD 30129` text artifact, and matched the yellow-and-teal dress between `reference_sheet.jpg` and `shot_08.jpg`—proving that selective prompt engineering locks *style and outfit palette*, even though true face-identity lock across shots requires an image-conditioned endpoint or LoRA.
  2. **English style instruction broke Amharic Gemini TTS (`EXPERIMENTS.md`, Experiment 5; `FAILURES.md`, Entry 8):**
     - While `"Say in a calm, warm, a little brisker voice:"` reduced English duration by `15.3%` (`runs.jsonl` lines 4–8 vs. lines 13–17), prepending that English instruction to Amharic text (`runs.jsonl` lines 61–70) caused Gemini TTS to **translate/speak in English instead of Amharic**. Stripping the English prefix and sending pure Amharic text (`runs.jsonl` lines 71–83) was required to make Gemini TTS speak Amharic.

---

## 5. Ceiling Work: Three-Way TTS Architecture & Amharic Phonology Benchmark

To go beyond the floor, I built and benchmarked **three distinct TTS architectures** across two git branches (`main` and `local-voice`) and logged the runs in `runs.jsonl`:

| Engine / Model | `runs.jsonl` / Git Evidence | 12-Shot Active Latency | Avg Latency / Shot | Raw Speech Duration | Quota / Rate Limit | Amharic Support & Phonology |
|---|---|---|---|---|---|---|
| **1. Gemini TTS 3-Model Failover Chain** (`3.8-flash-tts` → `3.8-flash-lite-tts` → `2.5-flash-preview-tts`) | `runs.jsonl` **lines 71–83** (`13:01:40Z`–`13:05:40Z`), archived in `outputs/narration-gemini-archive/` | `48.13s` (+ `220s` RPM wait) | `4.01s` | `66.20s` | 3 RPM / 10 RPD per model | Reads Amharic Ge'ez script (only after stripping English prefixes), but speaks with a heavy **American English accent**. |
| **2. Local CPU Open-Weight TTS** (`piper-tts` `en_US-lessac-medium.onnx`) | `local-voice` branch (`commit 522ad2a`) | **`2.85s`** (`length_scale=1.0`) | **`0.24s`** | `36.49s` (`1.0x`) to `70.81s` (`2.3x`) | **Unlimited** (100% offline CPU) | Zero quota limits and 15× faster than cloud APIs, but stretching `length_scale >= 1.7` sounds robotic and no open-weight Amharic ONNX checkpoint exists yet. |
| **3. Native Ethiopian Neural TTS** (`am-ET-MekdesNeural` via `edge-tts`) | `runs.jsonl` **lines 165–176** (`16:50:01Z`–`16:50:26Z`, `stage: "narration"`) | **`27.65s`** (zero RPM wait) | **`2.30s`** | `56.27s` (`62.4s` shots + `2.6s` card = **`65.0s` film**) | Free endpoint, no 10 RPD cap | **Authentic Ethiopian Amharic accent**, accurate ejectives, and natural bedtime-story cadence. |

**Key Insight from Ceiling Work:** Frontier multimodal TTS models like Gemini 3.8 Flash TTS list 130+ languages on paper, but for Ethiopian languages like Amharic they currently exhibit two failure modes that only native-speaker listening catches: (1) prompt-language bleed when given English style instructions, and (2) English-phoneme transfer (an American accent on Ge'ez script). Routing `pipeline/narration.py` through a native Ethiopian neural voice (`am-ET-MekdesNeural`) with automatic failover to the 3-model Gemini TTS chain delivered both cultural authenticity and pipeline resilience.

---

## 6. What I Would Build Next

1. **Automated Kaggle / Colab GPU Worker for Wan 2.2 TI2V-5B and ACE-Step 1.5:** Because we lacked an uninterrupted phone-verified Kaggle/Colab GPU session during the sprint (`FAILURES.md`, Entry 13), `pipeline/shots.py` and `pipeline/music.py` used the deterministic FFmpeg `zoompan` and local Tizita pentatonic synthesizer floor path. Both scripts already include tested override hooks (`outputs/wan/shot_XX.mp4` with `tpad=stop_mode=clone` and `outputs/music/ace_step_chosen.wav` with full `runs.jsonl` logging); next, I would automate pushing cached keyframes to a remote GPU worker to generate Wan 2.2 video clips and audition three ACE-Step 1.5 tracks.
2. **Image-Conditioned Character Consistency (FLUX.2-klein / IP-Adapter / LoRA):** To solve the residual text-only character drift documented in Experiment 10, I would connect `reference_sheet.jpg` to an image-conditioned endpoint (or train a lightweight LoRA on a 4-angle character sheet) so facial proportions and clothing stay locked across all 12 shots by construction.
3. **Open-Weight Local Amharic Piper TTS Checkpoint:** Training or distilling an Amharic voice checkpoint into ONNX for `piper-tts` (building on our `local-voice` branch) would give Ethiopian creators `2.85-second` offline synthesis with zero cloud quotas.
