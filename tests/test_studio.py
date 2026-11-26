import json
import sys
import tempfile
import unittest
from pathlib import Path

PIPELINE_DIR = Path(__file__).resolve().parents[1] / "pipeline"
sys.path.insert(0, str(PIPELINE_DIR))

import script  # noqa: E402
import studio  # noqa: E402
from validate import validate  # noqa: E402

ROOT_BOARD = json.loads((PIPELINE_DIR.parent / "storyboard.json").read_text(encoding="utf-8"))


def synthetic_draft(shot_count=8):
    shots = []
    for index in range(1, shot_count + 1):
        shots.append(
            {
                "id": index,
                "narration": "A short spoken line for the story.",
                "subtitle": "A short English subtitle.",
                "picture": "A courtyard at dusk with one warm lamp.",
                "characters": [],
                "motion": {"type": "push-in", "amount": "slow"},
                "duration_s": None,
                "seed": 100 + index,
                "reason": "Moves the story forward with one clear image.",
            }
        )
    return {
        "title": "The Lantern Keeper",
        "title_local": "የፋኖሱ ጠባቂ",
        "aspect_ratios": ["9:16", "16:9"],
        "style_block": "ignored by normalise",
        "character": "A grandmother and her granddaughter.",
        "characters": {"grandmother": "an older woman in a white shawl"},
        "voice": {},
        "music": [{"id": "cue_01", "start_shot": 1, "end_shot": shot_count, "caption": "soft lullaby"}],
        "shots": shots,
    }


class StudioTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.original_projects = studio.PROJECTS_DIR
        studio.PROJECTS_DIR = Path(self.temp.name) / "projects"
        studio.PROJECTS_DIR.mkdir(parents=True)
        self.slug = studio.create_project(
            "The Lantern Keeper", "prompt", "A grandmother teaches her granddaughter about light.", "", "am", "storybook"
        )
        studio.save_storyboard(self.slug, json.loads(json.dumps(ROOT_BOARD)))

    def tearDown(self):
        studio.PROJECTS_DIR = self.original_projects
        self.temp.cleanup()

    def test_slugify_is_stable_and_ascii(self):
        self.assertEqual(studio.slugify("Abigiya and the Little Star"), "abigiya-and-the-little-star")
        self.assertEqual(studio.slugify("ኮኮቤ"), "film")
        self.assertNotEqual(studio.unique_slug("The Lantern Keeper"), self.slug)

    def test_plan_stages_follows_field_dependencies(self):
        base = {"narration": "a", "subtitle": "b", "picture": "c", "characters": [], "motion": {"type": "none", "amount": "none"}, "seed": 1, "reason": "why"}

        self.assertEqual(studio.plan_stages(base, {**base, "subtitle": "new"}), [])
        self.assertEqual(studio.plan_stages(base, {**base, "motion": {"type": "pan-left", "amount": "slow"}}), ["shots"])
        self.assertEqual(
            studio.plan_stages(base, {**base, "picture": "new"}),
            ["keyframes", "shots"],
        )
        self.assertEqual(
            studio.plan_stages(base, {**base, "narration": "new"}),
            ["narration", "shots", "music"],
        )
        self.assertEqual(studio.plan_stages(base, {**base, "reason": "new reason"}), [])

    def test_shot_edit_persists_and_returns_stages(self):
        _, stages = studio.apply_shot_edit(self.slug, 2, {"subtitle": "A new subtitle for the second shot."})
        self.assertEqual(stages, [])
        saved = studio.storyboard(self.slug)
        self.assertEqual(saved["shots"][1]["subtitle"], "A new subtitle for the second shot.")
        summary = studio.project_summary(self.slug)
        self.assertTrue(summary["film_stale"])
        self.assertFalse(any(shot["stale"] for shot in summary["shots"]))
        studio.clear_build_state(self.slug)
        self.assertFalse(studio.project_summary(self.slug)["film_stale"])

    def test_media_edit_marks_the_shot_until_it_is_rebuilt(self):
        _, stages = studio.apply_shot_edit(self.slug, 2, {"picture": "A new picture prompt."})
        self.assertEqual(stages, ["keyframes", "shots"])
        summary = studio.project_summary(self.slug)
        self.assertTrue(summary["shots"][1]["stale"])
        self.assertFalse(summary["shots"][0]["stale"])
        self.assertTrue(summary["film_stale"])
        studio.clear_build_state(self.slug, [2])
        summary = studio.project_summary(self.slug)
        self.assertFalse(summary["shots"][1]["stale"])
        self.assertTrue(summary["film_stale"])
        studio.clear_build_state(self.slug)
        self.assertFalse(studio.project_summary(self.slug)["film_stale"])

    def test_reason_only_edit_does_not_mark_the_shot_or_cuts_dirty(self):
        _, stages = studio.apply_shot_edit(self.slug, 3, {"reason": "A clearer reason."})
        self.assertEqual(stages, [])
        summary = studio.project_summary(self.slug)
        self.assertFalse(summary["shots"][2]["stale"])
        self.assertFalse(summary["film_stale"])

    def test_shot_edit_rejects_unknown_character(self):
        with self.assertRaises(ValueError):
            studio.apply_shot_edit(self.slug, 2, {"characters": ["alien"]})

    def test_summary_reports_missing_artifacts(self):
        summary = studio.project_summary(self.slug)
        self.assertEqual(summary["slug"], self.slug)
        self.assertTrue(summary["storyboard_exists"])
        self.assertTrue(summary["shots"][0]["missing"])
        self.assertEqual(summary["total_seconds"], 65.0)

    def test_showcase_is_read_only(self):
        with self.assertRaises(PermissionError):
            studio.apply_shot_edit(studio.SHOWCASE_SLUG, 1, {"subtitle": "no"})
        with self.assertRaises(PermissionError):
            studio.delete_project(studio.SHOWCASE_SLUG)

    def test_delete_removes_workspace(self):
        root = studio.project_root(self.slug)
        studio.delete_project(self.slug)
        self.assertFalse(root.exists())


