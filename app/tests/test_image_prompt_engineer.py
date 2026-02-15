import unittest

from app.core.brains.image_prompt_engineer import (
    _detect_mandatory_focus_tags,
    _enforce_tag_policy,
)


def _split(prompt: str) -> list[str]:
    return [tag.strip() for tag in prompt.split(",") if tag.strip()]


class TestImagePromptEngineerPolicy(unittest.TestCase):
    def test_feet_request_enforces_focus_and_pov_closeup(self):
        mandatory = _detect_mandatory_focus_tags("show your feet", "")
        output = _enforce_tag_policy(
            "1girl, solo, rating:sensitive, smile, bedroom, dim_lighting",
            mandatory_focus_tags=mandatory,
        )
        tags = set(_split(output))

        self.assertIn("pov", tags)
        self.assertIn("close-up", tags)
        self.assertIn("feet", tags)
        self.assertIn("foot_focus", tags)
        self.assertNotIn("full_body", tags)

    def test_far_framing_tags_are_removed(self):
        output = _enforce_tag_policy(
            "1girl, solo, rating:general, full_body, wide_shot, long_shot, multiple_views, smile"
        )
        tags = set(_split(output))

        self.assertNotIn("full_body", tags)
        self.assertNotIn("wide_shot", tags)
        self.assertNotIn("long_shot", tags)
        self.assertNotIn("multiple_views", tags)

    def test_scene_lock_preserves_clothing_and_environment(self):
        output = _enforce_tag_policy(
            "1girl, solo, rating:questionable, pov, close-up, blush",
            scene_lock={"clothing": ["lingerie"], "environment": ["bedroom", "dim_lighting"]},
            preserve_scene_lock_clothing=True,
            preserve_scene_lock_environment=True,
        )
        tags = set(_split(output))

        self.assertIn("lingerie", tags)
        self.assertIn("bedroom", tags)
        self.assertIn("dim_lighting", tags)

    def test_male_body_tags_are_removed(self):
        output = _enforce_tag_policy(
            "1girl, 1boy, male_focus, rating:explicit, pov, close-up, hetero, sex, bedroom"
        )
        tags = set(_split(output))

        self.assertNotIn("1boy", tags)
        self.assertNotIn("male_focus", tags)
        self.assertIn("pov", tags)
        self.assertIn("close-up", tags)

    def test_aliases_are_normalized(self):
        output = _enforce_tag_policy(
            "1girl, solo, rating:sensitive, soft_smile, flushed, bedroom"
        )
        tags = set(_split(output))

        self.assertIn("light_smile", tags)
        self.assertIn("blush", tags)
        self.assertNotIn("soft_smile", tags)
        self.assertNotIn("flushed", tags)

    def test_required_core_and_single_rating_are_enforced(self):
        output = _enforce_tag_policy(
            "smile, bedroom, dim_lighting, rating:general, rating:questionable"
        )
        tags = _split(output)
        tag_set = set(tags)

        ratings = [tag for tag in tags if tag.startswith("rating:")]
        self.assertEqual(len(ratings), 1)
        self.assertIn("1girl", tag_set)
        self.assertIn("solo", tag_set)
        self.assertIn("pov", tag_set)
        self.assertIn("close-up", tag_set)

    def test_output_is_trimmed_to_max_tag_limit(self):
        raw = ", ".join(
            [
                "1girl",
                "solo",
                "rating:sensitive",
                "pov",
                "close-up",
                "upper_body",
                "cowboy_shot",
                "smile",
                "light_smile",
                "blush",
                "parted_lips",
                "looking_at_viewer",
                "lingerie",
                "bra",
                "panties",
                "bedroom",
                "indoors",
                "night",
                "dim_lighting",
                "depth_of_field",
                "blurry_background",
                "lens_flare",
                "bloom",
                "hand_focus",
                "breast_focus",
                "foot_focus",
                "feet",
            ]
        )
        output = _enforce_tag_policy(raw)
        tags = _split(output)

        self.assertLessEqual(len(tags), 24)
        self.assertIn("1girl", tags)
        self.assertIn("solo", tags)
        self.assertIn("pov", tags)
        self.assertIn("close-up", tags)


if __name__ == "__main__":
    unittest.main()
