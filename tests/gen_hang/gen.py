#!/usr/bin/env python3
"""Seeded random hang scenarios for qnx-doctor (QNX 8.0 message passing).

  python3 tests/gen_hang/gen.py --pool dev|heldout --out DIR      # writes DIR/common + one dir per scenario + DIR/labels.json

Each seed draws: a kind (deadlock / priority_chain / none), 2–6 processes, cycle length, how the cycle is closed
(every member sends first, or a starter plus relays that forward before replying = SEND and REPLY waits mixed),
extra waiters queued behind the cycle, decoys that wait long but legitimately (a slow server, idle receivers fed by
pulses), random role names, random function names and order, random loop style. The source carries no comments
and no marker; the answer key goes to labels.json, OUTSIDE the scenario directories the doctor copies.
Directory names are random too, so nothing in a path tells the kind.
"""
import argparse
import hashlib
import json
import os
import random
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
COMMON = os.path.join(HERE, "..", "sealed_hang", "common")
SYL = "ka ri mo su te na vo li pe zu ga ho bi ne ru so ta mi ko re".split()
GEN_VERSION = 1


def word(r, n=2):
    return "".join(r.choice(SYL) for _ in range(n))


class Prog:
    def __init__(self, r):
        self.r, self.funcs, self.roles, self.used = r, [], [], set()

    def ident(self, base):
        while True:
            n = f"{word(self.r)}_{word(self.r)}" if self.r.random() < 0.5 else word(self.r, 3)  # never derived from the kind
            if n not in self.used:
                self.used.add(n); return n

    def loop(self, body, var="n"):
        if self.r.random() < 0.5:
            return f"  for (int {var} = 0;; {var}++) {{\n{body}  }}\n"
        return f"  int {var} = 0;\n  while (1) {{\n{body}    {var}++;\n  }}\n"

    def add(self, kind, src):
        name = self.ident(kind[:3])
        self.funcs.append((kind, name, src.replace("FN", name)))
        return name


def node_src(p, kind, a):
    """C source of one role. `a` = dict of arguments; argv: <fn> <me> [peer] [...]."""
    m, c, rv = p.ident("m"), p.ident("c"), p.ident("rid")
    us = p.r.choice([5000, 10000, 20000, 50000])
    if kind == "pingpong":  # send to next first, then serve one request
        body = f"    qd_send({c}, n);\n    int {rv} = qd_receive(at->chid, &{m});\n    if ({rv} > 0) MsgReply({rv}, EOK, &n, sizeof n);\n    qd_tick(me, n);\n"
        return f"static void FN(const char *me, const char *nx) {{\n  name_attach_t *at = qd_attach(me);\n  int {c} = qd_open(nx);\n  qd_msg_t {m};\n" + p.loop(body) + "}\n"
    if kind in ("starter", "waiter"):  # client loop: request, wait for reply
        body = f"    qd_send({c}, n);\n    qd_tick(me, n);\n    usleep({us});\n"
        att = "  qd_attach(me);\n" if kind == "starter" else ""
        return f"static void FN(const char *me, const char *nx) {{\n{att}  int {c} = qd_open(nx);\n" + p.loop(body) + "}\n"
    if kind == "relay":  # serve a request by asking the next one first
        body = f"    int {rv} = qd_receive(at->chid, &{m});\n    if ({rv} <= 0) continue;\n    int r = qd_send({c}, {m}.app.v);\n    MsgReply({rv}, EOK, &r, sizeof r);\n"
        return f"static void FN(const char *me, const char *nx) {{\n  name_attach_t *at = qd_attach(me);\n  int {c} = qd_open(nx);\n  qd_msg_t {m};\n" + p.loop(body) + "}\n"
    if kind == "leaf":
        body = f"    int {rv} = qd_receive(at->chid, &{m});\n    if ({rv} > 0) MsgReply({rv}, EOK, &{m}.app.v, sizeof {m}.app.v);\n"
        return f"static void FN(const char *me, const char *nx) {{\n  (void)nx;\n  name_attach_t *at = qd_attach(me);\n  qd_msg_t {m};\n" + p.loop(body) + "}\n"
    if kind == "slow":  # legit long wait: answers after a pause
        body = f"    int {rv} = qd_receive(at->chid, &{m});\n    if ({rv} <= 0) continue;\n    usleep({a['pause']});\n    MsgReply({rv}, EOK, &{m}.app.v, sizeof {m}.app.v);\n"
        return f"static void FN(const char *me, const char *nx) {{\n  (void)nx;\n  name_attach_t *at = qd_attach(me);\n  qd_msg_t {m};\n" + p.loop(body) + "}\n"
    if kind == "idle":
        body = f"    qd_receive(at->chid, &{m});\n    qd_tick(me, n);\n"
        return f"static void FN(const char *me, const char *nx) {{\n  (void)nx;\n  name_attach_t *at = qd_attach(me);\n  qd_msg_t {m};\n" + p.loop(body) + "}\n"
    if kind == "feeder":
        body = f"    MsgSendPulse({c}, -1, 1, n);\n    usleep({a['every']});\n"
        return f"static void FN(const char *me, const char *nx) {{\n  (void)me;\n  int {c} = qd_open(nx);\n" + p.loop(body) + "}\n"
    if kind == "pserver":  # priority server: channel id published in a file
        body = f"    int {rv} = qd_receive(ch, &{m});\n    if ({rv} <= 0) continue;\n    volatile long x = 0; for (long i = 0; i < {a['work']}; i++) x += i;\n    MsgReply({rv}, EOK, &{m}.app.v, sizeof {m}.app.v);\n"
        return (f"static void FN(const char *me, const char *nx) {{\n  (void)nx;\n  setprio(0, {a['lo']});\n  int ch = ChannelCreate({a['flags']});\n"
                f"  char path[64]; snprintf(path, sizeof path, \"/tmp/%s.id\", me);\n  FILE *f = fopen(path, \"w\"); fprintf(f, \"%d %d\\n\", getpid(), ch); fclose(f);\n  qd_msg_t {m};\n" + p.loop(body) + "}\n")
    if kind == "pclient":
        body = f"    qd_send({c}, n);\n    qd_tick(me, n);\n    usleep({us});\n"
        return (f"static void FN(const char *me, const char *nx) {{\n  setprio(0, {a['hi']});\n  char path[64]; snprintf(path, sizeof path, \"/tmp/%s.id\", nx);\n"
                f"  int pid = 0, ch = 0; FILE *f = NULL;\n  for (int i = 0; i < 100 && !f; i++) {{ f = fopen(path, \"r\"); if (!f) usleep(50000); }}\n"
                f"  if (!f || fscanf(f, \"%d %d\", &pid, &ch) != 2) exit(1);\n  fclose(f);\n  int {c} = ConnectAttach(0, pid, ch, _NTO_SIDE_CHANNEL, 0);\n" + p.loop(body) + "}\n")
    if kind == "hog":
        return (f"static void *spin_{p.ident('s')}(void *x) {{ time_t e = time(NULL) + (long)x; volatile long k = 0; while (time(NULL) < e) k++; return NULL; }}\n"
                f"static void FN(const char *me, const char *nx) {{\n  (void)me; (void)nx;\n  setprio(0, {a['mid']});\n  pthread_t t[2];\n"
                f"  for (int i = 0; i < 2; i++) pthread_create(&t[i], NULL, SPIN, (void *)20L);\n  for (int i = 0; i < 2; i++) pthread_join(t[i], NULL);\n}}\n")
    raise ValueError(kind)


