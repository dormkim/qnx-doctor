"""harness_check.py <scenario dir>: build, boot and observe one harness-check scenario once; print TICK counts and the
code judgment. For tests/harness_checks only (never a benchmark set). Uses the qnx_doctor package of the current dir."""
import json, os, shutil, sys

sys.path.insert(0, os.getcwd())  # the qnx_doctor of the checkout you run it from (main vs a fix branch)
from qnx_doctor import hang  # noqa: E402

scen = sys.argv[1]
work = hang.prepare(scen)
name = scen.rstrip("/").split("/")[-1]
obs = hang.observe(work, name)
shutil.rmtree(work, ignore_errors=True)
print(json.dumps({"ok": obs.get("ok"), "stage": obs.get("stage"), "ticks": obs.get("ticks"), "graph": obs.get("graph"),
                  "log": obs.get("log") if not obs.get("ok") else None}, ensure_ascii=False))
