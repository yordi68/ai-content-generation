So first when I was generating the script, while I was working with the tool I'm using, it generated like the assessment file said, "For us to use 8 to 12 shots, so I went with 12 to 12 shots, it generated 12 statements. So when you read or listen, when you read that 12 statements, it actually doesn't tell a story. So if the story is going to be bad, it's not going to be a good video. So for that, what I first did is I generated, I gave it some ideas and generated a whole paragraph and then I read that after I read that, then it's better to split it to 12 sections. So I think that's a better way to generate the narration.

## Narration stage: the story in plain language (25 Nov 2026)

I wanted the narrator to sound like one steady person from the first line to the last. The free Google voice I chose sounds good, but it has a limit on how much it can be used each day. I hit that limit part of the way through making the narration, and the work stopped.

What I did about it, in order:

- **Slowed the voice down to a faster pace.** The first version ran about 100 seconds, which is longer than the 90 seconds the brief allows. Speeding the voice up brought it to about 75 seconds.
- **Set up back-up voices.** When the first voice runs out, the work moves to a second Google voice, then a third. This kept the film moving, but the back-up voices sound a little faster and shorter, so the film now mixes voices.
- **Planned to replace the back-up voice later.** The main voice came back for one part of the film, so the other mixed parts can be remade with it once the limit fully resets. That's the plan for the next run.

The bigger idea I discussed is to make every part sound like the same person, even when different companies make the sound. This is called voice cloning: you record one sample of a voice, and another company copies it. The cost of that idea is:

- **Permission.** The copy needs a real person's voice. I would need their written consent, recorded in the ethics file, before using it. My narrator was meant to be invented, so this adds work.
- **Money.** The free voice services don't offer voice copying in the languages I need. I would need paid accounts with other companies.
- **Imperfect results.** A copy from one company won't match another company's voice exactly. I would still need to listen to both and decide whether the difference matters.
- **Time.** Testing, paying and recording would take days, not hours.

There's also a free option: a voice that runs on my own computer. It never runs out, but it sounds different from the Google voice, so the film would still have a third voice unless I remade everything with it.

What the choice comes down to:

1. **Keep the mix and accept two voices.** Free and fast, but the change is noticeable.
2. **Wait for the limit to reset, then remake the back-up parts with the main voice.** Free, and the voice stays the same, but it costs a day or so of waiting.
3. **Clone one voice with a paid service.** Costs money, needs written permission from the voice's owner, and takes several days to test.
4. **Switch everything to a free voice on my computer.** Free, never runs out, but it means remaking every part, and the voice won't match the Google one.

My recommendation is option 2, because it keeps one voice and costs nothing beyond waiting.

## Narration stage: problems and fixes, in detail (25 Nov 2026)

**1. Gemini 3.8 Flash text call took 2 min 17 s.**
Tried: one smoke test call, timed and logged in runs.jsonl.
Status: open. Not seen again yet. Watch latency in later runs.

**2. Gemini TTS returned HTTP 429 (Too Many Requests) on shot 7.**
After six clips, the main model rejected requests. Retries failed in about 1 second each, which points to a quota limit, not a slow server.
Tried: retry with a wait, then stop. The full error text was not logged at first.
Fixed: the script now logs Google's full error message, so I can tell a per-minute limit from a daily one.
Status: open. The quota limit is not yet explained.

**3. The backup model returned audio the WAV reader could not open.**
Gemini 2.5 Flash TTS returned raw audio without a WAV header. The script crashed when it tried to read the length.
Fixed: the script detects raw audio and wraps it in a WAV header, using the sample rate in the response.

**4. Fallback clips are a different voice and pace.**
Shots 6 to 10 and 12 came from the backup model. They run about 3 to 5 seconds, against 6 to 10 seconds for the main model on the same kind of line. The film's voice changes partway through.
Tried: a rule to regenerate fallback clips with the main model on each run.
Status: open until the main model's quota resets. Shots 6 to 10 and 12 still need the upgrade.

**5. The first full narration ran about 100 seconds.**
The approved voice style ("calm, warm, unhurried") made the film longer than the brief's 90-second limit.
Fixed: changed the style to "calm, warm, a little brisker". The total is now 74.6 seconds. This regenerated all clips, which used quota.

