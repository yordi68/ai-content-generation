# AI Content Generation

A contract-driven film studio: one validated JSON document describes a short film, and a fixed sequence of stages turns it into narration, images, moving shots, a score, and finished MP4s. The web studio lets someone who does not code create their own film through the same pipeline.

## Language

### Story Inputs

**Story Prompt**:
A short idea or theme a person types (one to three sentences) that the drafting model expands into a Script.
_Avoid_: idea, brief, topic

**Script**:
The continuous written narrative of one film before it is divided into Shots.
_Avoid_: story text, copy, content

**Storyboard**:
The complete plan for one film (`storyboard.json`): film-level direction (title, style, characters, voice, music cues) plus an ordered list of 8–12 Shots.
_Avoid_: storyboard file, project, script

**Shot**:
One numbered segment of a Storyboard, bundling its Amharic `narration`, English `subtitle`, visual `picture` prompt, active `characters`, camera `motion`, `duration_s`, `seed`, and `reason`, together with the artifacts generated from it (narration audio, keyframe image, moving clip).
_Avoid_: scene, section, panel, frame

**Film Cut**:
A finished video file rendered from a Storyboard. One Storyboard produces three: the vertical `9:16` cut, the horizontal `16:9` cut, and the narration-only radio cut.
_Avoid_: video, output, export

### Studio

**Project Workspace**:
The isolated folder holding one Storyboard and everything generated from it (`projects/<slug>/`), so two films never share media or cache.
_Avoid_: project, job, session

**Stage**:
One step of the pipeline that reads the Storyboard, produces artifacts, and logs its calls: `script`, `narration`, `keyframes`, `shots`, `music`, `assemble`.
_Avoid_: step, phase, task

**Run Log**:
The append-only `runs.jsonl` record of every model or tool call: timestamp, stage, model, latency, status, cost, and project.
_Avoid_: log, history, telemetry

**Cache Sidecar**:
A small committed JSON file beside each artifact recording the SHA-256 `cache_key` that produced it, so a re-run can prove a stage was skipped rather than repeated.
_Avoid_: metadata, manifest, hash file
