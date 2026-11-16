"""Pure-function tests for the wait-for graph judge. Fixture pidin_dl2_1115.txt is a real QNX 8.0 capture
(two processes SEND-blocked on each other, feasibility run 2026-11-15); the rest are small synthetic tables."""
import os
import unittest

from qnx_doctor import waitgraph as wg

HERE = os.path.dirname(os.path.abspath(__file__))
HEAD = "     pid tid name                         prio STATE          Blocked\n"
KERNEL = "       1   9 /proc/boot/procnto-smp-instr  10r REPLY          1\n       1   1 /proc/boot/procnto-smp-instr   0f READY\n"


def table(*rows):
    return HEAD + KERNEL + "".join(f"{p:8d} {t:3d} {n:28s} {pr:>4s} {st:14s} {b}\n" for p, t, n, pr, st, b in rows)


class Parse(unittest.TestCase):
    def test_real_capture(self):
        th = wg.parse(open(os.path.join(HERE, "fixtures", "pidin_dl2_1115.txt")).read())
        dl = [t for t in th if t.name == "var/dl"]
        self.assertEqual([(t.pid, t.state, t.blocked, t.prio) for t in dl], [(180241, "SEND", 180242, 10), (180242, "SEND", 180241, 10)])

    def test_no_prio_column_and_blank_blocked(self):
        th = wg.parse("   1  9 procnto-smp-instr  REPLY  1\n  77 1 bin/sh 10r SIGSUSPEND\n")
        self.assertEqual(th[0].prio, None)
        self.assertEqual((th[1].state, th[1].blocked), ("SIGSUSPEND", None))


class Judge(unittest.TestCase):
    def test_real_two_way_deadlock(self):
        j = wg.judge(wg.parse(open(os.path.join(HERE, "fixtures", "pidin_dl2_1115.txt")).read()))
        self.assertEqual(j["kind"], "deadlock")
        self.assertEqual([[m["pid"] for m in c] for c in j["cycles"]], [[180241, 180242]])
        self.assertIn("DEADLOCK: 180241(var/dl, SEND-blocked on 180242) -> 180242", wg.describe(j))

    def test_three_ring_found_once(self):
        j = wg.judge(wg.parse(table((10, 1, "a", "10r", "SEND", 11), (11, 1, "b", "10r", "SEND", 12), (12, 1, "c", "10r", "SEND", 10))))
        self.assertEqual([[m["pid"] for m in c] for c in j["cycles"]], [[10, 11, 12]])

    def test_reply_chain_behind_cycle(self):
        j = wg.judge(wg.parse(table((20, 1, "client", "10r", "REPLY", 21), (21, 1, "server", "10r", "SEND", 22),
                                    (22, 1, "logger", "10r", "SEND", 21))))
        self.assertEqual([[m["pid"] for m in c] for c in j["cycles"]], [[21, 22]])
        self.assertEqual([b["pid"] for b in j["behind"]], [20])

    def test_callback_cycle_reply_and_send(self):
        j = wg.judge(wg.parse(table((30, 1, "client", "10r", "REPLY", 31), (31, 1, "server", "10r", "SEND", 30))))
        self.assertEqual(j["kind"], "deadlock")

    def test_kernel_waits_are_not_edges(self):
        self.assertEqual(wg.judge(wg.parse(table((40, 1, "x", "10r", "REPLY", 1)))), {"kind": "none"})

    def test_priority_inversion_with_middle_thread_ready(self):  # observer holds the CPUs at the snapshot (dev 1014)
        j = wg.judge(wg.parse(table((50, 1, "ctl", "33r", "REPLY", 51), (51, 1, "srv", "6r", "READY", ""),
                                    (52, 2, "hog", "21r", "READY", ""), (52, 3, "hog", "21r", "READY", ""))))
        self.assertEqual(j["kind"], "priority_chain")

    def test_no_inversion_when_middle_thread_is_blocked(self):
        self.assertEqual(wg.judge(wg.parse(table((50, 1, "ctl", "33r", "REPLY", 51), (51, 1, "srv", "6r", "READY", ""),
                                                 (52, 1, "hog", "21r", "NANOSLEEP", ""))))["kind"], "none")

    def test_priority_inversion(self):
        j = wg.judge(wg.parse(table((50, 1, "ctl", "30r", "REPLY", 51), (51, 1, "srv", "5r", "READY", ""),
                                    (52, 1, "hog", "20r", "RUNNING", ""), (53, 1, "pidin", "63r", "RUNNING", ""))))
        self.assertEqual(j["kind"], "priority_chain")
        c = j["chains"][0]
        self.assertEqual((c["waiter"]["pid"], c["server"]["pid"], [r[0] for r in c["running"]]), (50, 51, [52]))

    def test_inherited_priority_is_healthy(self):
        # with priority inheritance the server runs at the client's priority: not a chain
        self.assertEqual(wg.judge(wg.parse(table((50, 1, "ctl", "30r", "REPLY", 51), (51, 1, "srv", "30r", "READY", ""),
                                                 (52, 1, "hog", "20r", "RUNNING", ""))))["kind"], "none")

    def test_slow_server_is_not_a_hang(self):
        self.assertEqual(wg.judge(wg.parse(table((60, 1, "cli", "10r", "REPLY", 61), (61, 1, "srv", "10r", "NANOSLEEP", ""))))["kind"], "none")

    def test_idle_receive_is_not_a_hang(self):
        self.assertEqual(wg.judge(wg.parse(table((70, 1, "w1", "10r", "RECEIVE", 1), (71, 1, "w2", "10r", "RECEIVE", 1),
                                                 (72, 1, "feed", "10r", "NANOSLEEP", ""))))["kind"], "none")

    def test_focus_filters(self):
        th = wg.parse(table((10, 1, "a", "10r", "SEND", 11), (11, 1, "b", "10r", "SEND", 10), (80, 1, "other", "10r", "RUNNING", "")))
        self.assertEqual(wg.judge(th, focus="other")["kind"], "none")
        self.assertEqual(wg.judge(th, focus="11")["kind"], "deadlock")
        self.assertEqual(wg.judge(th, focus="a")["kind"], "deadlock")


class Check(unittest.TestCase):
    def test_split(self):
        out = "x\n=== PIDIN ===\n" + table((1, 1, "a", "10r", "RUNNING", "")) + "=== TICKS ===\n/tmp/d01a.log 0\n/tmp/d01b.log 12\nQDDONE\n"
        pid, ticks = wg.split_check(out)
        self.assertIn("RUNNING", pid)
        self.assertEqual(ticks, {"d01a": 0, "d01b": 12})


if __name__ == "__main__":
    unittest.main()
