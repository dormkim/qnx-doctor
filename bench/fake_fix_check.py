"""Attack the hang verifier on the real target with shortcut «fixes» (dev pool only — never held-out or sealed).

For one deadlock ring (every member sends first) and one priority chain from the dev pool, build fixes by plain
text edits, apply each to a fresh copy, rebuild with qcc, boot, rerun, and judge with hangdoctor.verdict:
  real    pulse back / channel without _NTO_CHF_FIXED_PRIORITY            -> must be fixed
  fake    rewire run.sh, one member stops sending, client stops sending,
          CPU-load threads removed, CPU load lowered                       -> must be rejected
Prints one row per fix: expected, fixed, alive-again (liveness only), reasons. States only (QNX licence 4.6(i)).

  python3 bench/fake_fix_check.py --pool /tmp/qd_dev --out runs/fake_fix.jsonl

Gates before sealed v6 (2026-11-22, bench/V6_PLAN.md section 4.2):
  --tick-first          only the ring, with every member's TICK moved in front of its send (a copy; the pool is not
                        edited), plus fakes for the rule that reads the rerun's second TICK count
  --checks ID[,ID...]   the self-send and mutex harness checks (CHECKS below); --pool is then tests/harness_checks
A fake counts as «ok» only if it was rejected by a finished rerun or by a static structure rule: a build failure or
a failed boot is not a rejection.

  python3 bench/fake_fix_check.py --pool DEV --tick-first --out runs/tick_first.jsonl
  python3 bench/fake_fix_check.py --pool tests/harness_checks --checks ss01,mx01 --out runs/checks.jsonl
"""
import argparse
import json
import os
import re
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from qnx_doctor import hang  # noqa: E402
from qnx_doctor.hangdoctor import named, verdict  # noqa: E402
from qnx_doctor.structure import STATIC  # noqa: E402


def src(pool, sid):
    c = [f for f in os.listdir(os.path.join(pool, sid)) if f.endswith(".c")][0]
    return f"{sid}/{c}", open(os.path.join(pool, sid, c)).read(), open(os.path.join(pool, sid, "run.sh")).read()


def ring_fixes(pool, sid, lab):
    path, s, run = src(pool, sid)
    send = re.search(r"    qd_send\((\w+), n\);\n    int \w+ = qd_receive", s)
    c = send[1]
    line = f"    qd_send({c}, n);"
    first = lab["members"][0]
    peer_line = next(l for l in run.splitlines() if f" {first} " in l and l.startswith("/var/qd"))
    return [("real: pulse to the next member", True, [{"type": "edit_file", "path": path, "find": line, "replace": f"    MsgSendPulse({c}, -1, 1, n);"}]),
            ("fake: run.sh rewired", False, [{"type": "edit_file", "path": f"{sid}/run.sh", "find": peer_line, "replace": peer_line.replace(f" {first} ", f" {first}x ", 1)}]),
            ("fake: one member stops sending", False, [{"type": "edit_file", "path": path, "find": line, "replace": f"    if (strcmp(me, \"{first}\")) qd_send({c}, n);"}]),
            ("fake: every member stops sending", False, [{"type": "edit_file", "path": path, "find": line, "replace": f"    (void){c};"}])]


def chain_fixes(pool, sid, lab):
    path, s, _ = src(pool, sid)
    out = [("real: channel inherits the client's priority", True,
            [{"type": "edit_file", "path": path, "find": "ChannelCreate(_NTO_CHF_FIXED_PRIORITY)", "replace": "ChannelCreate(0)"}])]
    out.append(("fake: CPU-load threads removed", False, [{"type": "edit_file", "path": path, "find": "for (int i = 0; i < 2; i++) pthread_create",
                                                              "replace": "for (int i = 0; i < 0; i++) pthread_create"}]))
    mid = re.search(r"setprio\(0, (\d+)\);\n  pthread_t t\[2\]", s)
    out.append(("fake: CPU load lowered", False, [{"type": "edit_file", "path": path, "find": mid[0], "replace": mid[0].replace(f"setprio(0, {mid[1]})", "setprio(0, 1)")}]))
    cli = re.search(r"    qd_send\((\w+), n\);\n    qd_tick\(me, n\);\n    usleep", s)
    if cli and "ConnectAttach" in s[max(0, cli.start() - 600):cli.start()]:
        out.append(("fake: client stops sending", False, [{"type": "edit_file", "path": path, "find": cli[0], "replace": cli[0].replace(f"qd_send({cli[1]}, n);", f"(void){cli[1]};")}]))
    return out


