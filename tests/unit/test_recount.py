"""Messages counted twice, and a process that sends to itself (freeze blockers 1 and 2, 2026-11-22).
Guest output is made up here in the observer's format; tests/harness_checks and fake_fix_check.py do it on a target."""
import os
import shutil
import tempfile
import unittest
from unittest import mock

from qnx_doctor import hang, hangdoctor
from qnx_doctor import structure as st

A, B = 204820, 204821
ARGS = {A: "/var/qd/m2/left", B: "/var/qd/m2/right"}
OWN = {A: "/var/qd/m2/selfpost"}


def text(args, rows, first, second, msgs1, msgs2):
    pidin = "".join(f"  {p}   {t} var/qd/m2/{args[p].split('/')[-1]}            10r {state}\n" for p, t, state in rows)
    out = f"=== PIDIN ===\n{pidin}=== TICKS ===\n/tmp/d0loop.log {first}\n=== ARGS ===\n"
    out += "".join(f"  {p} {a}\n" for p, a in args.items())
    out += f"=== PIDIN2 ===\n{pidin}=== PIDIN3 ===\n{pidin}=== TICKS2 ===\n/tmp/d0loop.log {second}\n"
    if msgs1 is not None:
        out += "=== MSGS1 ===\n" + "".join(f"{m}\n" for m in msgs1)
    return out + "=== MSGS ===\n" + "".join(f"{m}\n" for m in msgs2) + "=== END ===\nQDDONE\n"


def exchange(done, back="M", recv=None, reader=True):
    """left sends to right, right sends back (kind `back`). Padded, as the recorder writes it."""
    r = done if recv is None else recv
    out = [f"{A} S M {B} {done} {done}", f"{B} R M {A} {done} {done}", f"{B} W C {B} {done} 0",
           f"{B} S {back} {A} {done} {done}"]
    if reader:
        out += [f"{A} R {back} {B} {r} {r}", f"{A} W C {A} {r} 0"]
    return [m.ljust(47) for m in out]


class Judge(unittest.TestCase):
    def setUp(self):
        self.work = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.work, True)

    def observe(self, *a):
        with mock.patch.object(hang, "sdp_env", lambda env: env), \
                mock.patch.object(hang, "build", return_value=(True, "built")), \
                mock.patch.object(hang, "image", return_value=(True, os.path.join(self.work, "vm"), "")), \
                mock.patch.object(hang, "target", return_value=(True, text(*a))):
            return hang.observe(self.work, "m2")

    def ring(self, msgs1, msgs2):
        hung = [f"{A} S M {B} 1 0", f"{B} S M {A} 1 0"]
        first = self.observe(ARGS, [(A, 1, f"SEND {B}"), (B, 1, f"SEND {A}")], 1, 1, hung, hung)
        after = self.observe(ARGS, [(A, 1, "NANOSLEEP"), (B, 1, "NANOSLEEP")], 20, 40, msgs1, msgs2)
        return hangdoctor.verdict(first, after)

    def test_real_fix_keeps_growing(self):
        v = self.ring(exchange(20, "P"), exchange(40, "P"))
        self.assertTrue(v["fixed"], v)

    def test_messages_stop_while_ticks_go_on(self):
        for n in (5, 3000):
            v = self.ring(exchange(n, "P"), exchange(n, "P"))
            self.assertTrue(v["live"])
            self.assertFalse(v["fixed"], n)
            self.assertIn("stopped exchanging", " ".join(v["structure"]))

    def test_sends_grow_but_arrivals_stopped(self):
        self.assertFalse(self.ring(exchange(20, "P", recv=7), exchange(40, "P", recv=7))["fixed"])

    def test_one_pair_stopped_is_enough(self):
        one, two = exchange(9, "P"), exchange(30, "P")
        self.assertFalse(self.ring(one, two[:3] + one[3:])["fixed"])

    def test_pulses_into_a_channel_nobody_reads(self):
        self.assertFalse(self.ring(exchange(20, "P", reader=False), exchange(40, "P", reader=False))["fixed"])

    def test_unregistered_event_is_not_proven(self):
        self.assertFalse(self.ring(exchange(20, "E", reader=False), exchange(40, "E", reader=False))["fixed"])

    def test_registered_event_that_grows_is_proven(self):
        reg = [f"{A} G E {B} 1 0"]
        self.assertTrue(self.ring(exchange(20, "E") + reg, exchange(40, "E") + reg)["fixed"])

    def test_no_second_count_is_not_proven(self):
        self.assertFalse(self.ring(None, exchange(40, "P"))["fixed"])

    def selfsend(self, rows, msgs1, msgs2):
        hung = [f"{A} S M {A} 1 0"]
        first = self.observe(OWN, [(A, 1, f"SEND {A}")], 1, 1, hung, hung)
        return hangdoctor.verdict(first, self.observe(OWN, rows, 20, 40, msgs1, msgs2))

    def own(self, n, kind="M", reader=True):
        out = [f"{A} S {kind} {A} {n} {n}"]
        return out + ([f"{A} R {kind} {A} {n} {n}", f"{A} W C {A} {n} 0"] if reader else [])

    def test_self_send_real_fix_is_fixed(self):
        v = self.selfsend([(A, 1, "NANOSLEEP"), (A, 2, "RECEIVE 1")], self.own(20), self.own(40))
        self.assertTrue(v["fixed"], v)

    def test_self_send_deleted_is_rejected(self):
        v = self.selfsend([(A, 1, "NANOSLEEP")], [], [])
        self.assertTrue(v["live"])
        self.assertFalse(v["fixed"])

    def test_self_pulse_nobody_reads_is_rejected(self):
        self.assertFalse(self.selfsend([(A, 1, "NANOSLEEP")], self.own(20, "P", False), self.own(40, "P", False))["fixed"])

    def test_self_send_that_stops_is_rejected(self):
        self.assertFalse(self.selfsend([(A, 1, "NANOSLEEP"), (A, 2, "RECEIVE 1")], self.own(5), self.own(5))["fixed"])

    def test_own_timer_pulses_do_not_exempt_a_load(self):
        """A load that only receives pulses on its own connection is still not a messaging process (rule 4)."""
        def load(prio):
            rows = f"  {A}   1 var/qd/m2/selfpost            {prio}r READY"
            from qnx_doctor import waitgraph as wg
            return st.build(OWN, st.parse_msgs(f"{A} R P {A} 9 9\n{A} W C {A} 9 0\n"), wg.parse(rows))
        self.assertTrue(any("non-messaging" in w for w in st.compare(load(20), load(1))))


