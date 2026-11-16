#!/usr/bin/env python3
"""Seeded random hang scenarios, generator v2 (QNX 8.0 message passing). v1 (gen.py) stays as sealed.

  python3 tests/gen_hang/gen2.py --pool dev|heldout --out DIR     # DIR/common + one dir per scenario + DIR/labels.json

Why v2 (2026-11-16): on v1 the naive baseline named every kind right from the source alone, and v1 had only one
held-out priority chain. v2 draws more chains and adds axes where the source alone does not tell which hang happens:
  runtime_mode   ring members decide «send first» or «serve first» from a bit mask passed at run time (argument or
                 environment variable); the same source deadlocks or runs depending on run.sh
  confounder     the scenario also holds the other kind of hang in a form that does NOT happen at run time: a
                 fixed-priority server whose CPU load sits below it, or a ring with mixed modes. Their logs carry no
                 TICK, so the logs do not tell which part is stuck
  runtime_prio   server, client and load priorities come from run.sh arguments instead of constants
  timing         (healthy only) a priority chain that clears before the snapshot: the CPU load runs for a short time
  multi_file     the roles are split over 2–3 programs
  indirection    run.sh passes indices; the role names live in a header table
The answer key goes to labels.json OUTSIDE the scenario directories; sources carry no comments and no marker.
"""
import argparse
import hashlib
import json
import os
import random
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
COMMON = os.path.join(HERE, "..", "sealed_hang", "common")
SYL = "ka ri mo su te na vo li pe zu ga ho bi ne ru so ta mi ko re ba di fu ji".split()
GEN_VERSION = 2
SERVERS = ("pserver", "slow", "leaf", "idle", "member")


def word(r, n=2):
    return "".join(r.choice(SYL) for _ in range(n))


class Prog:
    def __init__(self, r):
        self.r, self.used = r, set()

    def ident(self):
        while True:
            n = f"{word(self.r)}_{word(self.r)}" if self.r.random() < 0.5 else word(self.r, 3)
            if n not in self.used:
                self.used.add(n); return n

    def loop(self, body, var="n"):
        if self.r.random() < 0.5:
            return f"  for (int {var} = 0;; {var}++) {{\n{body}  }}\n"
        return f"  int {var} = 0;\n  while (1) {{\n{body}    {var}++;\n  }}\n"


