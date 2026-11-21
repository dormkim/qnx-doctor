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


class MissingReply(unittest.TestCase):
    """2026-11-17: REPLY-blocked on an application process whose threads all wait in RECEIVE = a forgotten MsgReply."""

    def test_idle_server_holding_a_reply(self):
        j = wg.judge(wg.parse(table((20, 1, "var/qd/t/cl", "10r", "REPLY", 21), (21, 1, "var/qd/t/srv", "10r", "RECEIVE", 1))))
        self.assertEqual(j["kind"], "missing_reply")
        self.assertIn("MISSING REPLY: 20(var/qd/t/cl) REPLY-blocked on 21(var/qd/t/srv)", wg.describe(j))

    def test_server_still_working_is_not_missing(self):
        th = table((20, 1, "var/qd/t/cl", "10r", "REPLY", 21), (21, 1, "var/qd/t/srv", "10r", "RECEIVE", 1),
                   (21, 2, "var/qd/t/srv", "10r", "CONDVAR", ""))
        self.assertEqual(wg.judge(wg.parse(th))["kind"], "none")

    def test_send_blocked_is_not_missing(self):
        th = table((20, 1, "var/qd/t/cl", "10r", "SEND", 21), (21, 1, "var/qd/t/srv", "10r", "RECEIVE", 1))
        self.assertEqual(wg.judge(wg.parse(th))["kind"], "none")

    def test_resource_manager_holding_a_read_is_normal(self):
        th = table((20, 1, "var/qd/t/cl", "10r", "REPLY", 30), (30, 1, "proc/boot/devc-ser8250", "24r", "RECEIVE", 1))
        self.assertEqual(wg.judge(wg.parse(th))["kind"], "none")


class Persistence(unittest.TestCase):
    """2026-11-17: a chain seen in one snapshot only (a passing state) is not a chain."""
    CHAIN = ((40, 1, "var/qd/t/cli", "30r", "REPLY", 41), (41, 1, "var/qd/t/srv", "5r", "READY", ""),
             (42, 1, "var/qd/t/mem", "10r", "READY", ""))
    LATER = ((40, 1, "var/qd/t/cli", "30r", "REPLY", 41), (41, 1, "var/qd/t/srv", "5r", "RUNNING", ""),
             (42, 1, "var/qd/t/mem", "10r", "RECEIVE", 1))

    def test_single_snapshot_still_judged(self):
        self.assertEqual(wg.judge(wg.parse(table(*self.CHAIN)))["kind"], "priority_chain")

    def test_passing_chain_dropped(self):
        j = wg.judge(wg.parse(table(*self.CHAIN)), later=[wg.parse(table(*self.CHAIN)), wg.parse(table(*self.LATER))])
        self.assertEqual(j["kind"], "none")

    def test_persistent_chain_kept(self):
        j = wg.judge(wg.parse(table(*self.CHAIN)), later=[wg.parse(table(*self.CHAIN))] * 2)
        self.assertEqual(j["kind"], "priority_chain")


# pidin lines as recorded in the dev-set runs (v4 D02, D10, D22: bench/sealed_v4_1117/scored_1118/code.jsonl, the
# «lines» of the graph entry). Kept as text fixtures for the parser; what QNX means by each column is not asserted.
D10 = """  204820   1 var/qd/D10/abba               10r JOIN           2
  204820   2 var/qd/D10/abba               10r MUTEX          (0x3f08248038) 204820-03 #0
  204820   3 var/qd/D10/abba               10r MUTEX          (0x3f08248030) 204820-02 #0
"""
D02 = """  204820   1 var/qd/D02/prio_none          40r JOIN           4
  204820   2 var/qd/D02/prio_none          10f READY
  204820   3 var/qd/D02/prio_none          20f READY
  204820   4 var/qd/D02/prio_none          30f MUTEX          (0x30afe0d030) 204820-02 #0
"""
D22 = "  204820   1 var/qd/D22/selfsend           10r SEND           204820\n"