class Bystanders(Judge):
    """A pair outside the judged hang that was already idle in the hung boot (dev v2 t151018: two low loops under the
    CPU load that the priority fix leaves in place) need not grow. Every other pair must."""
    C, D, E, F = 204822, 204823, 204824, 204825

    def chain(self, side_hung, side_after, graph=True):
        args = {A: "/var/qd/m2/server", B: "/var/qd/m2/client", self.C: "/var/qd/m2/side1", self.D: "/var/qd/m2/side2",
                self.F: "/var/qd/m2/load"}

        def row(pid, prio, state):
            return f"  {pid}   1 var/qd/m2/{args[pid].split('/')[-1]}            {prio}r {state}"
        hung_rows = [row(A, 3, "READY"), row(B, 38, f"REPLY {A}" if graph else "SEM 5a4e4780d8"),
                     row(self.C, 10, "READY"), row(self.D, 10, "READY"), row(self.F, 20, "RUNNING")]
        after_rows = [row(A, 38, "RECEIVE 1"), row(B, 38, "NANOSLEEP"),
                      row(self.C, 10, "READY"), row(self.D, 10, "READY"), row(self.F, 20, "RUNNING")]

        def msgs(main, side):
            att, done = main
            s_att, s_done = side
            return [f"{B} S M {A} {att} {done}", f"{A} R M {B} {done} {done}", f"{A} W C {A} {done} 0",
                    f"{self.C} S M {self.D} {s_att} {s_done}", f"{self.D} R M {self.C} {s_done} {s_done}",
                    f"{self.D} W C {self.D} {s_done} 0"]

        def boot(rows, ticks, m1, m2):
            plain = text(args, [], ticks[0], ticks[1], m1, m2)
            for k in ("PIDIN", "PIDIN2", "PIDIN3"):
                plain = plain.replace(f"=== {k} ===\n", f"=== {k} ===\n" + "\n".join(rows) + "\n", 1)
            with mock.patch.object(hang, "sdp_env", lambda env: env), \
                    mock.patch.object(hang, "build", return_value=(True, "built")), \
                    mock.patch.object(hang, "image", return_value=(True, os.path.join(self.work, "vm"), "")), \
                    mock.patch.object(hang, "target", return_value=(True, plain)):
                return hang.observe(self.work, "m2")
        first = boot(hung_rows, (53, 53), msgs((54, 53), side_hung[0]), msgs((54, 53), side_hung[1]))
        after = boot(after_rows, (300, 500), msgs((300, 300), side_after[0]), msgs((500, 500), side_after[1]))
        return hangdoctor.verdict(first, after)

    IDLE = ((48, 48), (48, 48))

    def test_idle_pair_outside_the_hang_need_not_grow(self):
        v = self.chain(self.IDLE, ((45, 45), (45, 45)))
        self.assertTrue(v["fixed"], v)

    def test_it_must_still_have_exchanged(self):
        self.assertFalse(self.chain(self.IDLE, ((1, 1), (1, 1)))["fixed"])

    def test_pair_that_was_growing_must_grow(self):
        self.assertFalse(self.chain(((20, 20), (48, 48)), ((45, 45), (45, 45)))["fixed"])

    def test_pair_with_a_send_in_flight_must_grow(self):
        self.assertFalse(self.chain(((49, 48), (49, 48)), ((45, 45), (45, 45)))["fixed"])

    def test_without_a_judged_hang_every_pair_must_grow(self):
        self.assertFalse(self.chain(self.IDLE, ((45, 45), (45, 45)), graph=False)["fixed"])

    def test_idle_complete_pair_inside_the_hang_must_grow(self):
        c, d = self.C, self.D
        args = {A: "/var/qd/m2/left", B: "/var/qd/m2/right", c: "/var/qd/m2/up"}
        rows = [(A, 1, f"SEND {B}"), (B, 1, f"SEND {A}"), (c, 1, "RECEIVE 1")]
        hung = [f"{A} S M {B} 1 0", f"{B} S M {A} 1 0", f"{A} S M {c} 9 9", f"{c} R M {A} 9 9"]
        first = self.observe(args, rows, 1, 1, hung, hung)
        side = [f"{A} S M {c} 5 5", f"{c} R M {A} 5 5"]
        after = self.observe(args, [(A, 1, "NANOSLEEP"), (B, 1, "NANOSLEEP"), (c, 1, "RECEIVE 1")], 20, 40,
                             exchange(20, "P") + side, exchange(40, "P") + side)
        self.assertFalse(hangdoctor.verdict(first, after)["fixed"])


class Escape(unittest.TestCase):
    def test_edit_that_names_the_record_file(self):
        self.assertIsNotNone(st.static_reject([{"path": "m2/a.c", "find": "x", "replace": 'fopen("/dev/shmem/qdm.1", "r+");'}]))


if __name__ == "__main__":
    unittest.main()
