"""Judge attacks on «fixed»: fake fixes that a looser check would accept (backlog ①, 2026-11-16, before held-out).

first = the hung observation, res = the rerun after a fix. Only states are used (no times)."""
import os
import tempfile
import unittest

from qnx_doctor.hang import checked_claims
from qnx_doctor.hangdoctor import restarted

FIRST = {"ticks": {"d0cli": 0, "d0wait": 0, "d0decoy": 7}, "alive": 4}


def rerun(kind="none", ticks=None, alive=4, ok=True):
    return {"ok": ok, "judge": {"kind": kind}, "ticks": ticks if ticks is not None else {"d0cli": 9, "d0wait": 9, "d0decoy": 7},
            "alive": alive}


class FakeFixes(unittest.TestCase):
    def test_real_fix_counts(self):
        self.assertTrue(restarted(FIRST, rerun()))

    def test_prints_one_tick_then_exits(self):
        self.assertFalse(restarted(FIRST, rerun(ticks={"d0cli": 1, "d0wait": 1, "d0decoy": 7})))

    def test_only_one_of_the_stopped_loops_resumes(self):
        self.assertFalse(restarted(FIRST, rerun(ticks={"d0cli": 9, "d0wait": 0, "d0decoy": 7})))

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
