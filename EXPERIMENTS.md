# Experiments

Every experiment below was run during the development of the pipeline and film, with model calls and latencies recorded in `runs.jsonl`.

---

## Experiment 1: Continuous Narrative vs. 12 Isolated Shot Statements

- **Hypothesis:** Drafting the script as 12 separate one-line shot statements will feel disconnected when spoken back-to-back, whereas writing a single continuous story paragraph first and splitting it across 12 shots will create natural narrative bridges between shots.
- **Change:** Replaced the initial 12 isolated statements with a unified prose narrative first, then mapped one sentence per shot across the 12 shots in `storyboard.json`.
- **Result:** The spoken flow improved immediately: transitions between setup, conflict, and resolution read as a single story rather than a bulleted list. Kept the paragraph-first method for both the developer draft and the final *Abigiya and the Little Star* script.

---

## Experiment 2: Gemini TTS Style Instruction Pacing (`unhurried` vs. `a little brisker`)

- **Hypothesis:** Changing `voice.style` in `storyboard.json` from `"calm, warm, unhurried"` to `"calm, warm, a little brisker"` on `gemini-3.8-flash-tts` (voice `Kore`) will reduce per-shot narration duration by ~15–20% and bring total runtime closer to the 60–90 second target.
- **Change:** Updated `voice.style` in `storyboard.json` and regenerated Shots 1–5 on `gemini-3.8-flash-tts` (`runs.jsonl` timestamps `07:35:36Z` vs. `07:40:10Z`).
- **Result:** Confirmed. Shot 1 dropped from `8.08s` to `6.36s` (-21%), Shot 2 dropped from `9.84s` to `8.08s` (-18%), Shot 4 dropped from `9.56s` to `7.64s` (-20%), and Shot 5 dropped from `10.88s` to `9.64s` (-11%). Across Shots 1–5, speech duration dropped from `45.08s` to `38.20s` (-15.3%).

---

## Experiment 3: Storyteller Style Instruction (`gentle, warm storyteller, unhurried`) on Amharic TTS

- **Hypothesis:** Using `"gentle, warm storyteller, unhurried"` for the children's story will sound warmer without exceeding the 90-second runtime ceiling.
- **Change:** Set `voice.style` to `"gentle, warm storyteller, unhurried"` and generated Shot 1 on `gemini-3.8-flash-tts` (`runs.jsonl` timestamp `13:26:12Z`).
- **Result:** Refuted for runtime budget. Shot 1 alone stretched to `14.13s` (nearly double the `7.61s` baseline), which projected to ~140+ seconds across 12 shots. Reverted `voice.style` and tightened the Amharic sentences.

---

## Experiment 4: Post-Synthesis FFmpeg `atempo=1.08` vs. Full Re-Synthesis for Fine Duration Tuning

- **Hypothesis:** Applying a 1.08x tempo adjustment (`atempo=1.08`) in `pipeline/assemble.py` will trim ~7.4% off the spoken narration duration without perceptible pitch distortion or spending an extra 12 API calls of daily quota.
- **Change:** Added `"tempo": 1.08` to `voice` in `storyboard.json` and `atempo=1.08` in `pipeline/assemble.py`.
- **Result:** Confirmed. The 90.8s raw speech total compressed to 84.1s of speech without consuming any additional Gemini TTS daily quota, and the voice timbre remained natural.

---

## Experiment 5: English Style Prefix Contamination on Non-English Gemini TTS Prompts

- **Hypothesis:** Prefixing an Amharic narration line with an English style instruction (`"Say in a calm, warm, a little brisker voice: <Amharic text>"`) causes `gemini-3.8-flash-tts` to switch into English generation instead of speaking Amharic, whereas sending raw Amharic text alone forces Amharic speech output.
- **Change:** Removed the English prefix `"Say in a {voice['style']} voice: "` from `synthesize()` in `pipeline/narration.py` so `contents[0].parts[0].text` contains only `shot["narration"]` in Amharic, and bumped `cache_key` with `"prompt_mode": "raw_text"`.
- **Result:** Confirmed. With the English prefix present, the model spoke English in the Abigiya draft clips. With pure Amharic text only, both `gemini-3.8-flash-lite-tts` (Shots 1–9) and `gemini-2.5-flash-preview-tts` (Shots 10–12) spoke Amharic (`runs.jsonl` timestamps `13:42:02Z`–`13:45:43Z`), producing a 67.4s storyboard total (70.0s assembled with end card).

---

## Experiment 6: Request Pacing (20s Gap) + Per-Model Daily Budget vs. Blind Retries on HTTP 429

- **Hypothesis:** Blindly retrying HTTP 429 errors burns through the 10 requests-per-day (RPD) free-tier quota and triggers the 3 requests-per-minute (RPM) limit; enforcing a 20-second minimum gap between calls and skipping models that return `"per day"` quota errors will eliminate failed retry waste.
- **Change:** Added `pace()` (`MIN_GAP_S = 20`) and `requests_today(model, key_id)` in `pipeline/narration.py` and `pipeline/runlog.py`, and stopped retrying when the 429 body contains `"per day"`.
- **Result:** Confirmed. Before pacing, rapid calls triggered 3 consecutive 429 retries on Shot 7 within 18 seconds (`runs.jsonl` `07:36:18Z`–`07:36:36Z`), pushing peak usage to 5/3 RPM and 13/10 RPD on the AI Studio dashboard. After adding 20s pacing and daily budget checks, zero RPM 429 errors occurred across the full 12-shot generation run.

---

## Experiment 7: Three-Model Gemini TTS Failover Chain (`3.8-flash-tts` → `3.8-flash-lite-tts` → `2.5-flash-preview-tts`)

