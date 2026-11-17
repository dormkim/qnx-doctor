"""Liveness by progress (progress.py, waitgraph.judge `moving`, hangdoctor.named) and the scorer's «unknown» mapping.
Synthetic pidin tables only; the shapes are the harness checks lp01 (slow server), sp01 (CPU spin), bo01 (blocked
outside message passing), oc01 (priority chain), not any sealed scenario."""
import json
import os
import sys
import tempfile
import unittest

from qnx_doctor import hangdoctor as hd
from qnx_doctor import progress as pg
from qnx_doctor import waitgraph as wg

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "bench"))
import score_hang as sh  # noqa: E402
import score_structure as ss  # noqa: E402

T = wg.Thread
N = "var/qd/xx/"


def slow_server():   # client REPLY-blocked on a server whose only thread waits on its channel
    return [T(20, 1, N + "asker", 10, "REPLY", 21), T(21, 1, N + "late", 10, "RECEIVE", 1)]


def spin():
    return [T(30, 1, N + "meter", 10, "RUNNING", None), T(31, 1, N + "store", 10, "RECEIVE", 1)]


class Moves(unittest.TestCase):
    def test_states(self):
        mv = pg.moves({"d0a": 3, "d0b": 3, "d0c": 0, "d0d": 1}, {"d0a": 9, "d0b": 3, "d0c": 0})
        self.assertEqual(mv, {"d0a": "grew", "d0b": "flat", "d0c": "idle", "d0d": "missing"})
        self.assertIsNone(pg.moves({"d0a": 3}, None))

    def test_role_maps_to_program_of_same_name(self):
        self.assertEqual(pg.role_pids(slow_server(), "xx", ["d0asker", "d0late", "d0other"]),
                         {"d0asker": {20}, "d0late": {21}, "d0other": set()})


class JudgeMoving(unittest.TestCase):
    def test_slow_server_is_a_lost_reply_by_states_only(self):
        th = slow_server()
        self.assertEqual(wg.judge(th, later=[th, th])["kind"], "missing_reply")
        self.assertEqual(wg.judge(th, later=[th, th], moving=frozenset({20}))["kind"], "none")

    def test_moving_drops_a_chain_but_not_a_cycle(self):
        chain = [T(40, 1, N + "ctl", 30, "REPLY", 41), T(41, 1, N + "slow", 5, "READY", None), T(42, 1, N + "load", 22, "RUNNING", None)]
        self.assertEqual(wg.judge(chain, later=[chain])["kind"], "priority_chain")
        self.assertEqual(wg.judge(chain, later=[chain], moving=frozenset({40}))["kind"], "none")
        ring = [T(50, 1, N + "a", 10, "SEND", 51), T(51, 1, N + "b", 10, "SEND", 50)]
        self.assertEqual(wg.judge(ring, moving=frozenset({50, 51}))["kind"], "deadlock")

    def test_only_the_moving_waiter_is_dropped(self):
        th = slow_server() + [T(22, 1, N + "other", 10, "REPLY", 23), T(23, 1, N + "deaf", 10, "RECEIVE", 1)]
        j = wg.judge(th, later=[th], moving=frozenset({20}))
        self.assertEqual([w["waiter"]["pid"] for w in j["waits"]], [22])


class Classify(unittest.TestCase):
    def test_slow_server_with_growth_is_healthy(self):
        th = slow_server()
        mv = pg.moves({"d0asker": 5}, {"d0asker": 11})
        j = wg.judge(th, later=[th, th], moving=pg.moving_pids(th, "xx", mv))
        live = pg.classify(j["kind"], th, [th, th], "xx", {"d0asker": 5}, mv)
        self.assertEqual((j["kind"], live["state"]), ("none", "healthy"))

    def test_spin_is_not_healthy(self):
        th = spin()
        mv = pg.moves({"d0meter": 6}, {"d0meter": 6})
        live = pg.classify("none", th, [th, th], "xx", {"d0meter": 6}, mv)
        self.assertEqual(live["state"], "spinning")
        self.assertIn("30(meter)", live["why"])
        self.assertEqual(pg.detected(live["state"], "none"), "unknown")

    def test_spinning_names_the_stalled_loop_before_a_load(self):
        th = spin() + [T(32, 1, N + "load", 22, "RUNNING", None)]
        live = pg.classify("none", th, [th], "xx", {"d0meter": 6}, {"d0meter": "flat"})
        self.assertIn("30(meter)", live["why"])
        self.assertNotIn("load", live["why"])

    def test_spin_must_be_seen_in_every_snapshot(self):
        th, idle = spin(), [T(30, 1, N + "meter", 10, "NANOSLEEP", None), T(31, 1, N + "store", 10, "RECEIVE", 1)]
        live = pg.classify("none", th, [idle], "xx", {"d0meter": 6}, {"d0meter": "flat"})
        self.assertEqual(live["state"], "blocked_other")
        self.assertIn("meter NANOSLEEP", live["why"])

    def test_blocked_outside_message_passing(self):
        th = [T(60, 1, N + "feeder", 10, "SEM", None)]
        live = pg.classify("none", th, [th, th], "xx", {"d0feeder": 3}, {"d0feeder": "flat"})
        self.assertEqual(live["state"], "blocked_other")
        self.assertIn("feeder SEM", live["why"])

    def test_nothing_to_go_on(self):
        th = [T(70, 1, N + "a", 10, "RECEIVE", 1), T(71, 1, N + "b", 10, "RECEIVE", 1)]
        live = pg.classify("none", th, [th], "xx", {"d0a": 0, "d0b": 0}, {"d0a": "idle", "d0b": "idle"})
        self.assertEqual(live["state"], "no_info")

    def test_one_flat_loop_spoils_healthy(self):
        th = [T(80, 1, N + "a", 10, "RECEIVE", 1), T(81, 1, N + "b", 10, "RECEIVE", 1)]
        live = pg.classify("none", th, [th], "xx", {"d0a": 4, "d0b": 4}, {"d0a": "grew", "d0b": "flat"})
        self.assertNotEqual(live["state"], "healthy")

    def test_without_second_count_old_rule(self):
        self.assertEqual(pg.classify("none", spin(), [], "xx", {"d0meter": 6}, None)["state"], "healthy")
        self.assertEqual(pg.classify("none", [], [], "xx", {"d0meter": 0}, None)["state"], "no_info")
        self.assertEqual(pg.classify("deadlock", [], [], "xx", {}, None)["state"], "hang")


