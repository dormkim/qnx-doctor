"""Judge attacks on «fixed»: fake fixes that a looser check would accept (backlog ①, 2026-11-16, before held-out).

first = the hung observation, res = the rerun after a fix. Only states are used (no times)."""
import os
import tempfile
import unittest

from qnx_doctor.hang import checked_claims
from qnx_doctor.hangdoctor import NOT_ALIVE, not_restarted, restarted, result_text, verdict

FIRST = {"ticks": {"d0cli": 0, "d0wait": 0, "d0decoy": 7}, "alive": 4}


def rerun(kind="none", ticks=None, alive=4, ok=True):
    return {"ok": ok, "judge": {"kind": kind}, "ticks": ticks if ticks is not None else {"d0cli": 9, "d0wait": 9, "d0decoy": 7},
            "alive": alive}


class FakeFixes(unittest.TestCase):
    def test_real_fix_counts(self):
        self.assertTrue(restarted(FIRST, rerun()))

    def test_prints_one_tick_then_exits(self):
        self.assertFalse(restarted(FIRST, rerun(ticks={"d0cli": 1, "d0wait": 1, "d0decoy": 7})))

    def test_a_loop_that_was_ticking_stops(self):
        self.assertFalse(restarted(FIRST, rerun(ticks={"d0cli": 9, "d0wait": 9, "d0decoy": 0})))

    def test_roles_that_never_tick_may_stay_at_zero(self):  # sealed D03: server and logger log but never TICK
        first = {"ticks": {"d03cli": 0, "d03srv": 0, "d03log": 0}, "alive": 3}
        self.assertTrue(restarted(first, rerun(ticks={"d03cli": 9, "d03srv": 0, "d03log": 0}, alive=3)))

    def test_a_peer_quits_so_nobody_waits(self):  # no cycle left because a member is gone
        self.assertFalse(restarted(FIRST, rerun(alive=3)))

    def test_cycle_still_there(self):
        self.assertFalse(restarted(FIRST, rerun(kind="deadlock")))

    def test_chain_still_there(self):
        self.assertFalse(restarted(FIRST, rerun(kind="priority_chain")))

    def test_rerun_failed_to_build_or_boot(self):
        self.assertFalse(restarted(FIRST, {"ok": False, "stage": "build"}))

    def test_role_log_missing_in_rerun(self):  # the fix stopped the role from logging at all
        self.assertFalse(restarted(FIRST, rerun(ticks={"d0decoy": 7})))

    def test_nothing_was_stopped(self):  # a healthy system cannot be «fixed»
        self.assertFalse(restarted({"ticks": {"d0a": 5}, "alive": 2}, rerun(ticks={"d0a": 9}, alive=2)))


def first_of(ticks, progress, alive):
    return {"ticks": ticks, "progress": progress, "alive": alive}


# Shapes of the dev-set records that the «printed no TICK at all» rule could never pass (2026-11-21). Numbers are TICK
# counts from the recorded runs (v4 D03, v5 E05/E08), used as states: stopped or ticking, more than before or not.
RING3 = first_of({"d0a": 1, "d0b": 1, "d0c": 1}, {"d0a": "flat", "d0b": "flat", "d0c": "flat"}, 3)
LATE_STOP = first_of({"d0a": 3, "d0b": 4}, {"d0a": "flat", "d0b": "flat"}, 2)
GROWS = {"d0a": "grew", "d0b": "grew", "d0c": "grew"}


def rerun2(ticks, progress=None, alive=3, kind="none", graph="no wait cycle and no priority chain"):
    return {"ok": True, "judge": {"kind": kind}, "graph": graph, "ticks": ticks, "progress": progress, "alive": alive}