def body_of(p, kind, cfg):
    """C source of one role function FN(me, nx, a, b). `cfg` = per-kind constants drawn by `draw`."""
    m, c, rv = p.ident(), p.ident(), p.ident()
    us = p.r.choice([5000, 10000, 20000, 50000])
    head = "static void FN(const char *me, const char *nx, int a, int b) {\n"
    unused = "  (void)a; (void)b;\n"
    if kind == "member":  # ring member: send first or serve first, decided at run time from bit a of the mask
        mode = f"(b >> a) & 1" if cfg["mode_src"] == "arg" else f"(atoi(getenv(\"{cfg['env']}\") ? getenv(\"{cfg['env']}\") : \"0\") >> a) & 1"
        k = p.ident()
        body = (f"    if ({k}) qd_send({c}, n);\n    int {rv} = qd_receive(at->chid, &{m});\n    if ({rv} > 0) MsgReply({rv}, EOK, &n, sizeof n);\n"
                f"    if (!{k}) qd_send({c}, n);\n    qd_tick(me, n);\n    usleep({us});\n")
        return (head + ("  (void)b;\n" if cfg["mode_src"] != "arg" else "") + f"  name_attach_t *at = qd_attach(me);\n  int {c} = qd_open(nx);\n  qd_msg_t {m};\n  int {k} = {mode};\n" + p.loop(body) + "}\n")
    if kind in ("starter", "waiter"):
        body = f"    qd_send({c}, n);\n    qd_tick(me, n);\n    usleep({us});\n"
        att = "  qd_attach(me);\n" if kind == "starter" else ""
        return head + unused + f"{att}  int {c} = qd_open(nx);\n" + p.loop(body) + "}\n"
    if kind == "relay":
        body = f"    int {rv} = qd_receive(at->chid, &{m});\n    if ({rv} <= 0) continue;\n    int r = qd_send({c}, {m}.app.v);\n    MsgReply({rv}, EOK, &r, sizeof r);\n"
        return head + unused + f"  name_attach_t *at = qd_attach(me);\n  int {c} = qd_open(nx);\n  qd_msg_t {m};\n" + p.loop(body) + "}\n"
    if kind in ("leaf", "slow"):
        pause = f"    usleep({cfg['pause']});\n" if kind == "slow" else ""
        body = f"    int {rv} = qd_receive(at->chid, &{m});\n    if ({rv} <= 0) continue;\n{pause}    MsgReply({rv}, EOK, &{m}.app.v, sizeof {m}.app.v);\n"
        return head + unused + f"  (void)nx;\n  name_attach_t *at = qd_attach(me);\n  qd_msg_t {m};\n" + p.loop(body) + "}\n"
    if kind == "idle":
        body = f"    qd_receive(at->chid, &{m});\n    qd_tick(me, n);\n"
        return head + unused + f"  (void)nx;\n  name_attach_t *at = qd_attach(me);\n  qd_msg_t {m};\n" + p.loop(body) + "}\n"
    if kind == "feeder":
        body = f"    MsgSendPulse({c}, -1, 1, n);\n    usleep({cfg['every']});\n"
        return head + unused + f"  (void)me;\n  int {c} = qd_open(nx);\n" + p.loop(body) + "}\n"
    if kind == "pserver":  # channel id published in a file; priority constant or from argument a
        prio = "a" if cfg["rt_prio"] else str(cfg["lo"])
        body = f"    int {rv} = qd_receive(ch, &{m});\n    if ({rv} <= 0) continue;\n    volatile long x = 0; for (long i = 0; i < {cfg['work']}; i++) x += i;\n    MsgReply({rv}, EOK, &{m}.app.v, sizeof {m}.app.v);\n"
        return (head + "  (void)nx; (void)b;\n" + f"  setprio(0, {prio});\n  int ch = ChannelCreate(_NTO_CHF_FIXED_PRIORITY);\n"
                "  char path[64]; snprintf(path, sizeof path, \"/tmp/%s.id\", me);\n  FILE *f = fopen(path, \"w\"); fprintf(f, \"%d %d\\n\", getpid(), ch); fclose(f);\n"
                f"  qd_msg_t {m};\n" + p.loop(body) + "}\n")
    if kind == "pclient":
        prio = "a" if cfg["rt_prio"] else str(cfg["hi"])
        body = f"    qd_send({c}, n);\n    qd_tick(me, n);\n    usleep({us});\n"
        return (head + "  (void)b;\n" + f"  setprio(0, {prio});\n  char path[64]; snprintf(path, sizeof path, \"/tmp/%s.id\", nx);\n"
                "  int pid = 0, ch = 0; FILE *f = NULL;\n  for (int i = 0; i < 100 && !f; i++) { f = fopen(path, \"r\"); if (!f) usleep(50000); }\n"
                f"  if (!f || fscanf(f, \"%d %d\", &pid, &ch) != 2) exit(1);\n  fclose(f);\n  int {c} = ConnectAttach(0, pid, ch, _NTO_SIDE_CHANNEL, 0);\n" + p.loop(body) + "}\n")
    if kind == "hog":  # CPU load on both CPUs: priority a, for b seconds (both from run.sh)
        spin = p.ident()
        return (f"static void *{spin}(void *x) {{ time_t e = time(NULL) + (long)x; volatile long k = 0; while (time(NULL) < e) k++; return NULL; }}\n"
                + head + f"  (void)me; (void)nx;\n  setprio(0, a);\n  pthread_t t[2];\n  pthread_attr_t at; pthread_attr_init(&at); pthread_attr_setinheritsched(&at, PTHREAD_INHERIT_SCHED);\n"
                f"  for (int i = 0; i < 2; i++) pthread_create(&t[i], &at, {spin}, (void *)(long)b);\n  for (int i = 0; i < 2; i++) pthread_join(t[i], NULL);\n}}\n")
    raise ValueError(kind)


