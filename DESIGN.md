# Design

## Film

Title: **Abigiya and the Little Star** (`ኮኮቤ`)

A 65.0-second short film for families and children, exported in both vertical (`9:16`, 720×1280) and horizontal (`16:9`, 1280×720) aspect ratios.

## Audience

Ethiopian families, children, and young people watching with their relatives or on mobile feeds. The story is told gently in Amharic, the way a grandmother tells a bedtime story, with burned-in English subtitles so younger diaspora viewers and international audiences can follow every line.

Where they watch: primarily on a phone in vertical (`9:16`) format on social platforms and messaging groups, and on a laptop or television in horizontal (`16:9`) format.

## Intent

When the film ends, the viewer should feel warm and hopeful: even a small act of kindness can make a difference, and a small light matters.

The viewer should understand this in one sentence: **you do not need to be a star in the sky to bring light to the world—every time you help someone, share kindness, or give hope to someone who feels lonely, you shine.**

---

## Why Every Shot Exists (Shot-by-Shot Intent)

| Shot | Duration | Visual & Camera Motion | Narrative & Emotional Reason |
|---|---|---|---|
| **1** | `5.3s` | Ethiopian village at dusk, small houses and hills in soft light (`push-in`) | Establishes the time, place, and warm storybook mood in Ethiopia. |
| **2** | `5.6s` | Abigiya sits by her bedroom window looking up at the night sky (`pan-right`) | Introduces Abigiya and her nightly habit of wonder and curiosity. |
| **3** | `5.2s` | One small star shining brighter than all the others over the hills (`push-in`) | Introduces the visual motif of the single small bright star (`ኮኮቡኣ`). |
| **4** | `4.8s` | Abigiya smiles and speaks softly toward the star (`push-in`) | Captures her quiet wish: *"I wish I could shine like you."* |
| **5** | `6.4s` | Her grandmother sits nearby and asks her a gentle question (`pan-left`) | Brings in the grandmother's warmth and opens the dialogue. |
| **6** | `5.7s` | Abigiya answers with hands clasped and determined eyes (`push-in`) | Shows Abigiya's pure motivation: stars bring light to darkness, and she wants to make the world better. |
| **7** | `3.2s` | Grandmother smiles and holds Abigiya's hand (`pull-out`) | An emotional pause that grounds their bond before the central lesson. |
| **8** | `9.6s` | Grandmother speaks in warm light; a child helps an elderly neighbour (`push-in`) | Delivers the heart of the film: kindness, helping others, and giving hope to the lonely are how people shine. |
| **9** | `3.7s` | Abigiya looks up at the night sky once more (`pan-left`) | A quiet beat of reflection after her grandmother's words. |
| **10** | `4.1s` | Abigiya holds a small warm light, calm and understanding (`push-in`) | Marks the internal turning point: she realizes even a small light makes a difference. |
| **11** | `5.0s` | Abigiya helps villagers in small ways with lanterns and water (`pan-right`) | Shows her changed actions in the village from that night onward. |
| **12** | `3.8s` (+ `2.6s` card) | Grandmother and Abigiya under the stars + `"Made with AI"` end card (`none`) | Emotional resolution as her grandmother names her **"Kokobe"** (`ኮኮቤ` — "My Star"), followed by the AI disclosure card. |

---

## User Tests and What Changed in `storyboard.json`

### Test 1: Early Narration & Radio Cut Prototype (`outputs/radio_cut.mp4`)

- **Prototype Tested:** Audio-first narration cuts over the gentle Tizita pentatonic lullaby underscore on a black screen with subtitles (`radio_cut.mp4`), tested before locking final visual assembly.
- **Participants (3 target listeners—peers and family reviewers):**
  - **Listener A** (Native Amharic speaker & software peer)
  - **Listener B** (Bilingual Amharic/English viewer who watches mobile shorts)
  - **Listener C** (Family story reviewer)
- **What They Said:**
  1. **Fragmented 12-statement structure vs. a real story:** On our initial draft, Listener A and Listener B pointed out that writing 12 isolated one-line statements sounded like disconnected bullet points rather than a cohesive story with emotional bridges between shots.
  2. **Unnatural literal Amharic & setting mismatch:** When testing the machine-translated Amharic lines and the initial setting (`በጣሊያን` — in Italy), listeners noted that the phrasing felt stiff and that an Ethiopian grandmother-and-granddaughter story (`አቢጊያ` and `ኮኮቤ`) belonged in an Ethiopian village (`በኢትዮጵያ ውብ መንደር`), not Italy.
  3. **Pacing and length (`~112s` vs. `60–90s`):** In the first unedited Abigiya Amharic TTS run (`runs.jsonl` `13:34:41Z`–`13:38:03Z`), Shots 1–10 alone ran `112.6s` (with Shot 8 taking `20.46s`), which listeners felt dragged too slowly for a mobile short.