**6. Both models were out of quota for shots 11 and 12 (10 RPD per model).**
A single fallback could not finish the 12-shot film because each Gemini TTS model on the Free Tier has a 10 requests-per-day (RPD) limit and a 3 requests-per-minute (RPM) limit.
Fixed: following a colleague's recommendation on Slack, I configured an ordered fallback chain across three distinct Gemini TTS models (`gemini-3.8-flash-tts`, `gemini-3.8-flash-lite-tts`, and `gemini-2.5-flash-preview-tts`), because each model has its own independent per-minute and per-day request quota (30 RPD combined per project), and `gemini-3.8-flash-lite-tts` stays within the 3.8 family for Amharic support. I also added 20-second pacing between calls to stay under the 3 RPM limit.

**7. A crash halfway left the storyboard without durations.**
The script writes `duration_s` only at the end of a full run.
Fixed by design: each finished clip is cached, so a re-run skips finished shots, and the storyboard is written once all 12 are done.

**8. An English style prefix caused Gemini TTS to speak English instead of Amharic.**
When I listened to the generated Abigiya clips, the narrator spoke in English even though `shot["narration"]` in `storyboard.json` was written in Amharic.
Why it happened: the script sent `"Say in a calm, warm, a little brisker voice: <Amharic text>"`. Because Gemini 3.8 Flash TTS is a generative language-and-audio model rather than a rigid text reader, starting the prompt with an English instruction steered the model into speaking English (translating or responding to the prompt) instead of reading the Amharic text verbatim. In the earlier smoke test, sending pure Amharic text with no English prefix spoke Amharic properly.
Fixed: removed the English `"Say in a ... voice:"` prefix from `pipeline/narration.py` so the request sends only the raw Amharic `narration` string, and bumped the cache key so old English-contaminated clips are not reused.

**9. Gemini TTS speaks Amharic with an American English accent (prosody and phonology gap).**
After removing the English prefix, `gemini-3.8-flash-lite-tts` and `gemini-2.5-flash-preview-tts` both read the Amharic script in Amharic, but the pronunciation and prosody sound like an American English speaker phonetically reading transliterated Amharic rather than a native Ethiopian speaker (e.g., flattened ejectives and English vowel coloration).
Status: kept the generated clips in `outputs/narration/` as a working baseline for the pipeline and documented this model limitation for the report and multilingual evaluation. Exploring native-accented alternatives (such as `am-ET-MekdesNeural` / `am-ET-AmehaNeural` or MMS-TTS Amharic) as a ceiling comparison.

## Keyframes and Assembly stages: problems and fixes (25 Nov 2026)

**10. Cloudflare Workers AI `@cf/black-forest-labs/flux-1-schnell` rejected the `/seed` JSON property with HTTP 400.**
When `pipeline/keyframes.py` first called Cloudflare FLUX with `{"prompt": prompt, "steps": 4, "seed": seed}`, the endpoint returned `HTTP Error 400: Bad Request: AiError: Bad input: Error: Additional or unevaluated properties '/seed' at '/' not allowed`.
Fixed: kept `seed` in `storyboard.json` and inside the local SHA-256 cache key (so changing a shot's seed still invalidates the cache and triggers regeneration), and sent `{"prompt": prompt, "steps": 4}` in the Cloudflare request payload. All 12 keyframes plus the reference sheet then generated in ~46 seconds total.

**11. Homebrew's default `ffmpeg 9.1` bottle excludes `drawtext` and `subtitles` (`libass`).**
When inspecting available FFmpeg filters (`ffmpeg -filters`), `zoompan`, `sidechaincompress`, and `loudnorm` were present, but `drawtext` and `subtitles` were absent because Homebrew moved `libass` and `libfreetype` into the separate `ffmpeg-full` formula. Relying on `drawtext` would break `make film` on any machine with standard Homebrew `ffmpeg`.
Fixed: rendered transparent subtitle overlay PNGs (wrapped inside safe areas) and the AI disclosure end card in Python with `Pillow`, and composited them with FFmpeg's built-in `overlay` filter so the pipeline runs on standard `ffmpeg`.



