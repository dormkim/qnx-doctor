"""hang.observe reads every thread, and a mutex hang is never «proven fixed» (2026-11-22, gate c of bench/V6_PLAN.md).
The boot is replaced by text in the observer's format, made up here in the shape of the harness checks mx01 and mx02."""
import os
import shutil
import tempfile
import unittest
from unittest import mock

from qnx_doctor import hang
from qnx_doctor import hangdoctor
from qnx_doctor import structure as st

SRV, CLI, SOLO = 204820, 204821, 204822
ARGS = {SRV: "/var/qd/m1/desk", CLI: "/var/qd/m1/teller"}
ADDR = "(0x1000000008) 204820-02 #0"


def row(pid, tid, prog, state, blocked=""):
    return f"  {pid}   {tid} var/qd/m1/{prog}            10r {state:<14} {blocked}".rstrip()


def desk(*workers):
    """The server (thread 1 receives, workers follow) and its REPLY-blocked client."""
    rows = [row(SRV, 1, "desk", "RECEIVE", "1")]
    rows += [row(SRV, i + 2, "desk", *w) for i, w in enumerate(workers)]
    return rows + [row(CLI, 1, "teller", "REPLY", str(SRV))]


def boot_text(snaps, first, second, msgs=(), args=ARGS):
    def part(title, lines):
        return f"=== {title} ===\n" + "".join(f"{x}\n" for x in lines)
    return (part("PIDIN", snaps[0]) + part("TICKS", [f"/tmp/d0teller.log {first}"])
            + part("ARGS", [f"  {p} {a}" for p, a in args.items()]) + part("PIDIN2", snaps[1]) + part("PIDIN3", snaps[2])
            + part("TICKS2", [f"/tmp/d0teller.log {second}"])
            + part("MSGS1", [m.replace(" 9 9", " 4 4") for m in msgs]) + part("MSGS", msgs) + "=== END ===\nQDDONE\n")


class Observe(unittest.TestCase):
    def setUp(self):
        self.work = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.work, True)

    def observe(self, *a, **kw):
        text = boot_text(*a, **kw)
        with mock.patch.object(hang, "sdp_env", lambda env: env), \
                mock.patch.object(hang, "build", return_value=(True, "built")), \
                mock.patch.object(hang, "image", return_value=(True, os.path.join(self.work, "vm"), "")), \
                mock.patch.object(hang, "target", return_value=(True, text)):
            return hang.observe(self.work, "m1")

    def hung(self, *workers):
        return self.observe([desk(*workers)] * 3, 1, 1, [f"{CLI} S M {SRV} 1 0", f"{SRV} W C {SRV} 1 0"])

    def alive(self, *workers):
        msgs = [f"{CLI} S M {SRV} 9 9", f"{SRV} R M {CLI} 9 9", f"{SRV} W C {SRV} 9 0"]
        return self.observe([desk(*workers)] * 3, 20, 30, msgs)

    def test_mutex_worker_is_in_the_structure_record(self):
        s = self.hung(("MUTEX", ADDR), ("MUTEX", ADDR), ("MUTEX", ADDR))["structure"]
        self.assertEqual(len(s["threads"][ARGS[SRV]]), 4)
        self.assertEqual(s["lock_waits"], [ARGS[SRV]])

    def test_mutex_worker_is_not_a_missing_reply(self):
        first = self.hung(("MUTEX", ADDR), ("MUTEX", ADDR))
        detected, note = hangdoctor.named(first)
        self.assertEqual((first["judge"]["kind"], detected), ("none", "unknown"))
        self.assertIn("MUTEX", note)

    def test_all_receive_is_still_a_missing_reply(self):
        self.assertEqual(hangdoctor.named(self.hung())[0], "missing_reply")
        self.assertEqual(hangdoctor.named(self.hung(("RECEIVE", "2")))[0], "missing_reply")

    def test_sem_or_condvar_worker_is_not_all_receive_either(self):  # the cost: such a server is «unknown»
        for state, col in (("SEM", "5a4e4780d8"), ("CONDVAR", "(0x5a4e459a4c)")):
            self.assertEqual(hangdoctor.named(self.hung((state, col)))[0], "unknown", state)

    def test_process_with_only_a_mutex_thread_is_alive(self):
        rows = desk() + [row(SOLO, 1, "solo", "MUTEX", ADDR)]
        first = self.observe([rows] * 3, 1, 1, args={**ARGS, SOLO: "/var/qd/m1/solo"})
        self.assertEqual(first["alive"], 3)
        self.assertEqual(len(first["structure"]["threads"]["/var/qd/m1/solo"]), 1)

    def test_removed_worker_is_seen(self):
        first = self.hung(("CONDVAR", "(0x5a4e459a4c)"), ("SEM", "5a4e4780d8"))
        v = hangdoctor.verdict(first, self.alive(("NANOSLEEP",)))
        self.assertTrue(v["live"])
        self.assertFalse(v["fixed"])
        self.assertTrue(any("thread removed" in w for w in v["structure"]), v["structure"])

    def test_mutex_hang_is_never_proven_fixed(self):
        first = self.hung(("MUTEX", ADDR), ("MUTEX", ADDR))
        v = hangdoctor.verdict(first, self.alive(("NANOSLEEP",), ("NANOSLEEP",)))
        self.assertTrue(v["live"])
        self.assertFalse(v["fixed"])
        self.assertEqual(len(v["structure"]), 1)
        self.assertTrue(v["structure"][0].startswith(st.UNPROVABLE))
        self.assertIn(st.UNPROVABLE, hangdoctor.result_text(v))

    def test_passing_mutex_wait_does_not_block_a_fix(self):  # MUTEX in one snapshot only
        snaps = [desk(("MUTEX", ADDR)), desk(("RECEIVE", "2")), desk(("RECEIVE", "2"))]
        first = self.observe(snaps, 1, 1, [f"{CLI} S M {SRV} 1 0", f"{SRV} W C {SRV} 1 0"])
        self.assertEqual(first["structure"]["lock_waits"], [])
        self.assertTrue(hangdoctor.verdict(first, self.alive(("NANOSLEEP",)))["fixed"])

    def test_mutex_wait_of_another_process_is_not_the_programs(self):  # system threads are not in the record
        rows = desk() + ["  163853   3 system/bin/io-sock             21r MUTEX          " + ADDR]
        self.assertEqual(self.observe([rows] * 3, 1, 1)["structure"]["lock_waits"], [])

    def test_records_without_the_key_read_as_before(self):
        before = self.hung()["structure"]
        before.pop("lock_waits")
        self.assertEqual(st.compare(before, self.alive()["structure"]), [])


if __name__ == "__main__":
    unittest.main()
