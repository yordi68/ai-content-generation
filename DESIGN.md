# Design

## Film

Title: **Abigiya and the Little Star** (`ኮኮቤ`)

A **65.0-second** short film (`62.4s` across 12 shots + `2.6s` AI disclosure end card) for Ethiopian families and children, exported in both vertical (`9:16`, 720×1280) and horizontal (`16:9`, 1280×720) aspect ratios.

## Audience

Ethiopian families, children, and diaspora relatives watching together at bedtime or on mobile feeds. The story is narrated in Amharic—the way an Ethiopian grandmother tells an evening story—with burned-in English subtitles so younger diaspora children and non-Amharic speakers can follow every beat.

Where they watch: primarily on a phone in vertical (`9:16`) format on family messaging groups and social feeds, and on a laptop or television in horizontal (`16:9`) format.

## Intent

When the film ends, the viewer should feel warm and hopeful: even a small act of kindness can make a difference, and a small light matters.

The viewer should understand this in one sentence: **you do not need to be a star in the sky to bring light to the world—every time you help someone, share kindness, or give hope to someone who feels lonely, you shine.**

---

## Why Every Shot Exists (Matches `reason` in `storyboard.json`)

| Shot | Duration | Active `characters` | Visual & Camera Motion | Narrative & Emotional Reason (`storyboard.json`) |
|---|---|---|---|---|
| **1** | `5.3s` | `[]` (Landscape only) | Ethiopian highland village at dusk, round stone-and-thatch houses (`push-in`, `slow`) | Establishes the time, place, and warm storybook mood in an Ethiopian highland village before introducing the protagonist. |
| **2** | `5.6s` | `["abigiya"]` | Abigiya sits by her wooden bedroom window looking up at the starry sky (`pan-right`, `slow`) | Introduces Abigiya in her quiet bedroom and establishes her nightly habit of wonder and stargazing. |
| **3** | `5.2s` | `[]` (Sky only) | Wide night sky over dark Ethiopian hills with one small golden star shining brightest (`push-in`, `slow`) | Introduces the central visual motif of the single small bright star in the night sky. |
| **4** | `4.8s` | `["abigiya"]` | Abigiya by the window smiling softly up toward the starlight (`push-in`, `slow`) | Captures Abigiya's quiet wish to shine and bring light like the star. |
| **5** | `6.4s` | `["grandmother", "abigiya"]` | Her grandmother sits nearby in the warm room, asking a gentle question (`pan-left`, `slow`) | Brings in the grandmother's presence and opens the dialogue that drives the lesson. |
| **6** | `5.7s` | `["abigiya"]` | Abigiya turns with hands clasped over her heart and earnest eyes (`push-in`, `slow`) | Reveals Abigiya's motivation: stars bring light to darkness, and she wants to make the world better. |
| **7** | `3.2s` | `["grandmother", "abigiya"]` | Close view of the grandmother smiling warmly and holding Abigiya's hands (`pull-out`, `slow`) | Creates an intimate emotional pause that grounds the bond between grandmother and granddaughter before the main lesson. |
| **8** | `9.6s` | `["grandmother", "abigiya"]` | Grandmother speaks tenderly to Abigiya beside a glowing lantern (`push-in`, `slow`) | Delivers the heart of the story: helping others, sharing kindness, and giving hope are how a person shines. |
| **9** | `3.7s` | `["abigiya"]` | Abigiya looks back up through the window toward the starry night sky (`pan-left`, `slow`) | Provides a quiet beat of reflection as Abigiya connects her grandmother's words to the star above. |
| **10** | `4.1s` | `["abigiya"]` | Abigiya holds a small glowing lantern in both hands, lit with understanding (`push-in`, `slow`) | Marks the internal turning point where she understands that even a small light makes a difference. |
| **11** | `5.0s` | `["abigiya"]` | Abigiya in the village courtyard at dusk sharing lantern light and water (`pan-right`, `slow`) | Shows her changed actions in the community as she brings light and kindness to others. |
| **12** | `3.8s` (+ `2.6s` card) | `["grandmother", "abigiya"]` | Grandmother embracing Abigiya outside under the starry sky + `"Made with AI"` end card (`none`) | Delivers the emotional payoff as her grandmother names her 'Kokobe' (My Star), leading into the AI disclosure end card. |

---

## User Tests and How `storyboard.json` Visibly Changed in Git

### Test 1: Radio Cut & Early Story Prototype (`commits 30fcc83` & `a215726` → `commit d32e9de`)

- **Prototype Tested:** Our first narration-only prototypes (`runs.jsonl` lines 4–58, `07:35:50Z`–`12:01:44Z`) and the first unedited Abigiya Amharic reading (`runs.jsonl` lines 59–70, `12:44:02Z`–`12:50:13Z`).
- **Participants (3 target audience members—family & diaspora listeners):**
  - **Participant 1 (Older Ethiopian family member, native Amharic speaker):** Represents the parent/grandparent generation who passes down family stories.
  - **Participant 2 (10-year-old younger cousin):** Represents the children's audience for bedtime stories.
  - **Participant 3 (Young adult diaspora relative watching on mobile):** Represents bilingual Amharic/English mobile viewers.
