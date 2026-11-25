# Ethics, Consent, Licences, and AI Labelling

## 1. Consent Record (Likeness and Voice Gate)

- **Characters:** Both characters depicted in *Abigiya and the Little Star*—**Abigiya** (an 8-year-old girl in an Ethiopian village) and her **grandmother**—are fictional storybook characters illustrated from text descriptions (`"soft hand-painted storybook illustration"`).
- **Faces and Likenesses:** No real person's photograph, face, or physical likeness was used as an input, reference image, or prompt target at any stage of the pipeline.
- **Voice and Narration:** The narration uses prebuilt synthetic text-to-speech voices (`Kore` on Google Gemini TTS and `am-ET-MekdesNeural` in the Amharic benchmark). No voice cloning or voice replication of any real person was performed. During development, I explicitly evaluated and rejected cross-provider voice cloning (documented in `FAILURES.md`) in part because cloning requires recording and storing a real person's voice along with formal written consent.
- **Gate Compliance:** Because no real person is shown or voiced, no individual likeness/voice release is required, and zero unconsented biometric data exists in the repository or outputs.

---

## 2. Model, Tool, and Output Licences

Every model, library, and tool used in the pipeline has been checked for licence terms and output usage rights:

| Component | Model / Package | Licence | Output & Commercial Usage Terms |
|---|---|---|---|
| **Repository Code** | `ai-content-generation` | **MIT Licence** (`LICENSE`) | Open-source; anyone may clone, modify, and run the pipeline. |
| **Keyframes** | Black Forest Labs `FLUX.1-schnell` (via Cloudflare Workers AI `@cf/black-forest-labs/flux-1-schnell`) | **Apache-2.0** | Permissive open-weight licence; generated images may be used and distributed freely under Apache-2.0 and Cloudflare Workers AI terms. |
| **Narration (Primary & Failover)** | Google `gemini-3.8-flash-tts`, `gemini-3.8-flash-lite-tts`, `gemini-2.5-flash-preview-tts` | **Google Gemini API Terms of Service** | Generated audio outputs belong to the user/developer subject to Google's Generative AI Prohibited Use Policy. Free-tier prompts may be reviewed by Google for service improvement. |
| **Narration (Local CPU Branch)** | `piper-tts` (`en_US-lessac-medium.onnx`) | **MIT Licence** (code) / **CC-BY-4.0** (Lessac voice dataset) | Permissive open-source synthesis; attribution to Ryan Lessac / Piper voice contributors. |
| **Narration (Amharic Benchmark)** | Microsoft `am-ET-MekdesNeural` (via `edge-tts` LGPL-3.0 wrapper) | **LGPL-3.0** (client library) / Microsoft Edge Read-Aloud service terms | Used strictly for non-commercial educational benchmarking of native Ethiopian Amharic phonology vs. Gemini TTS. |
| **Score (Local & Optional GPU)** | Local Tizita Pentatonic Synthesizer (`pipeline/music.py`) / `ACE-Step 1.5` | **MIT Licence** | Deterministic Python synthesis is MIT-licensed in this repo; ACE-Step 1.5 weights and outputs are MIT-licensed with commercial use permitted. |
| **Moving Shots & Assembly** | `FFmpeg 9.1` (`zoompan`, `sidechaincompress`, `loudnorm`, `overlay`) | **LGPL v2.1+ / GPL v2+** | Invoked as an external CLI process; output MP4 files are unrestricted user media. |
| **Schema & Overlay Rendering** | `jsonschema 4.26.0`, `Pillow 13.0.0` | **MIT Licence** / **MIT-CMU (HPND)** | Permissive open-source Python packages. |

---

## 3. Artistic Style Ethics

- To avoid appropriating the identity or livelihood of any living illustrator, `style_block` in `storyboard.json` describes only medium, lighting, palette, and texture qualities:
  > `"soft hand-painted storybook illustration, warm gentle light, pastel colours, painterly texture"`
- No living artist's name is used in any prompt.

---

## 4. Private Data and Free-Tier Privacy Hygiene

- Free-tier hosted APIs (such as the Google AI Studio Gemini API Free Tier) state in their data terms that submitted prompts and outputs may be used to train or improve models.
- Therefore, no private family names, personal addresses, photographs, voice recordings, or sensitive personal data were placed in `storyboard.json` or sent to any API endpoint.
- API keys (`GEMINI_API_KEY`, `CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_API_TOKEN`) are stored exclusively in `.env` (which is git-ignored). When `pipeline/runlog.py` tracks daily quota per key in `runs.jsonl`, it records only an irreversible 8-character SHA-256 prefix (`key_id`) so secrets never enter git history.

---

## 5. AI Disclosure and Provenance Labelling Plan

1. **In-Video End Card (Mandatory Deliverable):**
   - `pipeline/assemble.py` appends a dedicated **2.6-second AI disclosure end card** to every rendered video (`outputs/radio_cut.mp4`, `outputs/film_9x16.mp4`, and `outputs/film_16x9.mp4`).
   - The card clearly states on screen:
     - **"Abigiya and the Little Star — ኮኮቤ • Kokobe"**
     - **"Made with AI"**
     - **"Narrated with Gemini TTS • Illustrated with FLUX.1 • Assembled with FFmpeg from storyboard.json"**
2. **Platform Disclosure Label:**
   - When publishing the film on **YouTube** (and sharing the public post), the platform's **"Altered or synthetic content"** disclosure setting is switched **ON**, and the video description explicitly states that narration, illustrations, and score were generated via an AI pipeline.
3. **Provenance Metadata Preservation:**
   - The pipeline does not strip or obfuscate SynthID or C2PA provenance watermarks embedded by upstream providers, and `runs.jsonl` provides a complete, public audit trail of every model call, timestamp, prompt length, and parameter set used to produce the film.