def proc(kind, me, nx="", ticks=False, a=0, b=0, env=None):
    return {"kind": kind, "me": me, "nx": nx, "ticks": ticks, "a": a, "b": b, "env": env}


def ring_mask(r, L, all_first):
    """Distinct bit positions per member, the mask of send-first members, plus noise bits on unused positions."""
    pos = r.sample(range(6), L)
    if all_first:
        first = [True] * L
    else:
        first = [r.random() < 0.5 for _ in range(L)]
        if all(first) or not any(first):
            first[r.randrange(L)] = not first[0]
            if all(first) or not any(first):
                first[0] = not first[0]
    mask = sum(1 << p for p, f in zip(pos, first) if f)
    for q in set(range(6)) - set(pos):
        if r.random() < 0.4:
            mask |= 1 << q
    return pos, first, mask


def add_ring(r, role, procs, L, all_first, ticks, cfg):
    ring = [role() for _ in range(L)]
    pos, first, mask = ring_mask(r, L, all_first)
    env = {cfg["env"]: str(mask)} if cfg["mode_src"] == "env" else None
    for i, me in enumerate(ring):
        procs.append(proc("member", me, ring[(i + 1) % L], ticks, pos[i], mask if not env else 0, env))
    return ring, first


def add_chain(r, role, procs, cfg, ticks, hog_prio, hog_secs):
    srv, cli = role(), role()
    procs += [proc("pserver", srv, a=cfg["lo"]), proc("pclient", cli, srv, ticks, a=cfg["hi"]), proc("hog", role(), a=hog_prio, b=hog_secs)]
    return srv, cli


