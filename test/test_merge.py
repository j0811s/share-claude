"""settings.json のマージポリシーの検証。"""
import unittest

from deployer.merge import merge_settings


class MergeSettingsTest(unittest.TestCase):
    def test_permissions_allow_is_concatenated_base_first(self):
        base = {"permissions": {"allow": ["Bash(git status)", "Bash(git diff)"]}}
        overlay = {"permissions": {"allow": ["Bash(npm test)"]}}
        merged = merge_settings(base, overlay)
        self.assertEqual(
            merged["permissions"]["allow"],
            ["Bash(git status)", "Bash(git diff)", "Bash(npm test)"],
        )

    def test_permissions_allow_duplicates_are_removed_keeping_order(self):
        base = {"permissions": {"allow": ["a", "b"]}}
        overlay = {"permissions": {"allow": ["b", "c"]}}
        merged = merge_settings(base, overlay)
        self.assertEqual(merged["permissions"]["allow"], ["a", "b", "c"])

    def test_hooks_are_concatenated_with_base_entries_first(self):
        base = {"hooks": {"SessionStart": [{"matcher": "*", "hooks": [{"type": "command", "command": "base.sh"}]}]}}
        overlay = {"hooks": {"SessionStart": [{"matcher": "*", "hooks": [{"type": "command", "command": "project.sh"}]}]}}
        merged = merge_settings(base, overlay)
        commands = [entry["hooks"][0]["command"] for entry in merged["hooks"]["SessionStart"]]
        self.assertEqual(commands, ["base.sh", "project.sh"])

    def test_identical_hook_entries_are_deduplicated(self):
        entry = {"matcher": "*", "hooks": [{"type": "command", "command": "same.sh"}]}
        merged = merge_settings({"hooks": {"SessionStart": [entry]}}, {"hooks": {"SessionStart": [dict(entry)]}})
        self.assertEqual(len(merged["hooks"]["SessionStart"]), 1)

    def test_nested_dict_is_merged_recursively_with_overlay_winning(self):
        base = {"enabledPlugins": {"a@x": True, "b@x": False}}
        overlay = {"enabledPlugins": {"b@x": True, "c@x": True}}
        merged = merge_settings(base, overlay)
        self.assertEqual(merged["enabledPlugins"], {"a@x": True, "b@x": True, "c@x": True})

    def test_scalar_is_overridden_by_overlay(self):
        merged = merge_settings({"model": "sonnet"}, {"model": "opus"})
        self.assertEqual(merged["model"], "opus")

    def test_unknown_list_is_replaced_by_overlay(self):
        merged = merge_settings({"somethingNew": [1, 2, 3]}, {"somethingNew": [9]})
        self.assertEqual(merged["somethingNew"], [9])

    def test_key_present_only_in_base_survives(self):
        merged = merge_settings({"statusLine": {"type": "command"}}, {"model": "opus"})
        self.assertEqual(merged["statusLine"], {"type": "command"})

    def test_key_present_only_in_overlay_is_added(self):
        merged = merge_settings({"model": "opus"}, {"tui": "fullscreen"})
        self.assertEqual(merged["tui"], "fullscreen")

    def test_empty_side_returns_the_other_side(self):
        self.assertEqual(merge_settings({}, {"a": 1}), {"a": 1})
        self.assertEqual(merge_settings({"a": 1}, {}), {"a": 1})

    def test_type_mismatch_lets_overlay_win(self):
        merged = merge_settings({"x": {"nested": 1}}, {"x": [1, 2]})
        self.assertEqual(merged["x"], [1, 2])

    def test_inputs_are_not_mutated(self):
        base = {"permissions": {"allow": ["a"]}}
        overlay = {"permissions": {"allow": ["b"]}}
        merge_settings(base, overlay)
        self.assertEqual(base, {"permissions": {"allow": ["a"]}})
        self.assertEqual(overlay, {"permissions": {"allow": ["b"]}})


if __name__ == "__main__":
    unittest.main()