def draw(seed: int) -> dict:
    r = random.Random(seed)
    kind = r.choices(["deadlock", "priority_chain", "none"], [0.45, 0.25, 0.30])[0]
    p = Prog(r)
    procs, label = [], {"kind": kind, "seed": seed, "gen_version": GEN_VERSION}
    names = set()

    def role():
        while True:
            n = word(r, r.choice([2, 3]))
            if n not in names:
                names.add(n); return n

    budget = r.randint(2, 6)
    if kind == "deadlock":
        L = r.randint(2, min(4, budget))
        ring = [role() for _ in range(L)]
        style = r.choice(["all_send", "relays"])
        if style == "all_send":
            for i, me in enumerate(ring):
                procs.append(("pingpong", me, ring[(i + 1) % L], True))
            label.update(members=ring, culprit=f"the synchronous qd_send/MsgSend each member makes to the next ({' -> '.join(ring)} -> {ring[0]}) before serving its own channel",
                         fix="notify with MsgSendPulse or serve the channel on another thread, so no member blocks on one that is itself sending", loop_logs=[ring[0]])
        else:
            procs.append(("starter", ring[0], ring[1], True))
            for i in range(1, L):
                procs.append(("relay", ring[i], ring[(i + 1) % L], False))
            label.update(members=ring, culprit=f"{ring[-1]} forwards to {ring[0]} with a synchronous send while {ring[0]} waits for its own reply (the edge that closes the cycle)",
                         fix=f"{ring[-1]} answers without calling back {ring[0]} synchronously (reply first / MsgSendPulse)", loop_logs=[ring[0]])
        extra = r.randint(0, max(0, budget - L))
        for _ in range(min(extra, 2)):
            w = role(); procs.append(("waiter", w, r.choice(ring), True))
            label.setdefault("behind", []).append(w)
            label["loop_logs"].append(w)
        used = L + min(extra, 2)
    elif kind == "priority_chain":
        srv, cli = role(), role()
        lo, hi, mid = r.randint(3, 8), r.randint(25, 40), r.randint(15, 22)
        procs += [("pserver", srv, "", False, {"lo": lo, "flags": "_NTO_CHF_FIXED_PRIORITY", "work": r.choice([1000000, 2000000, 4000000])}),
                  ("pclient", cli, srv, True, {"hi": hi}), ("hog", role(), "", False, {"mid": mid})]
        label.update(members=[cli, srv], culprit=f"{srv} creates its channel with _NTO_CHF_FIXED_PRIORITY, so it does not inherit {cli}'s priority",
                     fix="ChannelCreate without _NTO_CHF_FIXED_PRIORITY (priority inheritance)", loop_logs=[cli], prio_client=cli)
        used = 2
    else:
        L = r.randint(1, min(3, budget))
        chain = [role() for _ in range(L + 1)]
        procs.append(("starter", chain[0], chain[1], True))
        for i in range(1, L):
            procs.append(("relay", chain[i], chain[i + 1], False))
        procs.append(("leaf", chain[-1], "", False))
        label.update(members=[], culprit=None, fix=None, loop_logs=[chain[0]])
        used = L + 1
    room = (6 - used) // 2
    for _ in range(min(room, r.randint(0 if kind != "none" else 1, 2))):
        if r.random() < 0.5:
            s, c = role(), role()
            procs += [("slow", s, "", False, {"pause": r.choice([700000, 1000000, 1500000])}), ("waiter", c, s, True)]
            label.setdefault("decoys", []).append(f"{c} waits on slow {s}")
            if kind == "none":
                label["loop_logs"].append(c)
        else:
            w, f = role(), role()
            procs += [("idle", w, "", True), ("feeder", f, w, False, {"every": r.choice([200000, 300000, 500000])})]
            label.setdefault("decoys", []).append(f"{w} idle, fed pulses by {f}")
    return {"label": label, "procs": procs, "prog": p}


