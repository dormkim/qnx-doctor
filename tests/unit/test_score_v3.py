"""score_structure sealed-v3 rules (bench/sealed_v3_1117/README.md, fixed before its single run): «unknown» label,
accept_kinds, «fixed on unknown» kept apart from fixed/false fix, loop_logs «every stopped loop ticks again», exclusions."""
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "bench"))
import score_structure as ss  # noqa: E402


def _jsonl(rows):
    f = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False)
    f.write("\n".join(json.dumps(r) for r in rows) + "\n"); f.close()
    return f.name


def _ours(sid, detected, note=None, fixes=()):
    tl = [{"kind": "graph", "ticks": {"d0a": 0, "d0b": 0}}] + [
        {"kind": "ai_fix", "result": "SOLVED (rerun ...)" if ok else "still hung", "live": ok, "rerun_tick_counts": t} for ok, t in fixes]
    return {"id": sid, "detected": detected, "note": note, "solved": True if any(ok for ok, _ in fixes) else (None if detected == "none" else False),
            "by": "ai" if fixes else "code", "timeline": tl}


NOT_RUNNING = "loop not running but no wait cycle or chain found"


class Unknown(unittest.TestCase):
    def test_hit_rules(self):
        u = {"kind": "unknown"}
        self.assertTrue(ss.hit(u, "unknown"))
        for d in ("deadlock", "priority_chain", "missing_reply", "none", None):
            self.assertFalse(ss.hit(u, d))
        self.assertTrue(ss.hit({"kind": "deadlock", "accept_kinds": ["deadlock", "missing_reply"]}, "missing_reply"))
        self.assertFalse(ss.hit({"kind": "deadlock"}, "missing_reply"))

    def test_code_note_reads_as_unknown_healthy_does_not(self):
        rows = ss.fresh_rows("code", _jsonl([_ours("u", "none", NOT_RUNNING), _ours("h", "none", "no hang found")]))
        self.assertEqual((rows["u"]["detected"], rows["h"]["detected"]), ("unknown", "none"))
        self.assertEqual(rows["u"]["raw"], "none")

    def test_fix_on_unknown_has_own_column(self):
        labels = {"u": {"kind": "unknown", "info_insufficient": True}, "n": {"kind": "none"}, "d": {"kind": "deadlock"}}
        naive = ss.fresh_rows("naive", _jsonl([
            {"id": "u", "detected": "deadlock", "solved": True, "attempts": [{"solved": True, "rerun_tick_counts": {"d0a": 5, "d0b": 5}}]},
            {"id": "n", "detected": "none", "solved": None, "attempts": []},
            {"id": "d", "detected": "deadlock", "solved": False, "attempts": [{"solved": False}]}]))
        s = ss.score(labels, naive)
        self.assertEqual((s["fixed"], s["ff"], s["fu"], s["hit"]["unknown"]), (0, 0, 1, 0))
        t = ss.table(labels, {"naive": naive})
        self.assertIn("| 0/1 | 0/1 | 0/1 | 0/1 | 0 | 0/1 | 0 | 1 |", t)  # faults = 1 (unknown and none are not faults)
        self.assertIn("naive u", ss.details(labels, {"naive": naive}))


class LoopLogs(unittest.TestCase):
    def test_every_stopped_loop_must_tick(self):
        lab = {"d": {"kind": "deadlock", "loop_logs": ["d0a", "/tmp/d0b.log"]}}
        half = ss.fresh_rows("ai", _jsonl([_ours("d", "deadlock", fixes=[(True, {"d0a": 9, "d0b": 0})])]))
        both = ss.fresh_rows("ai", _jsonl([_ours("d", "deadlock", fixes=[(False, {"d0a": 0, "d0b": 0}), (True, {"d0a": 9, "d0b": 3})])]))
        s1, s2 = ss.score(lab, half), ss.score(lab, both)
        self.assertEqual((s1["fixed"], s1["first"], s1["loop_cut"]), (0, 0, 1))
        self.assertEqual((s2["fixed"], s2["first"]), (1, 0))

    def test_role_written_without_prefix_and_missing_role_reported(self):
        self.assertEqual(ss._tick({"d0probe": 3}, "probe"), 3)
        self.assertIsNone(ss._tick({"d0probe": 3}, "other"))
        lab = {"d": {"kind": "deadlock", "loop_logs": ["zz"]}}
        rows = ss.fresh_rows("ai", _jsonl([_ours("d", "deadlock", fixes=[(True, {"d0a": 9, "d0b": 9})])]))
        self.assertIn("d: zz", ss.details(lab, {"ai": rows}))

    def test_old_rows_without_rerun_ticks_keep_verifier_verdict(self):
        lab = {"d": {"kind": "deadlock", "loop_logs": ["d0a"]}}
        rows = ss.fresh_rows("naive", _jsonl([{"id": "d", "detected": "deadlock", "solved": True, "actions": [{"type": "edit_file"}], "live": True}]))
        self.assertEqual(ss.score(lab, rows)["fixed"], 1)


class Exclude(unittest.TestCase):
    def test_excluded_are_listed_not_scored(self):
        lp = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
        json.dump({"_note": "x", "a": {"kind": "deadlock"}, "b": {"kind": "none"}}, lp); lp.close()
        ep = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
        json.dump({"a": "loop kept ticking unmodified"}, ep); ep.close()
        rows = _jsonl([_ours("b", "none", "no hang found")])
        buf = io.StringIO()
        with redirect_stdout(buf):
            ss.main([lp.name, "--exclude-file", ep.name, "--fresh", f"code={rows}"])
        out = buf.getvalue()
        self.assertIn("Excluded (unmodified run did not match «expect»): 1", out)
        self.assertIn("- a: loop kept ticking unmodified", out)
        self.assertIn("| code | 1/1 |", out)


if __name__ == "__main__":
    unittest.main()
