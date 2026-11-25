# Experiments

Every experiment below was run during the development of the pipeline and film, with exact line numbers and UTC timestamps verifiable in `runs.jsonl`.

---

## Experiment 1: Continuous Narrative Paragraph vs. 12 Isolated Shot Statements

- **Hypothesis:** Drafting the script as 12 separate one-line shot statements will feel disconnected when spoken back-to-back, whereas writing a single continuous story paragraph first and splitting it across 12 shots will create natural narrative bridges between shots.
- **Change:** Replaced the initial 12 isolated statements with a unified prose narrative first, then mapped one sentence per shot across the 12 shots in `storyboard.json` (`commit 522ad2a` on `local-voice`, `commit d32e9de` on `main`, and `FAILURES.md` Entry 0).
- **Result:** Confirmed. The spoken flow improved immediately: transitions between setup, dialogue, and resolution read as a single story rather than a bulleted list.

---

## Experiment 2: Gemini TTS Style Instruction Pacing (`unhurried` vs. `a little brisker` on English Text)

- **Hypothesis:** Changing `voice.style` in `storyboard.json` from `"calm, warm, unhurried"` to `"calm, warm, a little brisker"` on `gemini-3.8-flash-tts` (voice `Kore`) will reduce per-shot English narration duration by ~15–20% and bring total runtime closer to the 60–90 second target.
- **Change:** Updated `voice.style` in `storyboard.json` and regenerated Shots 1–5 on `gemini-3.8-flash-tts`:
  - Baseline (`"calm, warm, unhurried"`): `runs.jsonl` **lines 4–8** (`2026-11-25T07:35:50Z`–`07:36:12Z`).
  - Brisker (`"calm, warm, a little brisker"`): `runs.jsonl` **lines 13–17** (`2026-11-25T07:39:54Z`–`07:40:14Z`).
- **Result:** Confirmed on English text. Shot 1 dropped from `8.08s` (line 4) to `6.36s` (line 13, `-21.3%`), Shot 2 dropped from `9.84s` (line 5) to `8.08s` (line 14, `-17.9%`), Shot 4 dropped from `9.56s` (line 7) to `7.64s` (line 16, `-20.1%`), and Shot 5 dropped from `10.88s` (line 8) to `9.64s` (line 17, `-11.4%`). Across Shots 1–5, speech duration dropped from `45.08s` to `38.20s` (`-15.3%`).

---

## Experiment 3: Storyteller Style Instruction (`gentle, warm storyteller, unhurried`) on Amharic TTS

- **Hypothesis:** Using `"gentle, warm storyteller, unhurried"` for the children's story will sound warmer without exceeding the 90-second runtime ceiling.
- **Change:** Set `voice.style` to `"gentle, warm storyteller, unhurried"` and generated Shot 1 on `gemini-3.8-flash-tts` (`runs.jsonl` **line 59**, `2026-11-25T12:44:02Z`), compared against `"calm, warm, a little brisker"` (`runs.jsonl` **line 47**, `2026-11-25T11:55:27Z`, `7.61s`, and **line 61**, `2026-11-25T12:47:15Z`, `12.52s`).
- **Result:** Refuted for runtime budget. Shot 1 stretched to `14.13s` (`runs.jsonl` line 59), and in the subsequent full run (`runs.jsonl` **lines 61–70**, `12:47:15Z`–`12:50:13Z`), Shots 1–10 alone totaled `112.61s` (with Shot 8 taking `20.46s` at **line 68**, `12:49:36Z`), exceeding the 90-second ceiling before Shots 11–12 even ran.

---

## Experiment 4: Post-Synthesis FFmpeg `atempo=1.08` vs. Full Re-Synthesis for Fine Duration Tuning

- **Hypothesis:** Applying a `1.08x` tempo adjustment (`atempo=1.08`) in `pipeline/assemble.py` will trim ~7.4% off a 90.8s voice track without perceptible pitch distortion or spending an extra 12 API calls of daily quota.
- **Change:** Added `"tempo": 1.08` to `voice` in `storyboard.json` (`commit a215726`) and `atempo` filtering in `pipeline/assemble.py`.
- **Result:** Confirmed. The `90.8s` raw speech track (`runs.jsonl` lines 13–17 and 35–45) compressed to `84.1s` of speech (`90.2s` with `0.5s` pauses) with zero additional Gemini TTS quota consumed. Once we switched to the more concise Abigiya Amharic script and `am-ET-MekdesNeural` (`56.27s` raw speech), we were able to set `"tempo": 1.0` (natural 1.0x speed, `62.4s` with pauses + `2.6s` end card = `65.0s` total film runtime).

