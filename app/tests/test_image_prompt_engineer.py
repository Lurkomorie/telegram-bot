import unittest

from app.core.brains.image_prompt_engineer import (
    _build_image_context,
    _detect_mandatory_focus_tags,
    _enforce_tag_policy,
    _should_use_scene_lock,
)


def _split(prompt: str) -> list[str]:
    return [tag.strip() for tag in prompt.split(",") if tag.strip()]


class TestImagePromptEngineerPolicy(unittest.TestCase):
    def test_history_start_source_disables_scene_lock(self):
        self.assertFalse(_should_use_scene_lock({"source": "history_start"}))
        self.assertFalse(_should_use_scene_lock({"source": "ai_initial_story"}))
        self.assertFalse(_should_use_scene_lock({"source": "gift_purchase"}))
        self.assertTrue(_should_use_scene_lock({"source": "message_response"}))

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
        self.assertFalse(any(tag.startswith("rating:") for tag in tags))

    def test_far_framing_tags_are_removed(self):
        output = _enforce_tag_policy(
            "1girl, solo, rating:general, full_body, wide_shot, long_shot, multiple_views, smile"
        )
        tags = set(_split(output))

        self.assertNotIn("full_body", tags)
        self.assertNotIn("wide_shot", tags)
        self.assertNotIn("long_shot", tags)
        self.assertNotIn("multiple_views", tags)
        self.assertFalse(any(tag.startswith("rating:") for tag in tags))

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
        self.assertFalse(any(tag.startswith("rating:") for tag in tags))

    def test_scene_lock_is_fallback_only_when_current_turn_has_buckets(self):
        output = _enforce_tag_policy(
            "1girl, solo, rating:questionable, pov, close-up, sundress, beach, smile",
            scene_lock={"clothing": ["lingerie"], "environment": ["bedroom", "dim_lighting"]},
            preserve_scene_lock_clothing=True,
            preserve_scene_lock_environment=True,
        )
        tags = set(_split(output))

        self.assertIn("sundress", tags)
        self.assertIn("beach", tags)
        self.assertNotIn("lingerie", tags)
        self.assertNotIn("bedroom", tags)
        self.assertFalse(any(tag.startswith("rating:") for tag in tags))

    def test_male_body_tags_are_removed(self):
        output = _enforce_tag_policy(
            "1girl, 1boy, male_focus, rating:explicit, pov, close-up, hetero, sex, bedroom"
        )
        tags = set(_split(output))

        self.assertNotIn("1boy", tags)
        self.assertNotIn("male_focus", tags)
        self.assertIn("pov", tags)
        self.assertIn("close-up", tags)
        self.assertFalse(any(tag.startswith("rating:") for tag in tags))

    def test_gift_override_is_not_auto_applied_without_force(self):
        context, _, _, _, _ = _build_image_context(
            state='relationshipStage="lover" | emotions="happy" | moodNotes="" | location="bedroom" | description="" | aiClothing="lingerie" | userClothing="unknown" | terminateDialog=false | terminateReason=""',
            dialogue_response="_I smile softly_",
            user_message="hello",
            persona={},
            chat_history=[],
            previous_image_prompt="1girl, solo, bedroom",
            previous_image_meta={"source": "message_response"},
            purchases=[{"item_name": "Vibrator", "context_effect": "vibrator, masturbation", "messages_since": 0}],
            force_gift_override=False,
            forced_gift_tags="",
        )
        self.assertNotIn("GIFT OVERRIDE", context)

    def test_gift_override_is_present_only_when_forced(self):
        context, _, _, _, _ = _build_image_context(
            state='relationshipStage="lover" | emotions="happy" | moodNotes="" | location="bedroom" | description="" | aiClothing="lingerie" | userClothing="unknown" | terminateDialog=false | terminateReason=""',
            dialogue_response="_I smile softly_",
            user_message="hello",
            persona={},
            chat_history=[],
            previous_image_prompt="1girl, solo, bedroom",
            previous_image_meta={"source": "message_response"},
            purchases=[{"item_name": "Vibrator", "context_effect": "vibrator, masturbation", "messages_since": 0}],
            force_gift_override=True,
            forced_gift_tags="vibrator, masturbation",
        )
        self.assertIn("GIFT OVERRIDE", context)
        self.assertIn("vibrator, masturbation", context)

    def test_refusal_suppresses_user_focus_tags(self):
        _, mandatory_focus_tags, _, _, observability = _build_image_context(
            state='relationshipStage="lover" | emotions="nervous" | moodNotes="" | location="pond" | description="" | aiClothing="shorts, blouse" | userClothing="unknown" | terminateDialog=false | terminateReason=""',
            dialogue_response="_I recoil and step back, cheeks burning. Not in public... only if you catch me first._",
            user_message="show pussy",
            persona={},
            chat_history=[],
            previous_image_prompt=None,
            previous_image_meta={"source": "message_response"},
            force_gift_override=False,
            forced_gift_tags="",
        )
        self.assertEqual(mandatory_focus_tags, [])
        self.assertTrue(observability["refusal_detected"])

    def test_aliases_are_normalized(self):
        output = _enforce_tag_policy(
            "1girl, solo, rating:sensitive, soft_smile, flushed, bedroom"
        )
        tags = set(_split(output))

        self.assertIn("light_smile", tags)
        self.assertIn("blush", tags)
        self.assertNotIn("soft_smile", tags)
        self.assertNotIn("flushed", tags)
        self.assertFalse(any(tag.startswith("rating:") for tag in tags))

    def test_required_core_and_no_rating_tags_are_enforced(self):
        output = _enforce_tag_policy(
            "smile, bedroom, dim_lighting, rating:general, rating:questionable"
        )
        tags = _split(output)
        tag_set = set(tags)

        ratings = [tag for tag in tags if tag.startswith("rating:")]
        self.assertEqual(len(ratings), 0)
        self.assertIn("1girl", tag_set)
        self.assertIn("solo", tag_set)
        self.assertIn("pov", tag_set)
        self.assertIn("close-up", tag_set)
        self.assertIn("eye_focus", tag_set)

    def test_eye_quality_booster_added_for_normal_portraits(self):
        output = _enforce_tag_policy(
            "1girl, solo, rating:sensitive, pov, close-up, smile, bedroom"
        )
        tags = set(_split(output))
        self.assertIn("eye_focus", tags)
        self.assertTrue("looking_at_viewer" in tags or "eye_contact" in tags)
        self.assertFalse(any(tag.startswith("rating:") for tag in tags))

    def test_eye_quality_booster_skips_when_closed_eyes(self):
        output = _enforce_tag_policy(
            "1girl, solo, rating:sensitive, pov, close-up, closed_eyes, smile, bedroom"
        )
        tags = set(_split(output))
        self.assertNotIn("eye_focus", tags)
        self.assertFalse(any(tag.startswith("rating:") for tag in tags))

    def test_eye_quality_booster_skips_for_heavy_body_focus(self):
        output = _enforce_tag_policy(
            "1girl, solo, rating:questionable, pov, close-up, feet, foot_focus, bedroom"
        )
        tags = set(_split(output))
        self.assertNotIn("eye_focus", tags)
        self.assertFalse(any(tag.startswith("rating:") for tag in tags))

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
