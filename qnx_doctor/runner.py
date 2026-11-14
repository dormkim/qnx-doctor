"""Run one command spec in a work directory and capture what happened.

A spec is plain data so the doctor's fixes can be applied by code and re-run:
  argv, cwd (relative to the work dir), env (set), env_unset, source_sdp (bool), timeout,
  success = {exit, expect_output?, verify? (argv run after the command)}
"""
import copy
import os
import shlex
import subprocess
from dataclasses import dataclass

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(HERE, "bin")


@dataclass
class Result:
    ok: bool
    exit: int
    output: str
    reason: str


def base_env() -> dict:
    env = dict(os.environ)
    env.setdefault("QNX_SDP", os.path.expanduser("~/personal/qnx/qnx800"))
    env.setdefault("QD_QEMU_ROOT", os.path.expanduser("~/personal/qemu_local/root"))
    env["PATH"] = BIN + os.pathsep + env.get("PATH", "")
    # A clean shell: the SDP is only on PATH when the spec asks for it.
    for k in ("QNX_HOST", "QNX_TARGET", "QNX_CONFIGURATION", "MAKEFLAGS"):
        env.pop(k, None)
    env["PATH"] = os.pathsep.join(p for p in env["PATH"].split(os.pathsep) if "qnx800" not in p)
    return env


def sdp_env(env: dict) -> dict:
    """Return env after sourcing qnxsdp-env.sh (what a developer does by hand)."""
    script = os.path.join(env["QNX_SDP"], "qnxsdp-env.sh")
    out = subprocess.run(["bash", "-c", f". {shlex.quote(script)} >/dev/null 2>&1; env -0"],
                         env=env, capture_output=True, timeout=60).stdout.decode(errors="replace")
    new = dict(env)
    for item in out.split("\0"):
        if "=" in item:
            k, v = item.split("=", 1)
            new[k] = v
    return new


def build_env(spec: dict) -> dict:
    env = base_env()
    if spec.get("source_sdp"):
        env = sdp_env(env)
    for k in spec.get("env_unset", []):
        env.pop(k, None)
    for k, v in spec.get("env", {}).items():
        env[k] = os.path.expandvars(v.replace("$QD_QEMU_ROOT", env["QD_QEMU_ROOT"]).replace("$QNX_SDP", env["QNX_SDP"]))
    return env


def expand(argv, env):
    out = []
    for a in argv:
        for k in ("QD_QEMU_ROOT", "QNX_SDP"):
            a = a.replace("$" + k, env[k])
        out.append(a)
    return out


def run(spec: dict, workdir: str) -> Result:
    env = build_env(spec)
    cwd = os.path.join(workdir, spec.get("cwd", "."))
    argv = expand(spec["argv"], env)
    try:
        p = subprocess.run(argv, cwd=cwd, env=env, capture_output=True, timeout=spec.get("timeout", 120))
        out = (p.stdout + p.stderr).decode(errors="replace")
        code = p.returncode
    except FileNotFoundError as e:
        return Result(False, 127, f"{argv[0]}: command not found ({e})", "exec_failed")
    except subprocess.TimeoutExpired as e:
        out = ((e.stdout or b"") + (e.stderr or b"")).decode(errors="replace")
        return Result(False, -1, out + "\n[timed out]", "timeout")
    succ = spec.get("success", {"exit": 0})
    if code != succ.get("exit", 0):
        return Result(False, code, out, f"exit {code}")
    if succ.get("expect_output") and succ["expect_output"] not in out:
        return Result(False, code, out, "expected output missing")
    if succ.get("verify"):
        v = subprocess.run(expand(succ["verify"], env), cwd=cwd, env=env, capture_output=True, timeout=60)
        if v.returncode != 0:
            return Result(False, code, out + f"\n[verify failed: {' '.join(succ['verify'])}]", "verify failed")
    return Result(True, code, out, "ok")


def tail(text: str, n: int = 60) -> str:
    return "\n".join(text.strip().splitlines()[-n:])


def clone(spec: dict) -> dict:
    return copy.deepcopy(spec)
