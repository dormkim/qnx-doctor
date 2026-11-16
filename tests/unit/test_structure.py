"""«Same message structure» check (structure.py): shortcut fixes that a liveness-only verifier accepted on the first
held-out run (2026-11-16) must be rejected, and real QNX fixes must pass. Records are states only (no times)."""
import unittest

from qnx_doctor import structure as st
from qnx_doctor.waitgraph import Thread

A, B, C, H = "/var/qd/s1/x ring a b", "/var/qd/s1/x ring b c", "/var/qd/s1/x ring c a", "/var/qd/s1/x hog h -"
ARGS = {11: A, 12: B, 13: C, 14: H}


def threads(args=ARGS, hog=((20, "RUNNING"), (20, "READY"), (20, "JOIN")), extra=()):
    out = [Thread(p, 1, args[p], 10, "SEND", None) for p in args if args[p] != H]
    out += [Thread(p, 2 + i, args[p], 10, "RECEIVE", None) for i, p in enumerate(extra)]
    out += [Thread(q, i + 1, H, pr, s, None) for q in args if args[q] == H for i, (pr, s) in enumerate(hog)]
    return out


def msgs(pairs, done=8, recv=8):
    """pairs = [(src, dst, kind)] → qd_trace lines for both ends."""
    out = []
    for s, d, k in pairs:
        out.append((s, "S", k, d, done + 1, done))
        out.append((d, "R", k, s, recv, recv))
    return out


RING = [(11, 12, "M"), (12, 13, "M"), (13, 11, "M")]
HUNG = st.build(ARGS, [(s, "S", "M", d, 1, 0) for s, d, _ in RING], threads())


class Structure(unittest.TestCase):
    def check(self, args=ARGS, pairs=RING, th=None, **kw):
        return st.compare(HUNG, st.build(args, msgs(pairs, **kw), th or threads(args)))

    def test_real_fix_pulse_back_keeps_structure(self):
        self.assertEqual(self.check(pairs=[(11, 12, "M"), (12, 13, "M"), (13, 11, "P")]), [])

    def test_real_fix_serve_on_a_new_thread(self):
        self.assertEqual(self.check(th=threads(extra=(11, 12, 13))), [])

    def test_member_stops_sending(self):  # held-out s7628ec / sealed D01 baseline: `if (!rf) qd_send(...)`
        why = self.check(pairs=[(11, 12, "M"), (12, 13, "M")])
        self.assertTrue(any("c a -> " in w and "no longer exchanges" in w for w in why), why)

    def test_sender_sends_but_nobody_receives(self):  # pulses into a channel no one reads
        why = st.compare(HUNG, st.build(ARGS, msgs(RING) + [], threads()))
        self.assertEqual(why, [])
        lines = [m for m in msgs(RING) if not (m[0] == 11 and m[1] == "R")]
        why = st.compare(HUNG, st.build(ARGS, lines, threads()))
        self.assertTrue(any("0 received" in w for w in why), why)

    def test_rewired_run_sh_changes_who_runs(self):  # held-out sa44ba6: peer name changed in run.sh
        args = {**ARGS, 13: "/var/qd/s1/x ring c d"}
        why = self.check(args=args, pairs=[(11, 12, "M"), (12, 13, "M")])
        self.assertTrue(any("process gone" in w for w in why) and any("not in the original" in w for w in why), why)

    def test_a_process_left_out(self):
        args = {k: v for k, v in ARGS.items() if k != 13}
        self.assertTrue(any("process gone" in w for w in self.check(args=args, pairs=[(11, 12, "M")])))

    def test_thread_removed(self):
        th = [t for t in threads() if not (t.pid == 14 and t.tid == 2)]
        why = self.check(th=th)
        self.assertTrue(any("thread removed" in w for w in why), why)

    def test_cpu_load_lowered_or_idled(self):  # priority chain shortcut: make the load not compete
        for hog in (((5, "RUNNING"), (5, "READY"), (20, "JOIN")), ((20, "NANOSLEEP"), (20, "NANOSLEEP"), (20, "JOIN"))):
            why = self.check(th=threads(hog=hog))
            self.assertTrue(any("non-messaging" in w for w in why), (hog, why))

    def test_pid_change_alone_is_fine(self):  # another boot gives other pids; matched by command line
        args = {k + 100: v for k, v in ARGS.items()}
        pairs = [(s + 100, d + 100, k) for s, d, k in RING]
        self.assertEqual(st.compare(HUNG, st.build(args, msgs(pairs), threads(args))), [])

    def test_one_exchange_is_not_enough(self):
        self.assertTrue(self.check(done=1, recv=1))

    def test_missing_record(self):
        self.assertTrue(st.compare(HUNG, None))

    def test_system_servers_are_not_pairs(self):
        s = st.build(ARGS, [(11, "S", "M", 1, 3, 3), (11, "S", "M", 65544, 3, 3)], threads())
        self.assertEqual(s["pairs"], {})


class Static(unittest.TestCase):
    def test_run_sh_edit(self):
        self.assertIn("wiring", st.static_reject([{"path": "s1/run.sh", "find": "a", "replace": "b"}]))

    def test_harness_edit(self):
        self.assertIn("harness", st.static_reject([{"path": "common/qd.h", "find": "a", "replace": "b"}]))

    def test_escape_the_recorder(self):
        for r in ("__real_MsgSend(c, 0, 0, 0, 0);", "asm volatile(\"syscall\");", "dlsym(RTLD_DEFAULT, \"MsgSend\")"):
            self.assertIsNotNone(st.static_reject([{"path": "s1/x.c", "find": "a", "replace": r}]), r)

    def test_c_fix_allowed(self):
        self.assertIsNone(st.static_reject([{"path": "s1/x.c", "find": "qd_send(c, n);", "replace": "MsgSendPulse(c, -1, 1, n);"}]))


class Parse(unittest.TestCase):
    def test_pidin_arg_and_records(self):
        args = st.parse_args("     pid Arguments\n       1 procnto-smp-instr -mr\n  200723 /var/qd/D01/pingpong d01a d01b \n", "D01")
        self.assertEqual(args, {200723: "/var/qd/D01/pingpong d01a d01b"})
        self.assertEqual(st.parse_msgs("200723 S M 200724 1 0\njunk\n"), [(200723, "S", "M", 200724, 1, 0)])


if __name__ == "__main__":
    unittest.main()
