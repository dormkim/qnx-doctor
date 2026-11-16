"""score_structure: «first try fixed» is reported next to «fixed incl. retries» (red team 2026-11-16).
A fix that needed the second try counts in the second column only; old one-shot naive rows still score."""
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "bench"))
import score_structure as ss  # noqa: E402

LABELS = {"a": {"kind": "deadlock"}, "b": {"kind": "deadlock"}, "c": {"kind": "none"}}


def _jsonl(rows):
    f = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False)
    f.write("\n".join(json.dumps(r) for r in rows) + "\n"); f.close()
    return f.name


class FirstTry(unittest.TestCase):
    def test_ours_second_try_counts_only_with_retries(self):
        p = _jsonl([
            {"id": "a", "detected": "deadlock", "solved": True, "by": "ai",
             "timeline": [{"kind": "ai_fix", "result": "SOLVED (rerun ...)", "live": True}]},
            {"id": "b", "detected": "deadlock", "solved": True, "by": "ai",
             "timeline": [{"kind": "ai_fix", "result": "still hung: ...", "live": False},
                          {"kind": "ai_fix", "result": "SOLVED (rerun ...)", "live": True}]},
            {"id": "c", "detected": "none", "solved": None, "by": "code", "timeline": []}])
        s = ss.score(LABELS, ss.fresh_rows("ai", p))
        self.assertEqual((s["first"], s["fixed"]), (1, 2))
        self.assertIn("| 1/2 | 2/2 |", ss.table(LABELS, {"ai": ss.fresh_rows("ai", p)}))

    def test_naive_retry_arm_and_old_rows(self):
        new = _jsonl([
            {"id": "a", "detected": "deadlock", "solved": True, "attempts": [{"solved": False, "live": False}, {"solved": True}]},
            {"id": "b", "detected": "deadlock", "solved": True, "attempts": [{"solved": True}]},
            {"id": "c", "detected": "none", "solved": None, "attempts": []}])
        old = _jsonl([
            {"id": "a", "detected": "deadlock", "solved": True, "actions": [{"type": "edit_file"}], "live": True},
            {"id": "b", "detected": "deadlock", "solved": False, "actions": [{"type": "edit_file"}], "live": False},
            {"id": "c", "detected": "none", "solved": None, "actions": []}])
        s2 = ss.score(LABELS, ss.fresh_rows("naive_x2", new))
        s1 = ss.score(LABELS, ss.fresh_rows("naive", old))
        self.assertEqual((s2["first"], s2["fixed"]), (1, 2))
        self.assertEqual((s1["first"], s1["fixed"]), (1, 1))


if __name__ == "__main__":
    unittest.main()
