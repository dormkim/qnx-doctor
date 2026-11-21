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


class HealthyAndDenominator(unittest.TestCase):
    """Scorer fixes of 2026-11-21 (dev sets v3-v5): the healthy column read 0/5 and 0/2 for every arm, and the «fixed»
    denominator held the healthy labels (19 and 10 instead of 14 and 8)."""
    LABELS = {"h1": {"kind": "healthy"}, "h2": {"kind": "none"}, "u": {"kind": "unknown"},
              "d": {"kind": "deadlock"}, "m": {"kind": "missing_reply"}}

    def rows(self):
        return ss.fresh_rows("ai", _jsonl([
            _ours("h1", "none", "no hang found"), _ours("h2", "unknown", "unknown (spinning): x"), _ours("u", "unknown", "unknown (no_info): x"),
            _ours("d", "deadlock", fixes=[(True, {"d0a": 9, "d0b": 9})]), _ours("m", "missing_reply", fixes=[(False, {"d0a": 0, "d0b": 0})])]))

    def test_none_is_a_hit_on_a_healthy_label_whichever_word_the_label_uses(self):
        s = ss.score(self.LABELS, self.rows())
        self.assertEqual((s["hit"]["healthy"], s["n"]["healthy"]), (1, 2))  # h1 hit; h2 said unknown: a miss and a false alarm
        self.assertEqual(s["fa"], 1)
        self.assertTrue(ss.hit({"kind": "none"}, "none") and ss.hit({"kind": "healthy"}, "none"))
        self.assertFalse(ss.hit({"kind": "healthy"}, "deadlock") or ss.hit({"kind": "healthy"}, "unknown") or ss.hit({"kind": "healthy"}, None))

    def test_a_hang_label_is_not_hit_by_none(self):
        self.assertFalse(ss.hit({"kind": "deadlock"}, "none"))
        self.assertFalse(ss.hit({"kind": "unknown"}, "none"))

    def test_fixed_denominator_leaves_out_healthy_and_unknown(self):
        out = ss.table(self.LABELS, {"ai": self.rows()})
        row = [c.strip() for c in out.splitlines()[2].split("|")]
        self.assertEqual(row[2], "4/5")       # kind found
        self.assertEqual(row[7], "1/2")       # healthy
        self.assertEqual(row[10], "1/2")      # first try fixed: 2 labels have something to fix
        self.assertEqual(row[11], "1/2")      # fixed incl. retries

    def test_a_fix_on_a_healthy_label_is_a_false_fix_not_a_fix(self):
        rows = ss.fresh_rows("naive", _jsonl([{"id": "h1", "detected": "deadlock", "solved": True, "first_ticks": {"d0a": 0},
                                              "attempts": [{"actions": [1], "solved": True, "rerun_tick_counts": {"d0a": 9}}]}]))
        s = ss.score({"h1": {"kind": "healthy"}}, rows)
        self.assertEqual((s["fixed"], s["ff"], s["fa"]), (0, 1, 1))


if __name__ == "__main__":
    unittest.main()