---

## Experiment 5: English Style Prefix Contamination on Non-English Gemini TTS Prompts

- **Hypothesis:** Prefixing an Amharic narration line with an English style instruction (`"Say in a calm, warm, a little brisker voice: <Amharic text>"`) causes `gemini-3.8-flash-tts` to switch into English generation instead of speaking Amharic, whereas sending raw Amharic text alone forces Amharic speech output.
- **Change:** Removed the English prefix `"Say in a {voice['style']} voice: "` from `synthesize_gemini()` in `pipeline/narration.py` so `contents[0].parts[0].text` contains only `shot["narration"]` in Amharic (`"prompt_mode": "raw_text"`), and regenerated all 12 shots:
  - With English style prefix: `runs.jsonl` **lines 61–70** (`2026-11-25T12:47:15Z`–`12:50:13Z`).
  - Without English prefix (raw Amharic text only): `runs.jsonl` **lines 71–83** (`2026-11-25T13:01:40Z`–`13:05:40Z`).
- **Result:** Confirmed. With the English prefix present (lines 61–70), the model spoke English in the Abigiya draft clips (`112.61s` across 10 shots). With pure Amharic text only (lines 71–83), both `gemini-3.8-flash-lite-tts` (Shots 1–9, lines 71–79) and `gemini-2.5-flash-preview-tts` (Shots 10–12, lines 81–83) spoke Amharic (`66.20s` raw speech across all 12 shots).

---

## Experiment 6: Request Pacing (20s Gap) + Per-Model Daily Budget vs. Blind Retries on HTTP 429

- **Hypothesis:** Blindly retrying HTTP 429 errors burns through the 10 requests-per-day (RPD) free-tier quota and triggers the 3 requests-per-minute (RPM) limit; enforcing a 20-second minimum gap between calls and skipping models that return `"per day"` quota errors will eliminate failed retry waste.
- **Change:** Added `pace()` (`MIN_GAP_S = 20`) and `requests_today(model, key_id)` in `pipeline/narration.py` and `pipeline/runlog.py`, and stopped retrying when the 429 response body contains `"per day"`.
- **Result:** Confirmed. Before pacing, rapid calls triggered 3 consecutive 429 retries on Shot 7 within 18 seconds (`runs.jsonl` **lines 10–12**, `2026-11-25T07:36:18Z`–`07:36:36Z`), pushing peak usage to `5 / 3 RPM` and `13 / 10 RPD` on the AI Studio dashboard. After adding 20s pacing and daily budget checks, zero RPM 429 errors occurred across all subsequent runs (`runs.jsonl` lines 35–83).

---

## Experiment 7: Three-Model Gemini TTS Failover Chain (`3.8-flash-tts` → `3.8-flash-lite-tts` → `2.5-flash-preview-tts`)

- **Hypothesis:** Because each Gemini TTS model has its own independent 10 RPD free-tier quota, chaining `gemini-3.8-flash-tts`, `gemini-3.8-flash-lite-tts`, and `gemini-2.5-flash-preview-tts` in `voice.models` will allow a 12-shot film to complete in a single session even when the primary model is at 10/10 RPD.
- **Change:** Updated `voice.models` in `storyboard.json` to include all three models and ran `pipeline/narration.py` (`runs.jsonl` **lines 71–83**, `2026-11-25T13:01:40Z`–`13:05:40Z`).
- **Result:** Confirmed. The script saw `gemini-3.8-flash-tts` at 10/10 RPD (from lines 61–70) and skipped it with zero wasted calls, generated Shots 1–9 on `gemini-3.8-flash-lite-tts` (lines 71–79, avg latency `3.80s`/shot), hit the 10 RPD limit on Shot 10 (line 80, `13:04:37Z`), and immediately failed over to `gemini-2.5-flash-preview-tts` for Shots 10–12 (lines 81–83, avg latency `4.47s`/shot). All 12 shots completed in one run.

