import unittest

from app.core.brains.gift_recommendation_brain import (
    classify_scene_mode,
    decide_gift_recommendation,
)
from app.core.catalog.gifts import get_shop_items_map


class TestGiftRecommendationBrain(unittest.TestCase):
    def test_too_early_blocks_suggestion(self):
        result = decide_gift_recommendation(
            state='relationshipStage="lover" | description="we are chatting"',
            dialogue_response="_I smile softly_",
            user_message="hi",
            chat_ext={},
            current_user_message_count=10,
            recent_purchases=[],
        )
        self.assertFalse(result["should_suggest"])
        self.assertEqual(result["reason"], "too_early")

    def test_cadence_blocks_until_20_user_messages(self):
        result = decide_gift_recommendation(
            state='relationshipStage="lover" | description="we are chatting"',
            dialogue_response="_I smile softly_",
            user_message="hi",
            chat_ext={"last_gift_suggestion_user_count": 40},
            current_user_message_count=55,
            recent_purchases=[],
        )
        self.assertFalse(result["should_suggest"])
        self.assertEqual(result["reason"], "cadence_block")

    def test_first_suggestion_waits_for_exact_boundary(self):
        result = decide_gift_recommendation(
            state='relationshipStage="lover" | description="we are chatting"',
            dialogue_response="_I smile softly_",
            user_message="hi",
            chat_ext={},
            current_user_message_count=21,
            recent_purchases=[],
        )
        self.assertFalse(result["should_suggest"])
        self.assertEqual(result["reason"], "cadence_wait_boundary")

    def test_purchase_blackout_blocks_for_20_user_messages(self):
        result = decide_gift_recommendation(
            state='relationshipStage="lover" | description="we are chatting"',
            dialogue_response="_I smile softly_",
            user_message="hi",
            chat_ext={"last_gift_purchase_user_count": 50},
            current_user_message_count=65,
            recent_purchases=[],
        )
        self.assertFalse(result["should_suggest"])
        self.assertEqual(result["reason"], "purchase_cooldown")

    def test_explicit_scene_prefers_adult_and_no_repeat(self):
        result = decide_gift_recommendation(
            state='relationshipStage="lover" | description="we are having sex on the beach"',
            dialogue_response="_I moan and move with you_",
            user_message="let's fuck harder",
            chat_ext={
                "last_gift_suggestion_user_count": 0,
                "last_gift_suggested_item_key": "anal_beads",
            },
            current_user_message_count=60,
            recent_purchases=[],
        )
        self.assertTrue(result["should_suggest"])
        self.assertIn(result["item_key"], {"anal_beads", "vibrator"})
        self.assertNotEqual(result["item_key"], "anal_beads")

    def test_normal_scene_uses_light_pool(self):
        result = decide_gift_recommendation(
            state='relationshipStage="lover" | description="we are walking in the park"',
            dialogue_response="_I laugh and hold your hand_",
            user_message="how was your day",
            chat_ext={"last_gift_suggestion_user_count": 0},
            current_user_message_count=80,
            recent_purchases=[],
        )
        self.assertTrue(result["should_suggest"])
        shop_items = get_shop_items_map()
        self.assertNotEqual(shop_items[result["item_key"]].get("category"), "adult")

    def test_refusal_downgrades_scene_to_normal(self):
        scene = classify_scene_mode(
            state='relationshipStage="lover" | description="we are having sex"',
            dialogue_response="_I recoil and step back. I won't do it like that._",
            user_message="fuck me",
        )
        self.assertEqual(scene, "normal")


if __name__ == "__main__":
    unittest.main()