class NonMessageWaits(unittest.TestCase):
    """2026-11-21: a Blocked column of several tokens is kept (any_blocked parse) and shown, not interpreted."""

    def test_mutex_lines_are_kept_with_the_column_as_printed(self):
        th = wg.parse(D10, any_blocked=True)
        self.assertEqual([(t.tid, t.state, t.blocked, t.detail) for t in th],
                         [(1, "JOIN", 2, "2"), (2, "MUTEX", None, "(0x3f08248038) 204820-03 #0"),
                          (3, "MUTEX", None, "(0x3f08248030) 204820-02 #0")])

    def test_priority_30_thread_is_no_longer_missing(self):
        th = wg.parse(D02, any_blocked=True)
        self.assertEqual([(t.tid, t.prio, t.state) for t in th], [(1, 40, "JOIN"), (2, 10, "READY"), (3, 20, "READY"), (4, 30, "MUTEX")])
        self.assertEqual(th[3].detail, "(0x30afe0d030) 204820-02 #0")

    def test_one_token_columns_parse_as_before(self):
        th = wg.parse("  7 1 var/qd/x/a 10r CONDVAR (0x518de30a4c)\n  7 2 var/qd/x/a 10r SEM 518de4f0d8\n  7 3 var/qd/x/a 10r READY\n", any_blocked=True)
        self.assertEqual([(t.state, t.blocked, t.detail) for t in th], [("CONDVAR", None, "(0x518de30a4c)"), ("SEM", None, "518de4f0d8"), ("READY", None, None)])

    def test_the_judge_parse_is_unchanged(self):  # strict parse: still drops them, findings and structure as before
        self.assertEqual([(t.tid, t.state) for t in wg.parse(D10)], [(1, "JOIN")])
        self.assertEqual(wg.parse(D10)[0].detail, None)

    def test_mutex_waits_get_no_name(self):  # not edges: the judge says none, the tool says unknown
        self.assertEqual(wg.judge(wg.parse(D10, any_blocked=True))["kind"], "none")
        self.assertEqual(wg.judge(wg.parse(D02, any_blocked=True))["kind"], "none")


class SelfSend(unittest.TestCase):
    """Found and shown in an «unknown» reason, not named by the judge (2026-11-21: no target check yet)."""

    def test_recorded_self_send_is_found_but_not_named(self):
        th = wg.parse(D22)
        self.assertEqual(wg.self_sends(th, later=[th, th]), [204820])
        self.assertEqual(wg.judge(th, later=[th, th]), {"kind": "none"})

    def test_a_receiving_thread_in_the_same_process_is_not_found(self):
        th = wg.parse(table((50, 1, "var/qd/x/a", "10r", "SEND", 50), (50, 2, "var/qd/x/a", "10r", "RECEIVE", 1)))
        self.assertEqual(wg.self_sends(th), [])

    def test_must_hold_in_every_snapshot(self):  # the receiver thread was only busy at the first snapshot
        first = wg.parse(table((50, 1, "var/qd/x/a", "10r", "SEND", 50), (50, 2, "var/qd/x/a", "10r", "READY", "")))
        later = wg.parse(table((50, 1, "var/qd/x/a", "10r", "NANOSLEEP", ""), (50, 2, "var/qd/x/a", "10r", "RECEIVE", 1)))
        self.assertEqual(wg.self_sends(first, later=[later]), [])
        self.assertEqual(wg.self_sends(first, later=[first]), [50])

    def test_a_ticking_loop_is_left_out(self):
        th = wg.parse(D22)
        self.assertEqual(wg.self_sends(th, later=[th], moving=frozenset({204820})), [])

    def test_reply_on_own_pid_is_not_a_self_send(self):  # another thread took the message and is working on it
        th = wg.parse(table((50, 1, "var/qd/x/a", "10r", "REPLY", 50), (50, 2, "var/qd/x/a", "10r", "READY", "")))
        self.assertEqual(wg.self_sends(th), [])

    def test_edges_still_leave_self_out(self):
        self.assertEqual(wg.edges(wg.parse(D22)), [])

    def test_kernel_is_never_a_self_send(self):
        self.assertEqual(wg.self_sends(wg.parse(KERNEL.replace("REPLY", "SEND "))), [])