---

## Experiment 8: Local Open-Source CPU TTS (`piper-tts` `en_US-lessac-medium`) Length Scale Sweep

- **Hypothesis:** Running `piper-tts` locally on CPU eliminates external API quotas, and sweeping `length_scale` from `1.0` to `2.3` will match the 60–90 second film runtime while staying natural.
- **Change:** Tested `en_US-lessac-medium.onnx` across `length_scale` values `1.0`, `1.3`, `1.4`, `1.5`, `1.7`, `1.9`, and `2.3` on the 12-shot storyboard on the `local-voice` git branch (`commit 522ad2a`).
- **Result:** Negative for natural pacing and Amharic support. At default `length_scale=1.0`, all 12 shots synthesized in `2.85s` wall-clock time on CPU, but total speech was only `36.49s` (too short for a 60–90s film). Slowing to `length_scale=2.3` reached `70.81s` of speech (`76.8s` with pauses) and `length_scale=1.7` reached `65.4s` of speech (`83.4s` with 1.5s pauses), but stretched vowels sounded robotic, and `piper-tts` lacks an open-weight Amharic voice model. Kept Piper on the `local-voice` branch and returned to Amharic neural TTS on `main`.

---

## Experiment 9: Amharic Accent & Prosody Benchmark — Gemini TTS vs. Native Ethiopian Neural TTS (`am-ET-MekdesNeural`)

- **Hypothesis:** While Gemini 3.8 Flash-Lite TTS and 2.5 Flash TTS can read Amharic Ge'ez script, their phonology sounds American-accented; a dedicated Ethiopian Amharic neural voice (`am-ET-MekdesNeural` via `edge-tts`) will deliver authentic Ethiopian pronunciation and prosody with lower latency and no 10 RPD cap.
- **Change:** Generated all 12 Abigiya Amharic shots with `am-ET-MekdesNeural` (first benchmarked in `runs.jsonl` **lines 127–138**, `2026-11-25T14:07:35Z`–`14:08:14Z`, and then run through `pipeline/narration.py` under `stage: "narration"` in `runs.jsonl` **lines 165–176**, `2026-11-25T16:50:01Z`–`16:50:26Z`), comparing side-by-side against the Gemini TTS Amharic run (`runs.jsonl` **lines 71–83**, `13:01:40Z`–`13:05:40Z`, archived in `outputs/narration-gemini-archive/`).
- **Result:** Confirmed:
  - **Gemini TTS (`3.8-flash-lite-tts` + `2.5-flash-preview-tts`, lines 71–83):** `66.20s` raw speech, `48.13s` active model latency (`4.01s`/shot) plus `220s` RPM pacing wait, capped at 10 RPD per model, audible American English accent on Amharic ejectives and vowels.
  - **`am-ET-MekdesNeural` (`edge-tts`, lines 165–176):** `56.27s` raw speech (`62.4s` across 12 shots with `0.5s` pauses + `2.6s` end card = **`65.0s` final film**), `27.65s` total generation latency (`2.30s`/shot) with zero RPM pacing wait, native Ethiopian Amharic pronunciation and natural storytelling cadence.

---

## Experiment 10: Text-Only Reference Sheet Conditioning on Cloudflare FLUX.1-schnell (Negative Result & Selective-Character Fix)

- **Hypothesis:** Generating a character reference sheet (`reference_sheet.jpg`) first and prepending the film-level `style_block` and `character` string to all 12 shot prompts on Cloudflare `@cf/black-forest-labs/flux-1-schnell` will keep character identity and scene composition consistent across all 12 shots.
- **Change & Two-Pass Comparison:**
  - **Pass 1 (`keyframes-v1`, `runs.jsonl` lines 88–100, `2026-11-25T13:51:22Z`–`13:52:06Z`, archived in `outputs/keyframes-v1-archive/`):** Prepended the full `character` string (`"a young Ethiopian girl about 8 years old, dark hair in braids, a simple colourful dress; an older Ethiopian grandmother with grey hair and a white shawl"`) to all 12 shots.
  - **Pass 2 (`keyframes-v2`, `runs.jsonl` lines 177–189, `2026-11-25T16:52:28Z`–`17:02:14Z`, active in `outputs/keyframes/`):** Added an explicit per-shot `characters` list (`[]`, `["abigiya"]`, or `["grandmother", "abigiya"]`) in `storyboard.json` so `pipeline/keyframes.py` only injects characters actually present in that shot, locked the dress color to `"two neat braids wearing a warm yellow-and-teal dress"` and `"traditional white cotton netela shawl"`, simplified Shot 8's prompt, and replaced `"no text, no watermark"` with `"pure illustration without any text, letters, numbers, or signatures"`.