class ParseAnyBlocked(unittest.TestCase):
    TXT = "   5 1 var/qd/xx/feeder 10r SEM 8049a3c\n   6 1 var/qd/xx/srv 10r RECEIVE 1\n"

    def test_address_column_kept_only_on_request(self):
        self.assertEqual([t.pid for t in wg.parse(self.TXT)], [6])
        th = wg.parse(self.TXT, any_blocked=True)
        self.assertEqual([(t.pid, t.state, t.blocked) for t in th], [(5, "SEM", None), (6, "RECEIVE", 1)])
        self.assertEqual(pg.classify("none", th, [th], "xx", {"d0feeder": 3}, {"d0feeder": "flat"})["state"], "blocked_other")


class Named(unittest.TestCase):
    def obs(self, kind, live):
        return {"judge": {"kind": kind}, "ticks": {"d0a": 1}, "liveness": live}

    def test_words(self):
        self.assertEqual(hd.named(self.obs("none", {"state": "healthy", "why": ""})), ("none", "no hang found"))
        d, note = hd.named(self.obs("none", {"state": "no_info", "why": "not enough information: x"}))
        self.assertEqual(d, "unknown")
        self.assertTrue(note.startswith("unknown (no_info): not enough information"))
        self.assertEqual(hd.named(self.obs("missing_reply", {"state": "hang", "why": ""}))[0], "missing_reply")

    def test_old_observation_without_liveness(self):
        self.assertEqual(hd.named({"judge": {"kind": "none"}, "ticks": {"d0a": 0}})[0], "unknown")
        self.assertEqual(hd.named({"judge": {"kind": "none"}, "ticks": {"d0a": 3}})[0], "none")


class Sections(unittest.TestCase):
    OUT = ("=== PIDIN ===\n  1 1 procnto 0f READY\n=== TICKS ===\n/tmp/d0a.log 3\n=== ARGS ===\n=== PIDIN3 ===\n"
           "=== TICKS2 ===\n/tmp/d0a.log 9\n/tmp/d0b.log 1\n=== MSGS ===\n=== END ===\n")

    def test_second_count_does_not_leak_into_first(self):
        self.assertEqual(wg.split_check(self.OUT)[1], {"d0a": 3})
        self.assertEqual(wg.tick_counts(self.OUT, "TICKS2"), {"d0a": 9, "d0b": 1})

    def test_old_recording_has_no_second_count(self):
        old = self.OUT.split("=== TICKS2 ===")[0] + "=== MSGS ===\n"
        self.assertIsNone(wg.tick_counts(old, "TICKS2"))
        self.assertEqual(wg.split_check(old)[1], {"d0a": 3})


class ScorerUnknown(unittest.TestCase):
    def rows(self, recs):
        f = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False)
        f.write("\n".join(json.dumps(r) for r in recs) + "\n"); f.close()
        return ss.fresh_rows("code", f.name)

    def test_old_note_and_new_word_score_the_same(self):
        tl = [{"kind": "graph", "ticks": {"d0a": 0}}]
        r = self.rows([{"id": "old", "detected": "none", "note": "loop not running but no wait cycle or chain found", "timeline": tl},
                       {"id": "new", "detected": "unknown", "note": "unknown (no_info): ...", "timeline": tl},
                       {"id": "ok", "detected": "none", "note": "no hang found", "timeline": tl}])
        self.assertEqual([r[i]["detected"] for i in ("old", "new", "ok")], ["unknown", "unknown", "none"])
        labels = {"old": {"kind": "unknown"}, "new": {"kind": "unknown"}, "ok": {"kind": "none"}}
        s = ss.score(labels, r)
        self.assertEqual((s["hit"]["unknown"], s["hit"]["none"], s["fa"]), (2, 1, 0))

    def test_v1_v2_scorer_reads_new_unknown_as_old_none(self):
        labels = {"a": {"kind": "deadlock"}, "b": {"kind": "none"}}
        for d in ("none", "unknown"):
            s = sh.score(labels, [{"id": "a", "detected": d}, {"id": "b", "detected": d}])
            self.assertEqual((s["missed"], s["false_alarm"], s["hit"]["none"]), (1, 0, 1))


if __name__ == "__main__":
    unittest.main()
