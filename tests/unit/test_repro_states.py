"""bench/repro_states.py: does the unmodified run show the processes and thread states its label describes?
Lines and label texts are the recorded ones of the dev sets (v4 D08, D10; v5 E01, E04, E11), used as fixtures."""
import os
import sys
import unittest

from qnx_doctor import waitgraph as wg

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "bench"))
import repro_states as rs  # noqa: E402

E01 = """  204820   1 var/qd/E01/lowsrv             12r READY
  204821   1 var/qd/E01/hog                20r READY
  204822   1 var/qd/E01/hicli              30r REPLY          204820
"""
E01_LABEL = {"kind": "priority_chain", "states": {"d0e01a": "REPLY-blocked on d0e01b", "d0e01b": "READY at prio 12 (runnable, never scheduled)",
                                                  "d0e01c": "RUNNING at prio 20 busy loop"}}
RUN3 = "#!/bin/sh\n/var/qd/E01/lowsrv d0e01b 12 > /tmp/d0e01b.log 2>&1 &\n/var/qd/E01/hog d0e01c 20 > /tmp/d0e01c.log 2>&1 &\n" \
       "/var/qd/E01/hicli d0e01a d0e01b 30 120 > /tmp/d0e01a.log 2>&1 &\nsleep 4\n"
D08 = """  204820   1 var/qd/D08/lowfix_srv         12r RECEIVE        1
  204821   1 var/qd/D08/hog                20r READY
  204822   1 var/qd/D08/hiclient           30r NANOSLEEP
"""
D08_LABEL = {"kind": "priority_chain", "states": {"d008a": "REPLY-blocked on d008b", "d008b": "RECEIVE at prio 12 (ready but never scheduled)",
                                                  "d008c": "RUNNING at prio 20 busy loop"}}
D10 = """  204820   1 var/qd/D10/abba               10r JOIN           2
  204820   2 var/qd/D10/abba               10r MUTEX          (0x3f08248038) 204820-03 #0
  204820   3 var/qd/D10/abba               10r MUTEX          (0x3f08248030) 204820-02 #0
"""


def snaps(text):
    return [wg.parse(text, any_blocked=True)]


class NamedStates(unittest.TestCase):
    def test_words_alternatives_and_runnable(self):
        self.assertEqual(rs.named_states(E01_LABEL), [("REPLY",), ("RUNNING", "READY")])
        self.assertEqual(rs.named_states({"states": {"a": "SEND/REPLY-blocked on b"}}), [("REPLY", "SEND")])

    def test_a_negated_clause_names_nothing(self):
        lab = {"states": {"a": "RUNNING busy-wait at its own prio; never blocks on a peer, no SEND/REPLY edge"}}
        self.assertEqual(rs.named_states(lab), [("RUNNING", "READY")])
        self.assertEqual(rs.named_states({"states": "no message wait at all: probe is in NANOSLEEP"}), [("NANOSLEEP",)])

    def test_v3_string_form(self):
        self.assertEqual(rs.named_states({"states": "navcore REPLY-blocked on routemap; routemap SEND-blocked on navcore"}), [("REPLY",), ("SEND",)])


class Check(unittest.TestCase):
    def test_label_states_seen(self):
        self.assertEqual(rs.check(E01_LABEL, "E01", RUN3, snaps(E01)), [])

    def test_client_never_connected(self):  # v4 D08: the loops «stop», but nobody is REPLY-blocked
        why = rs.check(D08_LABEL, "D08", RUN3.replace("E01", "D08"), snaps(D08))
        self.assertEqual(why, ["label names a thread in REPLY; no program thread was in REPLY"])

    def test_a_started_process_is_not_in_the_list(self):  # v5 E04: run.sh starts 4, 3 are there
        run4 = RUN3 + "/var/qd/E01/hog d0e01d 22 > /tmp/d0e01d.log 2>&1 &\n"
        self.assertIn("run.sh starts 4 program processes, 3 in the process list", rs.check(E01_LABEL, "E01", run4, snaps(E01)))

    def test_mutex_label_is_seen_now_that_the_line_is_parsed(self):
        lab = {"kind": "deadlock", "states": {"a": "MUTEX-blocked on m2 (holds m1)", "b": "MUTEX-blocked on m1 (holds m2)"}}
        self.assertEqual(rs.check(lab, "D10", "/var/qd/D10/abba d010a d010b > /tmp/x.log 2>&1 &\n", snaps(D10)), [])

    def test_state_seen_in_a_later_snapshot_counts(self):
        first = wg.parse(E01.replace("REPLY          204820", "READY"), any_blocked=True)
        self.assertEqual(rs.check(E01_LABEL, "E01", RUN3, [first, wg.parse(E01, any_blocked=True)]), [])

    def test_other_programs_threads_do_not_count(self):
        other = E01.replace("var/qd/E01/hicli", "system/bin/io-sock")
        self.assertTrue(any("REPLY" in w for w in rs.check(E01_LABEL, "E01", RUN3, snaps(other))))

    def test_healthy_label_is_checked_for_processes_only(self):
        lab = {"kind": "healthy", "states": {"a": "RECEIVE idle between knocks", "b": "SEM never"}}
        self.assertEqual(rs.check(lab, "E01", RUN3, snaps(E01)), [])


class FromRecord(unittest.TestCase):
    def row(self, lines, verdict="none", alive=3, procs=None):
        g = {"kind": "graph", "verdict": verdict, "lines": lines.splitlines(), "alive": alive}
        if procs is not None:
            g["structure"] = {"procs": procs}
        return {"timeline": [g]}

    def test_whole_program_record(self):
        th, n, partial = rs.from_record(self.row(D08, procs=["a", "b", "c"]), "D08")
        self.assertEqual((n, partial), (3, False))

    def test_record_of_a_named_hang_is_partial(self):
        _, n, partial = rs.from_record(self.row(E01, verdict="priority_chain", procs=["a", "b", "c"]), "E01")
        self.assertTrue(partial)
        why = rs.check({"kind": "deadlock", "states": "x SEM-blocked"}, "E01", RUN3, *rs.from_record(self.row(E01, verdict="deadlock"), "E01"))
        self.assertTrue(why[0].endswith(rs.PARTIAL))

    def test_no_graph_entry(self):
        self.assertIsNone(rs.from_record({"timeline": []}, "E01"))


if __name__ == "__main__":
    unittest.main()
