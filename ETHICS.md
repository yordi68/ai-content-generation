# Ethics, Consent, Licences, and AI Labelling

## 1. Consent Record (Likeness and Voice Gate)

- **Characters:** Both characters depicted in *Abigiya and the Little Star*—**Abigiya** (an 8-year-old girl in an Ethiopian village) and her **grandmother**—are fictional storybook characters illustrated from text descriptions (`"soft hand-painted storybook illustration"`).
- **Faces and Likenesses:** No real person's photograph, face, or physical likeness was used as an input, reference image, or prompt target at any stage of the pipeline.
- **Voice and Narration:** The narration uses prebuilt synthetic text-to-speech voices (`am-ET-MekdesNeural` as the primary Ethiopian Amharic voice and `Kore` on Google Gemini TTS in the failover chain). No voice cloning or voice replication of any real person was performed. During development, I explicitly evaluated and rejected cross-provider voice cloning (`FAILURES.md`, Section 1) because cloning requires recording and storing a real person's voice along with formal written consent.
- **Gate Compliance:** Because no real person is shown or voiced, no individual likeness/voice release is required, and zero unconsented biometric data exists in the repository or outputs.

---

## 2. Model, Tool, and Output Licences

Every model, library, and tool used in the pipeline has been checked for licence terms and output usage rights:

| Component | Model / Package | Licence / Service Terms | Output & Commercial Usage Notes |
|---|---|---|---|
| **Repository Code** | `ai-content-generation` | **MIT Licence** (`LICENSE`) | Open-source; anyone may clone, modify, and run the pipeline. |
| **Keyframes** | Black Forest Labs `FLUX.1-schnell` (via Cloudflare Workers AI `@cf/black-forest-labs/flux-1-schnell`) | **Apache-2.0** | Permissive open-weight licence; generated images may be used and distributed freely under Apache-2.0 and Cloudflare Workers AI terms. |
| **Primary Narration (Amharic)** | Microsoft `am-ET-MekdesNeural` (via `edge-tts 7.3.1`) | **LGPL-3.0** (Python client library) / **Microsoft Edge Read-Aloud Service Terms** | Used for this non-commercial educational challenge submission because it provides native Ethiopian Amharic phonology without a payment card. Note: Microsoft's keyless Edge Read-Aloud endpoint is not licensed for commercial production; commercial deployments should either supply a paid Azure Speech key or set `voice.models[0]` in `storyboard.json` to `gemini-3.8-flash-tts` / local `piper-tts`. |
| **Failover Narration Chain** | Google `gemini-3.8-flash-tts`, `gemini-3.8-flash-lite-tts`, `gemini-2.5-flash-preview-tts` | **Google Gemini API Terms of Service** | Generated audio outputs belong to the user/developer subject to Google's Generative AI Prohibited Use Policy. Free-tier prompts may be reviewed by Google for service improvement. |
| **Local CPU Narration (`local-voice` branch)** | `piper-tts` (`en_US-lessac-medium.onnx`) | **MIT Licence** (code) / **CC-BY-4.0** (Lessac voice dataset) | Permissive open-source local synthesis; requires attribution to Ryan Lessac / Piper voice contributors. |
| **Score (Local Floor & Optional GPU)** | Local Tizita Pentatonic Synthesizer (`pipeline/music.py`) / optional `ACE-Step 1.5` override | **MIT Licence** | Deterministic Python synthesis in `pipeline/music.py` is MIT-licensed in this repo. (If an optional ACE-Step 1.5 override is supplied, ACE-Step 1.5 weights and outputs are also MIT-licensed.) |
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
   - The card matches the active pipeline configuration in `storyboard.json` and clearly states on screen:
     - **"Abigiya and the Little Star — ኮኮቤ • Kokobe"**
     - **"Made with AI"**
     - **"Narrated with am-ET-MekdesNeural (Edge TTS) & Gemini TTS"**
     - **"Illustrated with FLUX.1-schnell • Assembled with FFmpeg"**
2. **Platform Disclosure Label:**
   - When publishing the film on **YouTube** (and sharing the public post), the platform's **"Altered or synthetic content"** disclosure setting is switched **ON**, and the video description explicitly states that narration, illustrations, and score were generated via an AI pipeline.
3. **Provenance Metadata and Re-Encoding Honesty:**
   - Note on C2PA / container metadata: because `pipeline/shots.py` and `pipeline/assemble.py` animate the raw JPEG keyframes (`zoompan`), composite PNG subtitle overlays, and encode the video stream with `libx264` and the audio stream with `aac`, any file-header C2PA metadata on individual upstream JPEG or WAV files does not survive FFmpeg re-encoding into the final MP4 container.
   - To keep the final MP4s transparent about their origin despite container re-encoding, provenance is preserved through three mechanisms: (1) the burned-in visual `"Made with AI"` end card inside the video frames themselves, (2) the platform's synthetic-content disclosure flag, and (3) the committed `runs.jsonl` log and `outputs/<stage>/*.json` SHA-256 cache sidecars in this repository.
