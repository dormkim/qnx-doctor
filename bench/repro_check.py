"""Does each sealed scenario actually fail on this machine? Prints only yes/no + exit code class.

Deliberately does NOT print or store the command output: the sealed set must stay unseen until the
single scored run (we may not tune rules/prompts on its error messages).
  python3 bench/repro_check.py tests/sealed > runs/sealed_repro.json
"""
import glob
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from qnx_doctor.doctor import setup  # noqa: E402
from qnx_doctor.runner import run  # noqa: E402


def main(d):
    out = []
    for f in sorted(glob.glob(os.path.join(d, "X*.json"))):
        s = json.load(open(f))
        if "spec" not in s:
            out.append({"id": s["id"], "runnable": False, "status": s.get("status")})
            continue
        work = setup(s)
        try:
            r = run(s["spec"], work)
            out.append({"id": s["id"], "runnable": True, "fails": not r.ok,
                        "kind": "timeout" if r.reason == "timeout" else ("exec_failed" if r.reason == "exec_failed" else "nonzero_or_verify")})
        except Exception as e:  # setup/runner error is itself a reproducibility problem
            out.append({"id": s["id"], "runnable": True, "fails": None, "error": type(e).__name__})
        finally:
            shutil.rmtree(work, ignore_errors=True)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "tests/sealed")
