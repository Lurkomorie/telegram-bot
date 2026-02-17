import unittest

from app.core.catalog.gifts import get_gift_catalog, get_shop_items_map
from app.db.crud import get_shop_items


EXPECTED_GIFT_KEYS = {
    "flower_bouquet",
    "wine_bottle",
    "dildo",
    "anal_plug",
    "cute_pajamas",
    "engagement_ring",
    "bondage_rope",
    "lace_lingerie",
    "fox_ears_headband",
    "control_orb",
}


class TestGiftCatalog(unittest.TestCase):
    def test_catalog_contains_exactly_10_expected_gifts(self):
        catalog = get_gift_catalog()
        self.assertEqual(set(catalog.keys()), EXPECTED_GIFT_KEYS)
        self.assertEqual(len(catalog), 10)

    def test_catalog_items_have_required_translation_and_icon_fields(self):
        catalog = get_gift_catalog()
        for key, item in catalog.items():
            self.assertEqual(item.get("key"), key)
            self.assertIn("translations", item)
            self.assertIn("ui", item)

            name = item["translations"].get("name", {})
            subtitle = item["translations"].get("subtitle", {})
            self.assertTrue(name.get("en"))
            self.assertTrue(name.get("ru"))
            self.assertIn("en", subtitle)
            self.assertIn("ru", subtitle)

            ui = item["ui"]
            self.assertTrue(ui.get("icon_lucide"))
            self.assertTrue(ui.get("icon_emoji_fallback"))
            self.assertIn("image_path", ui)

    def test_shop_items_map_contains_additive_metadata(self):
        items = get_shop_items_map(include_scene_override=False)
        self.assertEqual(set(items.keys()), EXPECTED_GIFT_KEYS)
        for key, item in items.items():
            self.assertEqual(item.get("name_en"), get_gift_catalog()[key]["translations"]["name"]["en"])
            self.assertEqual(item.get("name_ru"), get_gift_catalog()[key]["translations"]["name"]["ru"])
            self.assertIn("subtitle_en", item)
            self.assertIn("subtitle_ru", item)
            self.assertIn("icon_lucide", item)
            self.assertIn("icon_emoji_fallback", item)
            self.assertIn("image_path", item)

    def test_crud_shop_items_sorted_and_counted(self):
        items = get_shop_items()
        self.assertEqual(len(items), 10)
        self.assertEqual([item["key"] for item in items], [
            "flower_bouquet",
            "wine_bottle",
            "dildo",
            "anal_plug",
            "cute_pajamas",
            "engagement_ring",
            "bondage_rope",
            "lace_lingerie",
            "fox_ears_headband",
            "control_orb",
        ])


if __name__ == "__main__":
    unittest.main()