class StoppedAfterTicking(unittest.TestCase):
    """Every role printed a TICK before the hang: «stopped» comes from progress, not from a 0 count."""

    def test_ring_that_ticked_once_then_runs(self):
        self.assertTrue(restarted(RING3, rerun2({"d0a": 212493, "d0b": 212494, "d0c": 212493}, GROWS)))

    def test_server_that_stopped_after_a_few_rounds_then_runs(self):
        self.assertTrue(restarted(LATE_STOP, rerun2({"d0a": 34, "d0b": 34}, {"d0a": "grew", "d0b": "grew"}, alive=2)))

    def test_recorded_rerun_without_second_count_uses_the_counts(self):  # older recordings: no rerun progress
        self.assertTrue(restarted(RING3, rerun2({"d0a": 212493, "d0b": 212494, "d0c": 212493}, None)))

    def test_fake_same_single_tick_again(self):  # prints its one TICK on the way in and stops as before
        why = not_restarted(RING3, rerun2({"d0a": 1, "d0b": 1, "d0c": 1}, {"d0a": "flat", "d0b": "flat", "d0c": "flat"}))
        self.assertTrue(why.startswith(NOT_ALIVE))
        self.assertIn("d0a 1 -> 1", why)

    def test_fake_one_more_tick_is_not_a_loop(self):
        self.assertFalse(restarted(RING3, rerun2({"d0a": 2, "d0b": 2, "d0c": 2}, None)))
        self.assertFalse(restarted(LATE_STOP, rerun2({"d0a": 4, "d0b": 5}, None, alive=2)))

    def test_fake_prints_more_then_stops_again(self):  # the count passed, the second count of the rerun did not grow
        why = not_restarted(LATE_STOP, rerun2({"d0a": 9, "d0b": 9}, {"d0a": "flat", "d0b": "flat"}, alive=2))
        self.assertIn("not ticking any more at the second count", why)

    def test_fake_loop_deleted_so_nothing_is_logged(self):
        self.assertFalse(restarted(RING3, rerun2({}, {})))
        self.assertFalse(restarted(RING3, rerun2({"d0a": 0, "d0b": 0, "d0c": 0}, {"d0a": "idle", "d0b": "idle", "d0c": "idle"})))

    def test_fake_one_member_quits(self):
        why = not_restarted(RING3, rerun2({"d0a": 500, "d0b": 500, "d0c": 1}, GROWS, alive=2))
        self.assertIn("a program process is gone (3 -> 2", why)

    def test_fake_one_loop_runs_another_goes_silent(self):
        why = not_restarted(RING3, rerun2({"d0a": 500, "d0b": 500, "d0c": 0}, {"d0a": "grew", "d0b": "grew", "d0c": "idle"}))
        self.assertIn("prints none in the rerun (d0c)", why)

    def test_cycle_still_there_even_with_more_ticks(self):
        why = not_restarted(RING3, rerun2({"d0a": 50, "d0b": 50, "d0c": 50}, GROWS, kind="deadlock", graph="DEADLOCK: 5 -> 6 -> 5"))
        self.assertEqual(why, "still hung: DEADLOCK: 5 -> 6 -> 5")

    def test_healthy_first_run_cannot_be_fixed(self):  # every loop was growing: nothing was stopped
        first = first_of({"d0a": 27, "d0b": 27}, {"d0a": "grew", "d0b": "grew"}, 2)
        why = not_restarted(first, rerun2({"d0a": 900, "d0b": 900}, {"d0a": "grew", "d0b": "grew"}, alive=2))
        self.assertIn("no loop was stopped", why)

    def test_a_loop_that_kept_ticking_is_not_the_proof(self):  # partial stop: the witness must be a stopped role
        first = first_of({"d0live": 30, "d0stuck": 2}, {"d0live": "grew", "d0stuck": "flat"}, 2)
        self.assertFalse(restarted(first, rerun2({"d0live": 900, "d0stuck": 2}, {"d0live": "grew", "d0stuck": "flat"}, alive=2)))
        self.assertTrue(restarted(first, rerun2({"d0live": 900, "d0stuck": 40}, {"d0live": "grew", "d0stuck": "grew"}, alive=2)))

    def test_zero_tick_roles_judged_as_before(self):  # idle = the old «printed no TICK»
        first = first_of({"d0cli": 0, "d0decoy": 7}, {"d0cli": "idle", "d0decoy": "grew"}, 2)
        self.assertTrue(restarted(first, rerun2({"d0cli": 9, "d0decoy": 9}, {"d0cli": "grew", "d0decoy": "grew"}, alive=2)))
        self.assertFalse(restarted(first, rerun2({"d0cli": 1, "d0decoy": 9}, {"d0cli": "flat", "d0decoy": "grew"}, alive=2)))


class FailureText(unittest.TestCase):
    """The text a failed try gets back names the condition that failed (v5 E08: «still hung: no wait cycle and no
    priority chain» made the AI repeat the same edit)."""

    def test_no_cycle_but_not_alive_is_not_called_still_hung(self):
        v = verdict(RING3, rerun2({"d0a": 1, "d0b": 1, "d0c": 1}, None))
        self.assertFalse(v["fixed"])
        self.assertTrue(result_text(v).startswith(NOT_ALIVE))
        self.assertNotIn("still hung", result_text(v))

    def test_still_hung_keeps_the_graph(self):
        v = verdict(RING3, rerun2({"d0a": 1, "d0b": 1, "d0c": 1}, None, kind="deadlock", graph="DEADLOCK: 5 -> 6 -> 5"))
        self.assertEqual(result_text(v), "still hung: DEADLOCK: 5 -> 6 -> 5")

    def test_rerun_did_not_build(self):
        v = verdict(RING3, {"ok": False, "stage": "build", "log": "qcc a.c failed"})
        self.assertEqual(result_text(v), "rerun did not finish: build failed")  # no compiler text since 2026-11-22

    def test_baseline_feedback_has_the_condition_but_never_the_graph(self):
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "bench"))
        import naive_hang as nh
        res = rerun2({"d0a": 1, "d0b": 1, "d0c": 1}, None, kind="deadlock", graph="DEADLOCK: 5(a) -> 6(b) -> 5")
        fb = nh._feedback(res, verdict(RING3, res), None)
        self.assertNotIn("DEADLOCK", fb)
        self.assertIn("still hung", fb)
        res = rerun2({"d0a": 1, "d0b": 1, "d0c": 1}, None)
        self.assertIn(NOT_ALIVE, nh._feedback(res, verdict(RING3, res), None))


class Claims(unittest.TestCase):
    def setUp(self):
        self.work = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.work, "s1"))
        open(os.path.join(self.work, "s1", "a.c"), "w").write("  int ch = ChannelCreate(_NTO_CHF_FIXED_PRIORITY);\n")

    def claim(self, **kw):
        return checked_claims(self.work, kw)

    def test_label_outside_the_vocabulary(self):
        self.assertEqual(self.claim(cause_label="mutex_deadlock")["cause_label"], "unlisted")

    def test_culprit_line_must_be_in_the_file(self):
        good = {"file": "s1/a.c", "line": "int ch = ChannelCreate(_NTO_CHF_FIXED_PRIORITY);"}
        self.assertTrue(self.claim(cause_label="fixed_priority_channel", culprit=good)["culprit_in_source"])
        self.assertFalse(self.claim(culprit={"file": "s1/a.c", "line": "MsgSend(coid, 0);"})["culprit_in_source"])
        self.assertFalse(self.claim(culprit={"file": "../labels.json", "line": "kind"})["culprit_in_source"])
        self.assertFalse(self.claim(culprit={"file": "s1/a.c", "line": "  "})["culprit_in_source"])


if __name__ == "__main__":
    unittest.main()
