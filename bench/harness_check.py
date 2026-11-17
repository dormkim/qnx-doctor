"""harness_check.py <scenario dir> [--twice]: build, boot and observe one harness-check scenario once; print TICK
counts, the progress between the two counts of the same boot, and the code's judgment. For tests/harness_checks only
(never a benchmark set). Uses the qnx_doctor package of the current dir.

  --twice   the reproducibility-check paths instead (bench/repro_v3.observe_twice), each in its own boot: the v3 one
            (a second observer woken after check.sh) and the v4 one (--same-boot: snap's TICKS and TICKS2). Prints
            whether each second count came back (v3 lost it on every priority-chain scenario; tests/harness_checks/oc01)."""
import json
import os
import shutil
import sys

sys.path.insert(0, os.getcwd())  # the qnx_doctor of the checkout you run it from (main vs a fix branch)
sys.path.insert(0, os.path.join(os.getcwd(), "bench"))
from qnx_doctor import hang  # noqa: E402
from qnx_doctor import hangdoctor  # noqa: E402

scen = sys.argv[1]
if "--twice" in sys.argv:
    import repro_v3  # noqa: E402
    for path, same in (("second observer (v3)", False), ("same boot (v4)", True)):
        obs = repro_v3.observe_twice(scen, same_boot=same)
        print(json.dumps({"path": path, "error": obs.get("error"), "snap": obs.get("snap"), "later": obs.get("later"),
                          "second_count_back": obs.get("later") is not None}, ensure_ascii=False), flush=True)
    sys.exit(0)
work = hang.prepare(scen)
name = scen.rstrip("/").split("/")[-1]
obs = hang.observe(work, name)
shutil.rmtree(work, ignore_errors=True)
out = {"ok": obs.get("ok"), "stage": obs.get("stage"), "log": obs.get("log") if not obs.get("ok") else None}
if obs.get("ok"):
    detected, note = hangdoctor.named(obs)
    out.update({"ticks": obs["ticks"], "progress": obs.get("progress"), "state_only": obs.get("state_only"),
                "judge": obs["judge"]["kind"], "detected": detected, "note": note, "graph": obs["graph"]})
print(json.dumps(out, ensure_ascii=False))