- **Result:** **Negative result for strict identity lock in Pass 1; substantially improved scene composition and outfit palette in Pass 2.**
  1. **Why text-only reference sheets do not lock identity:** Cloudflare's `@cf/black-forest-labs/flux-1-schnell` endpoint is purely text-to-image (it does not accept `reference_sheet.jpg` as an image conditioning input) and rejects `/seed` in the JSON payload (`runs.jsonl` lines 85–87, `13:50:03Z`–`13:50:13Z`, HTTP 400 `code: 5006`).
  2. **Defects found in Pass 1 (`keyframes-v1`):**
     - *Over-injection:* Because `character` was glued onto every shot, Shot 1 (village establishing shot) and Shot 3 (the bright star in the sky) both drew Abigiya and her grandmother in the frame.
     - *Prompt collision:* Shot 8 asked for the grandmother speaking *plus* a child helping an elderly neighbour while also prepending the grandmother from `character`, producing three elderly women in one frame.
     - *Hallucinated text:* The v1 `reference_sheet.jpg` rendered garbled text (`GOCOD 30129`) and a corner signature despite `"no text, no watermark"`.
     - *Outfit drift:* `"a simple colourful dress"` drifted across green/blue, orange, yellow, and red vest variations across shots.
  3. **What Pass 2 (`keyframes-v2`) fixed and what still drifts:**
     - Selective character injection (`characters: []` on Shots 1 and 3) made `shot_01.jpg` a true wide Ethiopian highland village at dusk and `shot_03.jpg` a pure night-sky star over hills.
     - Locking the outfit to `"warm yellow-and-teal dress"` and `"white cotton netela shawl"` made `reference_sheet.jpg` and `shot_08.jpg` share the exact same yellow dress with teal trim, two braids, and white netela shawl, and eliminated the third elder in Shot 8 and the `GOCOD 30129` text artifact on `reference_sheet.jpg`.
     - However, without image-to-image conditioning or a LoRA, minor facial proportions and secondary dress details still vary across independent diffusion calls. Visual *style* is locked by a text `style_block`; exact *character identity* requires image-reference conditioning.

---

## Experiment 11: Sidechain Ducking + Two-Pass EBU R128 Loudness Normalization (`-14.0 LUFS`)

- **Hypothesis:** Mixing the Tizita lullaby score at constant volume under the narration competes with the voice, whereas ducking the score via `sidechaincompress` (`threshold=0.02:ratio=6:attack=300:release=1500`) and running two-pass EBU R128 loudness normalization (`loudnorm=I=-14:TP=-1.0:LRA=11`) keeps the narration intelligible while hitting the exact `-14.0 LUFS` platform target.
- **Change:** Implemented sidechain compression followed by two-pass `loudnorm` (Pass 1 measures `input_i`, `input_tp`, `input_lra`, `input_thresh`, and `target_offset` in JSON mode; Pass 2 applies `linear=true` normalization with the measured values) in `build_master_audio()` inside `pipeline/assemble.py` (`runs.jsonl` **line 215**, `2026-11-25T17:08:52Z`).
- **Result:** Confirmed. Pass 1 measured the pre-normalized mix at `input_i: "-28.54" LUFS`, `input_tp: "-13.10" dBTP`, and `input_lra: "7.20" LU` (`runs.jsonl` line 215), and Pass 2 normalized the final master track cleanly to `-14.0 LUFS` / `-1.0 dBTP` across `outputs/radio_cut.mp4`, `outputs/film_9x16.mp4`, and `outputs/film_16x9.mp4` (`65.0s`).