def render(seed: int, out_root: str) -> tuple[str, dict]:
    d = draw(seed)
    p, procs, label = d["prog"], d["procs"], d["label"]
    sid = "s" + hashlib.sha256(f"qd-gen-{seed}".encode()).hexdigest()[:6]
    exe = word(p.r, 3)
    table = {}
    for pr in procs:
        kind = pr[0]
        if kind not in table:
            src = node_src(p, kind, pr[4] if len(pr) > 4 else {})
            fn = p.add(kind, src)
            if kind == "hog":
                spin = src.split("static void *")[1].split("(")[0]
                p.funcs[-1] = (kind, fn, p.funcs[-1][2].replace("SPIN", spin))
            table[kind] = fn
        else:  # different arguments for a second process of the same kind: keep the first body (args are per kind)
            pass
    p.r.shuffle(p.funcs)
    disp = "\n".join(f"  if (!strcmp(argv[1], \"{fn}\")) {fn}(argv[2], argc > 3 ? argv[3] : \"\");" for _, fn, _ in p.funcs)
    src = ('#include "../common/qd.h"\n#include <pthread.h>\n#include <time.h>\n\n' + "\n".join(f[2] for f in p.funcs) +
           f"\nint main(int argc, char **argv) {{\n  if (argc < 3) return 2;\n{disp}\n  return 2;\n}}\n")
    os.makedirs(os.path.join(out_root, sid), exist_ok=True)
    open(os.path.join(out_root, sid, f"{exe}.c"), "w").write(src)
    order = procs[:]
    p.r.shuffle(order)
    hogs = [x for x in order if x[0] == "hog"]
    lines = ["#!/bin/sh"]
    for pr in [x for x in order if x[0] in ("pserver", "slow", "leaf", "idle")] + [x for x in order if x[0] not in ("pserver", "slow", "leaf", "idle", "hog")]:
        kind, me, nx, ticks = pr[:4]
        log = f"/tmp/d0{me}.log" if ticks else f"/tmp/q_{me}.err"
        lines.append(f"/var/qd/{sid}/{exe} {table[kind]} {me} {nx or '-'} > {log} 2>&1 &")
    lines.append("sleep 1")
    if hogs:
        lines.append(f": > /tmp/d0{label['prio_client']}.log")
        lines.append(f"/var/qd/{sid}/{exe} {table['hog']} {hogs[0][1]} - > /dev/null 2>&1 &")
    lines.append("sleep 4")
    open(os.path.join(out_root, sid, "run.sh"), "w").write("\n".join(lines) + "\n")
    label["procs"] = len([x for x in procs if x[0] != "hog"])
    return sid, label


POOLS = json.load(open(os.path.join(HERE, "seeds.json")))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pool", choices=["dev", "heldout"], required=True); ap.add_argument("--out", required=True)
    a = ap.parse_args()
    if os.path.exists(a.out):
        shutil.rmtree(a.out)
    os.makedirs(a.out)
    shutil.copytree(COMMON, os.path.join(a.out, "common"))
    labels = {}
    for seed in POOLS[a.pool]:
        sid, lab = render(seed, a.out)
        labels[sid] = lab
    json.dump(labels, open(os.path.join(a.out, "labels.json"), "w"), indent=1)
    kinds = {}
    for v in labels.values():
        kinds[v["kind"]] = kinds.get(v["kind"], 0) + 1
    print(a.out, len(labels), "scenarios", kinds)


if __name__ == "__main__":
    main()