- **Hypothesis:** Because each Gemini TTS model has its own independent 10 RPD free-tier quota, chaining `gemini-3.8-flash-tts`, `gemini-3.8-flash-lite-tts`, and `gemini-2.5-flash-preview-tts` in `voice.models` will allow a 12-shot film to complete in a single session even when the primary model is at 10/10 RPD.
- **Change:** Updated `voice.models` in `storyboard.json` to `["gemini-3.8-flash-tts", "gemini-3.8-flash-lite-tts", "gemini-2.5-flash-preview-tts"]` and ran `pipeline/narration.py`.
- **Result:** Confirmed. The script detected `gemini-3.8-flash-tts` at 10/10 RPD, generated Shots 1–9 on `gemini-3.8-flash-lite-tts` (avg latency `3.8s`/shot), hit the daily limit on Shot 10, and seamlessly failed over to `gemini-2.5-flash-preview-tts` for Shots 10–12 (avg latency `4.6s`/shot). All 12 shots completed in one run.

---

## Experiment 8: Local Open-Source CPU TTS (`piper-tts` `en_US-lessac-medium`) Length Scale Sweep

- **Hypothesis:** Running `piper-tts` locally on CPU eliminates external API quotas, and sweeping `length_scale` from `1.0` to `2.3` will match the 60–90 second film runtime while staying natural.
- **Change:** Tested `en_US-lessac-medium.onnx` across `length_scale` values `1.0`, `1.3`, `1.4`, `1.5`, `1.7`, `1.9`, and `2.3` on the 12-shot storyboard on the `local-voice` branch.
- **Result:** At default `length_scale=1.0`, all 12 shots synthesized in `2.85s` wall-clock time on CPU, but total speech was only `36.49s` (too fast for a 60–90s film). Slowing to `length_scale=2.3` reached `70.81s` of speech (`76.8s` with pauses) and `length_scale=1.7` reached `65.4s` of speech (`83.4s` with 1.5s pauses), but stretched vowels sounded noticeably unnatural, and `piper-tts` lacks an Amharic voice model. Kept Piper on the `local-voice` branch and returned to native/multilingual neural TTS on `main`.

---

## Experiment 9: Amharic Accent & Prosody Benchmark — Gemini TTS vs. Native Ethiopian Neural TTS (`am-ET-MekdesNeural`)

- **Hypothesis:** While Gemini 3.8 Flash-Lite TTS and 2.5 Flash TTS can read Amharic Ge'ez script, their phonology sounds American-accented; a dedicated Ethiopian Amharic neural voice (`am-ET-MekdesNeural` via `edge-tts`) will deliver authentic Ethiopian pronunciation and prosody with lower latency and no 10 RPD cap.
- **Change:** Generated all 12 Abigiya Amharic shots with `am-ET-MekdesNeural` into `outputs/narration-ethiopian/` and logged every call under `stage: "narration_benchmark"` in `runs.jsonl` (`13:55:40Z`–`13:56:21Z`), comparing side-by-side against `outputs/narration/` (Gemini TTS).
- **Result:** Confirmed:
  - **Gemini TTS (`3.8-flash-lite-tts` + `2.5-flash-preview-tts`):** 66.2s raw speech, avg latency `4.0s`/shot plus `20s` RPM pacing wait (~4.5 minutes wall time), capped at 10 RPD per model, audible American English accent on Amharic ejectives and vowels.
  - **`am-ET-MekdesNeural` (`edge-tts`):** 56.3s raw speech, avg latency `3.40s`/shot with no 20s pacing delay (`41.8s` total wall time for all 12 shots), native Ethiopian Amharic pronunciation and natural storytelling cadence.

---

## Experiment 10: Reference Sheet + Locked Character/Style Block for 12-Shot Keyframe Consistency

- **Hypothesis:** Prepending a fixed `style_block` (`"soft hand-painted storybook illustration, warm gentle light, pastel colours, painterly texture"`) and a locked `character` description (`"a young Ethiopian girl about 8 years old, dark hair in braids, a simple colourful dress; an older Ethiopian grandmother with grey hair and a white shawl"`) to every shot prompt on `@cf/black-forest-labs/flux-1-schnell` will keep character appearance and visual palette consistent across 12 independent diffusion calls without LoRA training.
- **Change:** Built `compose_reference_prompt()` and `compose_shot_prompt()` in `pipeline/keyframes.py` so every call to Cloudflare FLUX includes the exact film-level `style_block`, `character`, and centered-framing instructions.
- **Result:** Confirmed. All 13 images (`reference_sheet.jpg` + `shot_01.jpg`–`shot_12.jpg`) generated in `46.8s` total (`3.60s` average latency per image, `runs.jsonl` `13:51:15Z`–`13:52:01Z`) with a cohesive warm storybook palette, braided hair, colourful dress, and white-shawled grandmother across scenes.

---

## Experiment 11: Sidechain Ducking + EBU R128 Loudness Normalization (`-14 LUFS`)

- **Hypothesis:** Mixing the Tizita lullaby score at constant volume under the narration competes with the voice, whereas ducking the score via `sidechaincompress` (`threshold=0.02:ratio=6:attack=300:release=1500`) and normalizing the master mix with `loudnorm=I=-14:TP=-1.0:LRA=11` keeps the narration intelligible while letting the music swell in pauses and over the end card.
- **Change:** Implemented the dual-split sidechain compression and EBU R128 loudness normalization filter graph in `build_master_audio()` inside `pipeline/assemble.py`.
- **Result:** Confirmed. The music gently drops whenever the narrator speaks, rises smoothly over the 0.5s inter-shot pauses and the 2.6s AI end card, and hits the `-14 LUFS` platform target for YouTube and mobile playback.