def tick_first(pool, sid, into):
    """A copy of the ring in which each member prints its TICK before it sends."""
    shutil.copytree(os.path.join(pool, "common"), os.path.join(into, "common"))
    shutil.copytree(os.path.join(pool, sid), os.path.join(into, sid))
    path, s, _ = src(into, sid)
    tick = "    qd_tick(me, n);\n"
    send = re.search(r"    qd_send\((\w+), n\);\n    int \w+ = qd_receive", s)
    if not send or s.count(tick) != 1:
        raise LookupError(f"{sid}: not a plain send-first ring")
    s = s.replace(tick, "")
    s = s.replace(send[0], tick + send[0], 1)
    with open(os.path.join(into, path), "w") as f:
        f.write(s)
    return into


def tick_first_fixes(pool, sid, lab):
    path, s, _ = src(pool, sid)
    c = re.search(r"    qd_send\((\w+), n\);\n    int \w+ = qd_receive", s)[1]
    line, pulse = f"    qd_send({c}, n);", f"    MsgSendPulse({c}, -1, 1, n);"

    def put(text):
        return [{"type": "edit_file", "path": path, "find": line, "replace": text}]
    return ring_fixes(pool, sid, lab) + [
        ("fake: more TICKs, same cycle", False, put(f"    for (int k = 0; k < 4; k++) qd_tick(me, n);\n{line}")),
        ("fake: one more TICK, then stopped", False, put(f"    if (n >= 1) for (;;) sleep(1);\n{pulse}")),
        ("fake: more TICKs, then stopped again", False, put(f"    if (n >= 5) for (;;) sleep(1);\n{pulse}")),
        ("fake: TICKs go on, no message at all", False, put(f"    (void){c}; usleep(100000); continue;")),
        ("fake: TICKs go on, messages stop after a few rounds", False,
         put(f"    if (n >= 5) {{ usleep(100000); continue; }}\n{pulse}"))]


def edit(path, find, replace):
    return {"type": "edit_file", "path": path, "find": find, "replace": replace}


# Hand-written dev checks: scenario -> [(fix, must be fixed, actions)].
SS01 = "ss01/selfpost.c"
MX01 = "mx01/ledger.c"
MX02 = "mx02/desk.c"
MX02_ORDER = [edit(MX02, """    pthread_mutex_lock(&state);
    usleep(50000);
    pthread_mutex_lock(&queue);
    pthread_mutex_unlock(&queue);
    pthread_mutex_unlock(&state);""", """    pthread_mutex_lock(&queue);
    usleep(50000);
    pthread_mutex_lock(&state);
    pthread_mutex_unlock(&state);
    pthread_mutex_unlock(&queue);""")]
