"""`qnx-doctor verify SCENARIO PATCH`: judge a hang fix written by anyone (a person, a coding agent, qnx-doctor).

No model is called. The scenario is booted as it is and with the patch, and the patch gets one verdict
(bench/V7_VERIFY_PLAN.md section 1):
  accept  the stopped loop runs again, nothing that ran stops, and the message structure is kept (structure.py);
  reject  with the rule that failed (static rule, build, still hung, shortcut / structure changed);
  review  the rerun passes, but the check cannot vouch for it (gate.py): a person must read the named lines.
The row also keeps what a liveness-only check and the structure rule alone would have said, so the three can be
compared on the same boot. States only (QNX licence 4.6(i)).

PATCH is either a JSON list of edit_file actions (as the doctor writes them; paths start with the scenario's
directory name) or a unified diff against the scenario's directory (applied with `patch -p1`, else `-p0`).
"""
import glob
import json
import os
import shutil
import subprocess
import tempfile

from . import gate, hang
from .hangdoctor import verdict


def _sources(root: str, name: str) -> dict[str, str]:
    out = {}
    for f in sorted(glob.glob(os.path.join(root, "*.c")) + glob.glob(os.path.join(root, "*.h"))):
        out[f"{name}/{os.path.basename(f)}"] = open(f, errors="replace").read()
    return out


def load_patch(scen_dir: str, patch: str) -> tuple[list, str | None]:
    """(edit_file actions, error). A diff becomes one whole-file replacement per changed file."""
    name = os.path.basename(os.path.normpath(scen_dir))
    text = open(patch, errors="replace").read()
    if text.lstrip().startswith("["):
        try:
            acts = json.loads(text)
        except ValueError as e:
            return [], f"rejected: the patch is not valid JSON ({e})"
        return acts, None
    tmp = tempfile.mkdtemp(prefix="qd_patch_")
    try:
        dst = os.path.join(tmp, name)
        shutil.copytree(scen_dir, dst)
        for p in ("-p1", "-p0"):
            dry = subprocess.run(["patch", p, "--dry-run", "-s", "-d", dst, "-i", os.path.abspath(patch)],
                                 capture_output=True, text=True)
            if dry.returncode == 0:
                subprocess.run(["patch", p, "-s", "-d", dst, "-i", os.path.abspath(patch)], capture_output=True, text=True)
                break
        else:
            return [], "rejected: the diff does not apply to the scenario"
        before, after = _sources(scen_dir, name), _sources(dst, name)
        acts = [{"type": "edit_file", "path": k, "find": v, "replace": after[k]}
                for k, v in before.items() if after.get(k) is not None and after[k] != v]
        if set(after) - set(before) or set(before) - set(after):
            return [], "rejected (structure): the diff adds or removes source files"
        return acts, None if acts else "rejected: the diff changes no C source"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def verify(scen_dir: str, patch: str, sid: str | None = None) -> dict:
    name = os.path.basename(os.path.normpath(scen_dir))
    row = {"id": sid or name, "patch": os.path.basename(patch), "verdict": "reject", "why": [],
           "liveness_only": None, "structure_rule": None}
    acts, err = load_patch(scen_dir, patch)
    if err:
        row["why"] = [err]
        return row
    work = hang.prepare(scen_dir)
    try:
        first = hang.observe(work, name)
        if not first.get("ok"):
            row.update(verdict="error", why=[f"the unpatched scenario did not run: {first.get('stage')}"])
            return row
        fixed, err = hang.apply_fix(scen_dir, acts)
        try:
            if err:
                row["why"] = [err]
                return row
            res = hang.observe(fixed, name)
            v = verdict(first, res)
            row.update(liveness_only=bool(v["live"]), structure_rule=bool(v["fixed"]),
                       first_ticks=first.get("ticks"), rerun_ticks=res.get("ticks"), rerun_progress=res.get("progress"))
            if not v["fixed"]:
                row["why"] = ([v["why_not_live"]] if not v["live"] else
                              ["alive again but the message structure changed: " + "; ".join(v["structure"])])
                return row
            files_before = _sources(os.path.join(work, name), name)
            files_after = _sources(os.path.join(fixed, name), name)
            rv = gate.review(files_before, files_after)
            row.update(verdict="review" if rv else "accept", why=rv)
            return row
        finally:
            shutil.rmtree(fixed, ignore_errors=True)
    finally:
        shutil.rmtree(work, ignore_errors=True)