- **How `storyboard.json` Visibly Changed:**
  1. Replaced the fragmented 12-statement draft with the continuous, natural Amharic bedtime story of Abigiya and her grandmother, written as a unified narrative first and then mapped across the 12 shots (`commit 522ad2a` and `storyboard.json`).
  2. Changed Shot 1's setting in `storyboard.json` from `"በጣሊያን ውስጥ"` (in Italy) to `"በኢትዮጵያ ውብ መንደር"` (in a beautiful village in Ethiopia) and locked the character description to a young Ethiopian girl in braids and an older Ethiopian grandmother in a white shawl.
  3. Tightened the verbose Amharic sentences across Shots 1, 2, 5, 6, and 8 while preserving the exact dialogue and the closing nickname `"ኮኮቤ"` (`Kokobe`), bringing the 12-shot timeline from `>120s` down into the `65.0s–70.0s` target window.

---

### Test 2: Near-Final Cut (`outputs/film_9x16.mp4` and `outputs/film_16x9.mp4`)

- **Prototype Tested:** Full 12-shot cut with Cloudflare FLUX.1-schnell storybook keyframes, Ken Burns camera motion, sidechain-ducked Tizita lullaby score, burned-in English subtitles, and the AI end card.
- **Participants (3 target viewers):**
  - **Viewer A** (Native Amharic speaker listening on headphones)
  - **Viewer B** (Mobile viewer watching the `9:16` vertical cut on a phone screen)
  - **Viewer C** (Desktop viewer watching the `16:9` horizontal cut)
- **What They Said:**
  1. **English prefix glitch & American-accented Amharic in Gemini TTS:** On the first full Abigiya render, Viewer A immediately caught that Gemini TTS was speaking English because of the English style prompt prefix (`"Say in a calm, warm, a little brisker voice:"`). After stripping the English prefix, Gemini TTS spoke Amharic, but Viewer A and Viewer B both noted that the voice sounded *"like someone from the USA trying to speak Amharic"* (English vowel coloration and flattened Amharic ejectives), which distracted from the grandmother-and-child intimacy.
  2. **Visual consistency & subtitle readability:** Viewer B and Viewer C liked the warm hand-painted storybook illustrations and the translucent dark pill behind the English subtitles in the vertical safe area, noting that the gentle Tizita krar lullaby ducked cleanly under the voice without competing with the dialogue.
- **How `storyboard.json` and the Pipeline Visibly Changed:**
  1. Stripped the English style instruction prefix from `pipeline/narration.py` (`prompt_mode: "raw_text"`) so non-English prompts are never contaminated by English instructions.
  2. Added native Ethiopian Amharic neural TTS (`am-ET-MekdesNeural` via `edge-tts`) as the primary voice in `storyboard.json` (`voice.models[0] = "am-ET-MekdesNeural"`, `tempo: 1.0`) while preserving the 3-model Gemini TTS chain (`gemini-3.8-flash-tts`, `gemini-3.8-flash-lite-tts`, `gemini-2.5-flash-preview-tts`) in `voice.models` and keeping the Gemini TTS audio archive in `outputs/narration-gemini-archive/` for comparison.
  3. Re-ran `make film`, producing the final `65.0s` vertical (`outputs/film_9x16.mp4`) and horizontal (`outputs/film_16x9.mp4`) cuts with authentic Ethiopian Amharic narration.

---

## Summary of Key Design Decisions

| Decision | Choice | Why |
|---|---|---|
| **Story** | *Abigiya and the Little Star* (`ኮኮቤ`) | A warm Ethiopian grandmother-and-granddaughter story with a clear visual motif (the bright star) and message |
| **Audience** | Families, children, and diaspora viewers | Suits a gentle bedtime story in Amharic with English subtitles |
| **Intent** | Hope: small kindness makes a difference | Directly reinforces the grandmother's lesson in Shot 8 |
| **Narration Voice** | `am-ET-MekdesNeural` primary + 3-model Gemini TTS failover chain | Native Ethiopian Amharic accent and prosody, backed by automated multi-model failover |
| **Subtitles** | Burned-in English subtitles inside safe margins | Required by the brief; rendered via Pillow + FFmpeg `overlay` so standard FFmpeg works everywhere |
| **Characters** | Fictional Ethiopian girl (Abigiya) and grandmother | Zero real-person likeness/voice risk; consistent across 12 shots via locked character & style block |
| **Visual Style** | Soft hand-painted storybook illustration | Cohesive across shots, ethical (no living artist named), and fits the bedtime tone |