CHECKS = {
    "ss01": [
        ("real: a second thread receives", True, [
            edit(SS01, "int main(void) {", """static int own;
static void *take(void *unused) {
  (void)unused;
  qd_msg_t m;
  for (;;) { int r = qd_receive(own, &m); if (r > 0) MsgReply(r, EOK, &m.app.v, sizeof m.app.v); }
  return NULL;
}
int main(void) {"""),
            edit(SS01, "  for (int n = 0;; n++) {\n    qd_tick(",
                 "  pthread_t t; own = chid; pthread_create(&t, NULL, take, NULL);\n  for (int n = 0;; n++) {\n    qd_tick(")]),
        ("fake: the send is deleted", False, [edit(SS01, "    qd_send(coid, n);", "    (void)coid;")])],
    "ss02": [],
    "ss03": [],
    "mx01": [
        ("real: one lock order", True, [edit(MX01, '{ "d0audit", &indx, &book }', '{ "d0audit", &book, &indx }')]),
        ("fake: one worker is removed", False,
         [edit(MX01, "for (int i = 0; i < 2; i++) pthread_create", "for (int i = 0; i < 1; i++) pthread_create")]),
        ("fake: the second lock is deleted", False,
         [edit(MX01, "    pthread_mutex_lock(j->second);\n    pthread_mutex_unlock(j->second);\n", "")])],
    "mx02": [
        ("real: one lock order", True, MX02_ORDER),
        ("fake: lock order and one worker removed", False,
         MX02_ORDER + [edit(MX02, "  pthread_create(&t[2], NULL, flusher, NULL);\n", "  (void)flusher;\n")])],
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pool", required=True); ap.add_argument("--out", required=True); ap.add_argument("--only")
    ap.add_argument("--tick-first", action="store_true"); ap.add_argument("--checks")
    a = ap.parse_args()
    if a.checks:
        return run([(a.pool, sid, CHECKS[sid]) for sid in a.checks.split(",")], a.out)
    labels = json.load(open(os.path.join(a.pool, "labels.json")))
    ring = next(k for k, v in labels.items() if v["kind"] == "deadlock" and "each member makes" in (v.get("culprit") or ""))
    chain = next(k for k, v in labels.items() if v["kind"] == "priority_chain")
    if a.tick_first:
        copy = tempfile.mkdtemp(prefix="qd-tick-first-")
        try:
            tick_first(a.pool, ring, copy)
            return run([(copy, ring, tick_first_fixes(copy, ring, labels[ring]))], a.out)
        finally:
            shutil.rmtree(copy, ignore_errors=True)
    run([(a.pool, sid, maker(a.pool, sid, labels[sid])) for sid, maker in ((ring, ring_fixes), (chain, chain_fixes))
         if not a.only or a.only in (sid, maker.__name__)], a.out)


def rejected_properly(err, res) -> bool:
    """A fake is rejected by a static structure rule or by a finished rerun, never by a harness failure."""
    return err.startswith(STATIC) if err else bool(res.get("ok"))


def run(cases, path):
    with open(path, "w") as out:
        def emit(row):
            out.write(json.dumps(row) + "\n"); out.flush()
            print(json.dumps(row), flush=True)

        for pool, sid, fixes in cases:
            work = hang.prepare(os.path.join(pool, sid))
            first = hang.observe(work, sid)
            shutil.rmtree(work, ignore_errors=True)
            if not first.get("ok"):
                emit({"id": sid, "fix": None, "stage": first.get("stage"), "ok": False, "log": (first.get("log") or "")[-300:]})
                continue
            detected, note = named(first)
            emit({"id": sid, "fix": None, "ok": True, "first": first["judge"]["kind"], "detected": detected, "note": note,
                  "progress": first.get("progress"), "ticks": first.get("ticks"), "alive": first.get("alive"),
                  "structure": first.get("structure")})
            for name, want, acts in fixes:
                fixed, err = hang.apply_fix(os.path.join(pool, sid), acts)
                res = {} if err else hang.observe(fixed, sid)
                v = {"fixed": False, "live": None, "structure": [err]} if err else verdict(first, res)
                v["rerun"] = {"stage": res.get("stage"), "ok": res.get("ok"), "kind": (res.get("judge") or {}).get("kind"),
                              "ticks": res.get("ticks"), "progress": res.get("progress"), "alive": res.get("alive"),
                              "log": (res.get("log") or "")[-300:]}
                shutil.rmtree(fixed, ignore_errors=True)
                ok = v["fixed"] == want and (want or rejected_properly(err, res))
                emit({"id": sid, "fix": name, "expected_fixed": want, **v, "ok": ok})


if __name__ == "__main__":
    main()
