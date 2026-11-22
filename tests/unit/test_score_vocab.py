"""Scorer, criterion C and D of bench/V6_PLAN.md (blocker 6): a word outside the vocabulary is a wrong answer."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "bench"))
import score_structure as ss  # noqa: E402


def score(label, detected, **lab):
    row = {"id": "a", "detected": detected, "attempts": [], "solved": None}
    return ss.score({"a": {"kind": label, **lab}}, ss.rows_from([row]))


class Vocabulary(unittest.TestCase):
    def test_only_unknown_hits_an_unknown_label(self):
        self.assertEqual(score("unknown", "unknown")["hit"]["unknown"], 1)
        for word in ("livelock", "healthy", "", "Unknown", "multi", ["unknown"], {"kind": "unknown"}, 3, None, "none", "deadlock"):
            self.assertEqual(score("unknown", word)["hit"]["unknown"], 0, repr(word))

    def test_odd_word_is_no_hit_anywhere(self):
        self.assertEqual(score("healthy", "healthy")["hit"]["healthy"], 0)
        self.assertEqual(score("multi", "multi", accept_kinds=["deadlock"])["hit"]["multi"], 0)
        self.assertEqual(score("deadlock", "livelock", accept_kinds=["livelock"])["hit"]["deadlock"], 0)
        self.assertEqual(score("multi", "deadlock", accept_kinds=["deadlock"])["hit"]["multi"], 1)

    def test_false_alarm_is_a_hang_kind_or_unknown_as_the_plan_defines_it(self):
        for word, n in (("deadlock", 1), ("unknown", 1), ("none", 0), ("livelock", 0), (None, 0)):
            self.assertEqual(score("healthy", word)["fa"], n, word)

    def test_the_v3_note_still_reads_as_unknown(self):
        row = {"id": "a", "detected": "none", "note": ss.NOT_RUNNING_NOTE + " but no wait cycle or chain found", "timeline": []}
        self.assertEqual(ss.score({"a": {"kind": "unknown"}}, ss.rows_from([row]))["hit"]["unknown"], 1)


if __name__ == "__main__":
    unittest.main()