class ScriptNormaliseTests(unittest.TestCase):
    def test_normalise_repairs_film_level_fields(self):
        meta = {"title": "", "inputs": {}}
        inputs = {"mode": "prompt", "story_prompt": "A lamp", "script": "", "language": "am", "style": "storybook"}
        board = script.normalise(synthetic_draft(), meta, inputs)
        self.assertEqual(board["aspect_ratios"], ["9:16", "16:9"])
        self.assertEqual(board["style_block"], studio.STYLE_BLOCKS["storybook"])
        self.assertEqual(board["voice"], studio.VOICE_PRESETS["am"])
        self.assertEqual(board["music"][0]["end_shot"], 8)
        self.assertTrue(all(shot["duration_s"] is None for shot in board["shots"]))
        self.assertEqual(validate(board), [])

    def test_normalise_drops_unknown_character_keys(self):
        draft = synthetic_draft()
        draft["shots"][0]["characters"] = ["grandmother", "alien"]
        meta = {"title": "", "inputs": {}}
        inputs = {"mode": "prompt", "story_prompt": "A lamp", "script": "", "language": "am", "style": "storybook"}
        board = script.normalise(draft, meta, inputs)
        self.assertEqual(board["shots"][0]["characters"], ["grandmother"])


class SchemaTests(unittest.TestCase):
    def test_unknown_character_key_is_rejected_by_validate(self):
        board = json.loads(json.dumps(ROOT_BOARD))
        board["shots"][0]["characters"] = ["alien"]
        errors = validate(board)
        self.assertTrue(any("Unknown character keys" in error.message for error in errors))

    def test_runtime_outside_window_is_rejected(self):
        board = json.loads(json.dumps(ROOT_BOARD))
        board["shots"][0]["duration_s"] = 40
        errors = validate(board)
        self.assertTrue(any("60.0..90.0s" in error.message for error in errors))


if __name__ == "__main__":
    unittest.main()
