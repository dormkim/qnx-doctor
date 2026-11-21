"""Property tests for waitgraph, from the rules in its header (fixed seeds, stdlib only — no new dependency).

Each property runs on 400 random process tables rendered as pidin text, so the parser is exercised too.
Includes «attack the judge» mutations: delete one cycle edge or flip one state → the deadlock verdict must flip."""
import random
import unittest

from qnx_doctor import waitgraph as wg

STATES = ["RUNNING", "READY", "RECEIVE", "NANOSLEEP", "SEND", "REPLY", "SIGSUSPEND", "CONDVAR"]
N = 400


def rand_table(r):
    pids = r.sample(range(2, 99999), r.randint(2, 8))
    rows = [(1, 1, "/proc/boot/procnto-smp-instr", 0, "READY", None)]
    for p in pids:
        for tid in range(1, r.randint(1, 2) + 1):
            st = r.choice(STATES)
            peer = r.choice(pids + [1, p]) if st in ("SEND", "REPLY") else (1 if st == "RECEIVE" else None)
            rows.append((p, tid, r.choice(["var/qd/x/a", "bin/sh", "proc/boot/io"]), r.randint(1, 63), st, peer))
    return rows


def render(rows):
    head = "     pid tid name                         prio STATE          Blocked\n"
    return head + "".join(f"{p:8d} {t:3d} {n:28s} {pr:3d}r {st:14s} {'' if b is None else b}\n" for p, t, n, pr, st, b in rows)


def brute_cyclic(rows):
    g = {}
    for p, _, _, _, st, b in rows:
        if st in ("SEND", "REPLY") and b is not None and b > 1 and b != p:
            g.setdefault(p, set()).add(b)

    def reach(a):
        seen, todo = set(), [a]
        while todo:
            x = todo.pop()
            for y in g.get(x, ()):
                if y not in seen:
                    seen.add(y); todo.append(y)
        return seen
    return {p for p in g if p in reach(p)}


def brute_self_send(rows):
    """Pids with a SEND on their own pid and no RECEIVE thread (rule in the waitgraph header)."""
    return {p for p, _, _, _, st, b in rows if st == "SEND" and b == p and p > 1
            and not any(q == p and s2 == "RECEIVE" for q, _, _, _, s2, _ in rows)}


class Props(unittest.TestCase):
    def test_parser_round_trip(self):
        r = random.Random(1)
        for _ in range(N):
            rows = rand_table(r)
            got = [(t.pid, t.tid, t.name, t.prio, t.state, t.blocked) for t in wg.parse(render(rows))]
            self.assertEqual(got, rows)

    def test_cycle_iff_brute_force_and_same_members(self):
        r = random.Random(2)
        for _ in range(N):
            rows = rand_table(r)
            th = wg.parse(render(rows))
            cyc = brute_cyclic(rows)
            members = {p for c in wg.cycles(th) for p in c}
            self.assertEqual(members, cyc)
            self.assertEqual(set(wg.self_sends(th)), brute_self_send(rows))  # found and shown, never named (2026-11-21)
            self.assertEqual(wg.judge(th)["kind"] == "deadlock", bool(cyc))

    def test_pid1_and_self_never_edges(self):
        r = random.Random(3)
        for _ in range(N):
            for t, peer in wg.edges(wg.parse(render(rand_table(r)))):
                self.assertTrue(peer > 1 and peer != t.pid)

    def test_no_send_reply_means_none(self):
        r = random.Random(4)
        for _ in range(N):
            rows = [x if x[4] not in ("SEND", "REPLY") else (*x[:4], "RECEIVE", 1) for x in rand_table(r)]
            self.assertEqual(wg.judge(wg.parse(render(rows))), {"kind": "none"})

    def test_inversion_only_when_rule_holds(self):
        r = random.Random(5)
        for _ in range(N):
            th = wg.parse(render(rand_table(r)))
            for i in wg.inversions(th):
                w, s = i["waiter"], i["server"]
                self.assertEqual((s.state, s.pid), ("READY", w.blocked))
                self.assertLess(s.prio, w.prio)
                self.assertTrue(i["running"])
                for x in i["running"]:
                    self.assertIn(x.state, ("RUNNING", "READY"))
                    self.assertTrue(s.prio < x.prio < w.prio)

    def test_attack_delete_or_flip_one_cycle_edge(self):
        """Break a cycle in a real-looking snapshot (one waiter now RUNNING / waits on kernel): verdict must flip."""
        r, tricks = random.Random(6), 0
        for _ in range(N):
            L = r.randint(2, 6)
            pids = r.sample(range(2, 99999), L)
            rows = [(p, 1, "var/qd/x/a", 10, r.choice(["SEND", "REPLY"]), pids[(k + 1) % L]) for k, p in enumerate(pids)]
            self.assertEqual(wg.judge(wg.parse(render(rows)))["kind"], "deadlock")
            k = r.randrange(L)
            broken = list(rows)
            broken[k] = (*rows[k][:4], "RUNNING", None) if r.random() < 0.5 else (*rows[k][:4], "REPLY", 1)
            self.assertNotEqual(wg.judge(wg.parse(render(broken)))["kind"], "deadlock")
            tricks += 1
        self.assertEqual(tricks, N)


if __name__ == "__main__":
    unittest.main()
