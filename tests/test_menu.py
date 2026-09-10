import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from menu import (
    ALL_SUB_ACTIONS,
    CANONICAL_PIPELINE_ORDER,
    MENU_ITEMS,
    get_execution_plan,
    toggle_item,
)


class MenuLogicTests(unittest.TestCase):
    def test_toggle_all_selects_all_sub_actions(self):
        selected = set()
        toggle_item(selected, "all")
        self.assertIn("all", selected)
        for sub in ALL_SUB_ACTIONS:
            self.assertIn(sub, selected)

    def test_toggle_all_deselects_all_sub_actions(self):
        selected = set(["all"] + ALL_SUB_ACTIONS)
        toggle_item(selected, "all")
        self.assertNotIn("all", selected)
        for sub in ALL_SUB_ACTIONS:
            self.assertNotIn(sub, selected)

    def test_unchecking_one_sub_action_unchecks_all(self):
        selected = set(["all"] + ALL_SUB_ACTIONS)
        toggle_item(selected, "translate")
        self.assertNotIn("translate", selected)
        self.assertNotIn("all", selected)
        # Other sub-actions remain selected
        self.assertIn("sync", selected)
        self.assertIn("align", selected)
        self.assertIn("validate", selected)
        self.assertIn("export", selected)
        self.assertIn("build", selected)
        self.assertIn("dist", selected)
        self.assertIn("check", selected)
        self.assertIn("test", selected)

    def test_checking_all_sub_actions_automatically_checks_all(self):
        selected = set()
        for sub in ALL_SUB_ACTIONS[:-1]:
            toggle_item(selected, sub)
            self.assertNotIn("all", selected)

        # Toggle the last sub-action
        toggle_item(selected, ALL_SUB_ACTIONS[-1])
        self.assertIn("all", selected)

    def test_deploy_and_clear_are_independent_from_all(self):
        # 1. Toggling deploy does not affect all
        selected = set()
        toggle_item(selected, "deploy")
        self.assertIn("deploy", selected)
        self.assertNotIn("all", selected)

        # 2. Toggling all does not affect deploy or clear
        toggle_item(selected, "all")
        self.assertIn("all", selected)
        self.assertIn("deploy", selected)
        self.assertNotIn("clear", selected)

        # 3. Untoggling all does not remove deploy
        toggle_item(selected, "all")
        self.assertNotIn("all", selected)
        self.assertIn("deploy", selected)

    def test_menu_items_indentation(self):
        item_map = {item.key: item for item in MENU_ITEMS}
        self.assertFalse(item_map["all"].indent)
        self.assertFalse(item_map["deploy"].indent)
        self.assertFalse(item_map["clear"].indent)

        for sub in ALL_SUB_ACTIONS:
            self.assertTrue(item_map[sub].indent, f"Expected {sub} to have indent=True")

    def test_canonical_pipeline_order(self):
        # Add actions in random / reverse order
        selected = set(["dist", "sync", "build", "validate", "align", "deploy", "clear"])
        plan = get_execution_plan(selected)
        expected = ["clear", "sync", "align", "validate", "build", "dist", "deploy"]
        self.assertEqual(plan, expected)

    def test_all_meta_key_not_in_execution_plan(self):
        selected = set(["all", "sync", "build"])
        plan = get_execution_plan(selected)
        self.assertNotIn("all", plan)
        self.assertEqual(plan, ["sync", "build"])

    def test_menu_items_have_valid_keys(self):
        item_keys = [item.key for item in MENU_ITEMS]
        for sub in ALL_SUB_ACTIONS:
            self.assertIn(sub, item_keys)
        self.assertIn("all", item_keys)
        self.assertIn("deploy", item_keys)
        self.assertIn("clear", item_keys)


if __name__ == "__main__":
    unittest.main()
