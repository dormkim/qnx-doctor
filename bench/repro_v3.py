"""Sealed v3 reproducibility check (README rule 2), before the single scored run: does each UNMODIFIED scenario do what
its label's `expect` says (per loop role: stops / ticks / any)? No doctor, no AI, no wait-graph judgment is printed.

The TICK count of check.sh is a total at the snapshot, so a loop that ticked and then hung still shows N > 0. Here a
second observer (the same snap, started before the scenario so it is already in memory, woken with the builtin kill)
counts again a few seconds after check.sh: «ticks» = the count grew, «stops» = it did not. Prints per scenario only:
agree or not, the observed counts per role, and on a disagreement the expected word, to write the exclusion reason.
States only (QNX licence 4.6(i)).

  python3 bench/repro_v3.py POOL LABELS.json OUT.json [--retry-missing]
  python3 bench/repro_v3.py POOL LABELS.json OUT.json --same-boot      (for sealed v4 and later)

--same-boot (2026-11-17, after v3, before v4): no second observer. The two counts are snap's own TICKS and TICKS2 of
the same check.sh run (snap.c). Why: under a CPU load above the disk driver the second observer was woken but hung
after its fork, before pidin printed anything, while check.sh's own observer had worked a moment earlier (harness
check oc01, `bench/harness_check.py tests/harness_checks/oc01 --twice`; v3 excluded q02, q06, q09, q21 that way). The
first observer is the path every arm's observation uses, so the check now measures what the arms see.
"""
import json
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from qnx_doctor import hang  # noqa: E402
from qnx_doctor import waitgraph as wg  # noqa: E402
from qnx_doctor.runner import base_env, sdp_env  # noqa: E402

LATER_S = 3
EARLY_TIMER_S = 20  # every v3 run.sh sleeps 4 s; check.sh's snapshot is done well before this


def _counts(text):
    return wg.split_check(text)[1] if "=== TICKS ===" in text else None


def observe_twice(scen, early_timer=False, same_boot=False):
    name = os.path.basename(os.path.normpath(scen))
    env = sdp_env(base_env())
    work = hang.prepare(scen)
    try:
        ok, log = hang.build(work, name, env)
        if not ok:
            return {"error": "build failed"}
        ok, vm, _ = hang.image(work, env)
        if not ok:
            return {"error": "image failed"}
        cmd = (f"/var/qd/hi /bin/sh -c '/var/qd/snap & s=$!; /var/qd/check.sh {name}; sleep {LATER_S}; "
               f"kill -USR1 $s; wait $s; echo QDLATER'")
        if early_timer:  # retry (2026-11-17, first pass): `sleep` loaded from disk AFTER the scenario can be starved like
            # the old observer (snap.c); here the timer is forked and loaded BEFORE the scenario starts.
            cmd = (f"/var/qd/hi /bin/sh -c '/var/qd/snap & s=$!; (sleep {EARLY_TIMER_S}; kill -USR1 $s) & "
                   f"/var/qd/check.sh {name}; wait $s; echo QDLATER'")
        if same_boot:  # wins over early_timer: no second observer at all
            cmd = f"/var/qd/hi /var/qd/check.sh {name}"
        rc, out = hang._sh(["qd-target-exec", vm, cmd], vm, dict(env, QD_EXEC_TIMEOUT="90"), timeout=1500)
        if "QDDONE" not in out:
            return {"error": "target run did not finish"}
        if same_boot:
            return {"snap": _counts(out), "later": wg.tick_counts(out, "TICKS2"), "method": "same boot (TICKS, TICKS2)"}
        first, later = out.split("QDDONE", 1)
        return {"snap": _counts(first), "later": _counts(later) if "QDLATER" in later else None}
    finally:
        shutil.rmtree(work, ignore_errors=True)


def _get(counts, role):
    for k in (role.rsplit("/", 1)[-1].removesuffix(".log"), "d0" + role.rsplit("/", 1)[-1].removesuffix(".log")):
        if counts and k in counts:
            return counts[k]
    return None


def check(expect, obs):
    """-> (agree, reasons). A role whose log is missing, or no second count, is a disagreement with a reason."""
    if obs.get("error"):
        return False, [obs["error"]]
    if obs.get("later") is None:
        return False, ["second count missing (observer did not report)"]
    why = []
    for role, want in expect.items():
        if role.startswith("_") or want == "any":
            continue
        a, b = _get(obs["snap"], role), _get(obs["later"], role)
        if a is None or b is None:
            why.append(f"{role}: log not found (expected {want})")
            continue
        grew = b > a
        if want == "stops" and grew:
            why.append(f"{role}: expected stops, kept ticking ({a} -> {b})")
        elif want == "ticks" and not grew:
            why.append(f"{role}: expected ticks, did not grow ({a} -> {b})")
    return not why, why


def main(pool, labels_path, out_path):
    labels = {k: v for k, v in json.load(open(labels_path)).items() if not k.startswith("_")}
    done = json.load(open(out_path)) if os.path.exists(out_path) else {}
    retry = "--retry-missing" in sys.argv  # second pass: only scenarios whose second count was missing
    same = "--same-boot" in sys.argv
    for sid in sorted(labels):
        if sid in done and not (retry and done[sid].get("later") is None):
            continue
        if retry:
            done[sid + "#first_pass"] = done[sid]
        obs = observe_twice(os.path.join(pool, sid), early_timer=retry, same_boot=same)
        agree, why = check(labels[sid].get("expect", {}), obs)
        done[sid] = {"agree": agree, "why": why, "snap": obs.get("snap"), "later": obs.get("later"), "error": obs.get("error"),
                     "method": obs.get("method") or ("early timer 20 s" if retry else "sleep 3 after check.sh")}
        json.dump(done, open(out_path, "w"), indent=1)
        print(sid, "agree" if agree else "DISAGREE " + "; ".join(why), flush=True)


if __name__ == "__main__":
    main(*sys.argv[1:4])
