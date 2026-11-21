"""The baseline's optional fifth answer «unknown» (bench/naive_hang.py --allow-unknown, for sealed v6). No model is
called here: the prompt text, the reply reader and the «no rerun, no fix» path are pure."""
import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "bench"))
import naive_hang as nh  # noqa: E402
import score_structure as ss  # noqa: E402


class Prompt(unittest.TestCase):
    def test_default_prompt_is_the_recorded_one(self):  # runs up to v5 stay reproducible
        self.assertIs(nh.system_prompt(), nh.NAIVE_SYSTEM)
        self.assertNotIn("unknown", nh.NAIVE_SYSTEM)
        self.assertEqual(nh.kinds(), ("deadlock", "priority_chain", "missing_reply", "none"))

    def test_unknown_is_added_to_the_kind_list_and_explained(self):
        p = nh.system_prompt(True)
        self.assertIn('"missing_reply" | "none" | "unknown", "roles"', p)
        self.assertIn("unknown = a loop that should run has stopped", p)
        self.assertIn("For none and unknown give no actions.", p)
        self.assertNotIn("For none give no actions.", p)
        self.assertEqual(nh.kinds(True)[-1], "unknown")

    def test_nothing_else_changes(self):
        a, b = nh.system_prompt(False), nh.system_prompt(True)
        b = b.replace(nh.UNKNOWN_KIND, "", 1).replace(nh.UNKNOWN_TEXT, ". For none give no actions.", 1)
        self.assertEqual(a, b)

    def test_no_pidin_or_graph_is_promised(self):  # the baseline still gets sources and TICK counts only
        self.assertIn("You have no other tools or observations", nh.system_prompt(True))


class Reply(unittest.TestCase):
    def test_unknown_is_a_wrong_word_without_the_flag(self):
        r = nh.read_reply('{"kind": "unknown", "roles": [], "cause": "spins"}')
        self.assertIn("kind not in", r["error"])

    def test_unknown_is_read_with_the_flag(self):
        r = nh.read_reply('{"kind": "unknown", "roles": [], "cause": "spins"}', nh.kinds(True))
        self.assertEqual((r["kind"], r.get("error")), ("unknown", None))

    def test_unreadable_reply_is_a_wrong_answer(self):
        self.assertEqual(nh.read_reply("I think it is fine.", nh.kinds(True))["kind"], None)


class NoFixOnUnknown(unittest.TestCase):
    def setUp(self):
        self.pool = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.pool, "u1"))
        open(os.path.join(self.pool, "u1", "a.c"), "w").write("int main(void){for(;;);}\n")
        open(os.path.join(self.pool, "u1", "run.sh"), "w").write("/var/qd/u1/a &\n")

    def tearDown(self):
        shutil.rmtree(self.pool, ignore_errors=True)

    def test_unknown_ends_the_case_without_a_rerun(self):
        calls = []

        def fake(context, allow_unknown):
            calls.append(allow_unknown)
            return {"kind": "unknown", "cause": "busy loop, no message passing",
                    "actions": [{"type": "edit_file", "path": "u1/a.c", "find": "for(;;);", "replace": ""}]}
        row = nh.one(self.pool, "u1", {"d0a": 3}, 1, attempts=2, allow_unknown=True, ask=fake)
        self.assertEqual(calls, [True])  # one question, no retry
        self.assertEqual((row["detected"], row["solved"], row["attempts"]), ("unknown", None, []))
        self.assertEqual(row["vocabulary"][-1], "unknown")

    def test_scored_like_ours(self):  # hit on an «unknown» label, false alarm on a healthy one, never a fix
        f = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False)
        for sid in ("u", "h"):
            f.write(json.dumps({"id": sid, "mode": "naive", "detected": "unknown", "solved": None, "attempts": [], "first_ticks": {"d0a": 3}}) + "\n")
        f.close()
        s = ss.score({"u": {"kind": "unknown"}, "h": {"kind": "healthy"}}, ss.fresh_rows("naive", f.name))
        os.unlink(f.name)
        self.assertEqual((s["hit"]["unknown"], s["hit"]["healthy"], s["fa"], s["fixed"], s["fu"]), (1, 0, 1, 0, 0))


if __name__ == "__main__":
    unittest.main()