def draw(seed: int) -> dict:
    r = random.Random(seed)
    kind = r.choices(["deadlock", "priority_chain", "none"], [0.35, 0.40, 0.25])[0]
    p = Prog(r)
    procs, axes, names = [], [], set()
    label = {"kind": kind, "seed": seed, "gen_version": GEN_VERSION}

    def role():
        while True:
            n = word(r, r.choice([2, 3]))
            if n not in names:
                names.add(n); return n

    cfg = {"mode_src": r.choice(["arg", "env"]), "env": word(r, 2).upper() + "_" + word(r, 2).upper(),
           "lo": r.randint(3, 8), "hi": r.randint(25, 40), "mid": None, "work": r.choice([1000000, 2000000, 4000000]),
           "rt_prio": r.random() < 0.5, "pause": r.choice([700000, 1000000, 1500000]), "every": r.choice([200000, 300000, 500000])}
    cfg["mid"] = r.randint(max(cfg["lo"] + 1, 15), 22)
    confound = r.random() < 0.6
    if kind == "deadlock":
        L = r.randint(2, 4)
        if r.random() < 0.6:
            ring, _ = add_ring(r, role, procs, L, True, True, cfg)
            axes.append("runtime_mode")
            label.update(members=ring, cause="send_cycle", loop_logs=list(ring),
                         culprit=f"every ring member is in send-first mode at run time (mask from {cfg['mode_src']}): {' -> '.join(ring)} -> {ring[0]}",
                         fix="notify with MsgSendPulse, serve first in one member, or serve the channel on another thread")
        else:
            ring = [role() for _ in range(L)]
            procs.append(proc("starter", ring[0], ring[1], True))
            for i in range(1, L):
                procs.append(proc("relay", ring[i], ring[(i + 1) % L]))
            label.update(members=ring, cause="send_on_reply_path", loop_logs=[ring[0]],
                         culprit=f"{ring[-1]} forwards to {ring[0]} with a synchronous send while {ring[0]} waits for its own reply",
                         fix=f"{ring[-1]} answers without calling back {ring[0]} synchronously (reply first / MsgSendPulse)")
        for _ in range(r.randint(0, 2)):
            w = role(); procs.append(proc("waiter", w, r.choice(ring), True))
            label.setdefault("behind", []).append(w); label["loop_logs"].append(w)
        if confound:  # a fixed-priority server and a CPU load that is BELOW it: no chain at run time
            add_chain(r, role, procs, cfg, False, r.randint(1, cfg["lo"] - 1), 20)
            axes.append("confounder")
    elif kind == "priority_chain":
        srv, cli = add_chain(r, role, procs, cfg, True, cfg["mid"], 20)
        label.update(members=[cli, srv], cause="fixed_priority_channel", loop_logs=[cli], prio_client=cli,
                     culprit=f"{srv} creates its channel with _NTO_CHF_FIXED_PRIORITY, so it does not inherit {cli}'s priority while a CPU load sits between them",
                     fix="ChannelCreate without _NTO_CHF_FIXED_PRIORITY (priority inheritance)")
        if confound:  # a ring that could deadlock in source, but runs: mixed send-first / serve-first at run time
            add_ring(r, role, procs, r.randint(2, 3), False, False, cfg)
            axes += ["confounder", "runtime_mode"]
    else:
        L = r.randint(1, 3)
        chain = [role() for _ in range(L + 1)]
        procs.append(proc("starter", chain[0], chain[1], True))
        for i in range(1, L):
            procs.append(proc("relay", chain[i], chain[i + 1]))
        procs.append(proc("leaf", chain[-1]))
        label.update(members=[], cause=None, culprit=None, fix=None, loop_logs=[chain[0]])
        extra = r.choice(["mixed_ring", "short_chain", "low_load", "decoys"])
        if extra == "mixed_ring":
            ring, _ = add_ring(r, role, procs, r.randint(2, 3), False, True, cfg)
            axes.append("runtime_mode"); label["loop_logs"] += ring
        elif extra == "short_chain":  # the load runs 2 s; the snapshot comes after it ends
            _, cli = add_chain(r, role, procs, cfg, True, cfg["mid"], 2)
            axes.append("timing"); label["loop_logs"].append(cli); label["prio_client"] = cli
        elif extra == "low_load":
            add_chain(r, role, procs, cfg, False, r.randint(1, cfg["lo"] - 1), 20)
            axes.append("confounder")
    n_app = len([x for x in procs if x["kind"] != "hog"])
    for _ in range(max(0, min(r.randint(0, 2), (8 - n_app) // 2))):
        if r.random() < 0.5:
            s, c = role(), role()
            procs += [proc("slow", s), proc("waiter", c, s, True)]
            label.setdefault("decoys", []).append(f"{c} waits on slow {s}")
            if kind == "none":
                label["loop_logs"].append(c)
        else:
            w, f = role(), role()
            procs += [proc("idle", w, ticks=True), proc("feeder", f, w)]
            label.setdefault("decoys", []).append(f"{w} idle, fed pulses by {f}")
    if cfg["rt_prio"] and any(x["kind"] == "pserver" for x in procs):
        axes.append("runtime_prio")
    if r.random() < 0.5:
        axes.append("multi_file")
    if r.random() < 0.5:
        axes.append("indirection")
    label["axes"] = sorted(set(axes))
    return {"label": label, "procs": procs, "prog": p, "cfg": cfg, "r": r}


def render(seed: int, out_root: str) -> tuple[str, dict]:
    d = draw(seed)
    p, procs, label, cfg, r = d["prog"], d["procs"], d["label"], d["cfg"], d["r"]
    sid = "t" + hashlib.sha256(f"qd-gen2-{seed}".encode()).hexdigest()[:6]
    funcs, table = [], {}
    for pr in procs:
        if pr["kind"] not in table:
            name = p.ident()
            table[pr["kind"]] = name
            funcs.append((pr["kind"], name, body_of(p, pr["kind"], cfg).replace("FN", name, 1)))
    r.shuffle(funcs)
    nfiles = r.randint(2, 3) if "multi_file" in label["axes"] and len(funcs) >= 2 else 1
    nfiles = min(nfiles, len(funcs))
    exes = [p.ident() for _ in range(nfiles)]
    owner = {}
    for i, (kind, name, _) in enumerate(funcs):
        owner[kind] = exes[i % nfiles] if i < nfiles else exes[r.randrange(nfiles)]
    d_out = os.path.join(out_root, sid)
    os.makedirs(d_out, exist_ok=True)
    indirect = "indirection" in label["axes"]
    roles = sorted({x["me"] for x in procs} | {x["nx"] for x in procs if x["nx"]})
    r.shuffle(roles)
    hdr = p.ident() + ".h"
    hdr_src = ("#pragma once\n#include <stdlib.h>\n"
               f"static const char *const {hdr[:-2].upper()}_T[] = {{{', '.join(chr(34) + x + chr(34) for x in roles)}}};\n"
               f"static const char *nm(const char *s) {{ return (s[0] >= '0' && s[0] <= '9') ? {hdr[:-2].upper()}_T[atoi(s)] : s; }}\n")
    if indirect:
        open(os.path.join(d_out, hdr), "w").write(hdr_src)
    for exe in exes:
        mine = [f for f in funcs if owner[f[0]] == exe]
        disp = "\n".join(f"  if (!strcmp(argv[1], \"{fn}\")) {fn}({'nm(argv[2])' if indirect else 'argv[2]'}, "
                         f"argc > 3 ? {'nm(argv[3])' if indirect else 'argv[3]'} : \"\", argc > 4 ? atoi(argv[4]) : 0, argc > 5 ? atoi(argv[5]) : 0);"
                         for _, fn, _ in mine)
        src = ('#include "../common/qd.h"\n#include <pthread.h>\n#include <time.h>\n' + (f'#include "{hdr}"\n' if indirect else "") + "\n" +
               "\n".join(f[2] for f in mine) + f"\nint main(int argc, char **argv) {{\n  if (argc < 3) return 2;\n{disp}\n  return 2;\n}}\n")
        open(os.path.join(d_out, f"{exe}.c"), "w").write(src)

    def ref(x):
        return str(roles.index(x)) if indirect and x else (x or "-")

    order = procs[:]
    r.shuffle(order)
    lines = ["#!/bin/sh"]
    first = [x for x in order if x["kind"] in SERVERS and x["kind"] != "member"]
    rest = [x for x in order if x["kind"] not in SERVERS and x["kind"] != "hog"]
    ring = [x for x in order if x["kind"] == "member"]
    for x in first + ring + rest:
        log = f"/tmp/d0{x['me']}.log" if x["ticks"] else f"/tmp/q_{x['me']}.err"
        env = "".join(f"{k}={v} " for k, v in (x["env"] or {}).items())
        args = [table[x["kind"]], ref(x["me"]), ref(x["nx"])]
        if x["kind"] in ("member", "pserver", "pclient"):
            args += [str(x["a"]), str(x["b"])] if x["kind"] == "member" else ([str(x["a"])] if cfg["rt_prio"] else [])
        lines.append(f"{env}/var/qd/{sid}/{owner[x['kind']]} {' '.join(args)} > {log} 2>&1 &")
    lines.append("sleep 1")
    for x in order:
        if x["kind"] == "pclient" and x["ticks"]:
            lines.append(f": > /tmp/d0{x['me']}.log")
    for x in order:
        if x["kind"] == "hog":
            lines.append(f"/var/qd/{sid}/{owner['hog']} {table['hog']} {ref(x['me'])} - {x['a']} {x['b']} > /dev/null 2>&1 &")
    lines.append("sleep 4")
    open(os.path.join(d_out, "run.sh"), "w").write("\n".join(lines) + "\n")
    label["procs"] = len([x for x in procs if x["kind"] != "hog"])
    label["files"] = nfiles
    return sid, label


POOLS = json.load(open(os.path.join(HERE, "seeds2.json")))


def labels_hash(labels: dict) -> str:
    return hashlib.sha256(json.dumps(labels, sort_keys=True).encode()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pool", choices=["dev", "heldout"], required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--hash-only", action="store_true", help="print the answer-key hash, not the kinds")
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
    if a.hash_only:
        print(a.out, len(labels), "scenarios, labels sha256", labels_hash(labels))
        return
    kinds = {}
    for v in labels.values():
        kinds[v["kind"]] = kinds.get(v["kind"], 0) + 1
    print(a.out, len(labels), "scenarios", kinds, "labels sha256", labels_hash(labels))


if __name__ == "__main__":
    main()
