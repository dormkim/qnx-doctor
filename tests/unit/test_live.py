"""hang --live: a capture taken from a running target with no harness (bench/live_demo.sh, 2026-11-16).
The fixture is the raw console text, including the echoed command line that also holds the ARGS/END markers."""
import os
import unittest

from qnx_doctor import live

FIX = os.path.join(os.path.dirname(__file__), "fixtures", "live_control_loop_1116.txt")


class Live(unittest.TestCase):
    def setUp(self):
        self.out = open(FIX).read()

    def test_cycle_and_roles_by_command_line(self):
        r = live.check(self.out)
        self.assertEqual(r["kind"], "deadlock")
        self.assertEqual(sorted(c.split()[-1] for c in r["commands"].values()), ["actuator", "control", "sensor"])

    def test_echoed_markers_are_not_read_as_output(self):
        self.assertIn("/var/app/loop control", live.section(self.out, "ARGS"))

    def test_call_sites_from_source(self):
        src = os.path.join(os.path.dirname(__file__), "..", "..", "scenarios", "hang_demo", "control_loop")
        r = live.check(self.out, src=src)
        self.assertTrue(r["sites"] and all(s.startswith("loop.c:") for s in r["sites"]))

    def test_no_capture_is_an_error_not_a_clean_bill(self):
        with self.assertRaises(RuntimeError):
            live.capture("echo")  # prints the line back but never runs pidin: must not read as «no hang»


if __name__ == "__main__":
    unittest.main()