- **What They Said:**
  1. **12 disconnected statements vs. a real family story:** When listening to our first 12-shot draft (`commit 30fcc83` / `commit a215726`, *A New Life for a Software Engineer*, and its literal Amharic translation in `runs.jsonl` lines 47–58), Participant 1 and Participant 3 said the 12 lines sounded like isolated statements rather than a warm family story they would watch with children (`FAILURES.md`, Entry 0), and that literal machine-translated Amharic technical terms (`ሰው ሰራሽ ብልህነት`, `ሞዴሎቹ`) sounded cold and unnatural.
  2. **First Abigiya reading was too slow (`112.61s` across 10 shots):** When we tested the first unedited *Abigiya and the Little Star* Amharic narration (`runs.jsonl` lines 59–70, `12:44:02Z`–`12:50:13Z`), Participant 2 and Participant 3 liked the grandmother-and-star story, but pointed out that Shots 1–10 alone took `112.61s` (with Shot 8 running `20.46s` at `runs.jsonl` line 68, `12:49:36Z`), which dragged and exceeded the 90-second limit.
- **How `storyboard.json` Visibly Changed (`git diff a215726..d32e9de storyboard.json`):**
  1. Replaced the 12-statement developer script in `storyboard.json` with the unified 12-shot Ethiopian bedtime story ***Abigiya and the Little Star* (`ኮኮቤ`)**, set in an Ethiopian village (`በኢትዮጵያ ውብ መንደር`).
  2. Tightened the Amharic sentence phrasing across Shots 1, 2, 5, 6, and 8 in `storyboard.json` so Shot 8 dropped from `20.46s` (`runs.jsonl` line 68) to `12.20s` on Gemini TTS (`runs.jsonl` line 78) and `9.10s` on `am-ET-MekdesNeural` (`runs.jsonl` line 172), bringing the complete 12-shot film runtime to **`65.0s`**.

---

### Test 2: Near-Final Cut (`outputs/film_9x16.mp4` and `outputs/film_16x9.mp4`, `v1` → `v2`)

- **Prototype Tested:** The first assembled 12-shot video (`runs.jsonl` lines 71–125, `13:01:40Z`–`14:02:30Z`) with `keyframes-v1` (`outputs/keyframes-v1-archive/`) and Gemini TTS Amharic narration (`outputs/narration-gemini-archive/`).
- **Participants (same 3 target audience groups watching the video cut):**
  - **Participant 1 (Ethiopian family elder listening on speaker)**
  - **Participant 2 (10-year-old child viewer watching the story illustrations)**
  - **Participant 3 (Bilingual mobile viewer watching `film_9x16.mp4` on a phone)**
- **What They Said:**
  1. **American accent on Amharic Gemini TTS:** After we stripped the English style prefix (`runs.jsonl` lines 71–83), Gemini TTS read the Amharic words, but Participant 1 and Participant 3 immediately noted that the voice sounded *"like someone from the USA trying to speak Amharic"* (`FAILURES.md`, Entry 9), losing the warmth of an Ethiopian grandmother's storytelling.
  2. **Characters appearing in the village & star shots, three grandmothers in Shot 8, and shifting dress colors:** Participant 2 pointed out that in Shot 1 (when the narrator talks about the village) and Shot 3 (when the narrator talks about the single bright star in the sky), two people were standing right in the frame instead of just the village and the star; in Shot 8, three different grandmothers appeared in the same room; and Abigiya's dress changed color from green/blue to orange to red across shots (`FAILURES.md`, Entry 12).
  3. **Shot 8 vertical subtitle box too tall:** Participant 3 noted that Shot 8's 160-character English subtitle wrapped onto 5 lines on the vertical `9:16` cut, crowding the lower picture.
- **How `storyboard.json` and the Pipeline Visibly Changed (`runs.jsonl` lines 165–215):**
  1. **Changed `storyboard.json` to add per-shot `characters` and locked outfit colors:** Added `"characters": []` on Shot 1 (village) and Shot 3 (star), `"characters": ["abigiya"]` on solo shots, and `"characters": ["grandmother", "abigiya"]` on duo shots; simplified Shot 8's `picture` prompt so it no longer asked for a second elder; and locked Abigiya's outfit in `storyboard.json` to `"two neat braids wearing a warm yellow-and-teal dress"` and the grandmother's to `"traditional white cotton netela shawl"`. Regenerated the keyframes (`runs.jsonl` lines 177–189).
  2. **Switched primary voice in `storyboard.json` to native Ethiopian Amharic (`am-ET-MekdesNeural`):** Set `voice.models[0]` to `"am-ET-MekdesNeural"` (`provider: "edge-tts"`, `tempo: 1.0`) and ran `pipeline/narration.py` (`runs.jsonl` lines 165–176) while keeping the 3-model Gemini TTS failover chain in `voice.models[1..3]`.
  3. **Split long subtitles (>85 chars) into two timed cues:** Updated `pipeline/assemble.py` (`split_subtitle_cues()`) so Shot 8's subtitle splits across two timed 2–3 line cards (`0.0s..3.55s` and `3.55s..9.60s`), keeping vertical subtitles strictly inside the safe area.
