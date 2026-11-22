"""Run one command spec in a work directory and capture what happened.

A spec is plain data so the doctor's fixes can be applied by code and re-run:
  argv, cwd (relative to the work dir), env (set), env_unset, source_sdp (bool), timeout,
  success = {exit, expect_output?, verify? (argv run after the command)}
"""
import copy
import os
import re
import shlex
import signal
import subprocess
from dataclasses import dataclass

from . import sandbox

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(HERE, "bin")


@dataclass
class Result:
    ok: bool
    exit: int
    output: str
    reason: str


# Every child process starts from this allow-list (2026-11-22): no API key or other secret of the caller's shell.
KEEP = ("PATH", "HOME", "USER", "LOGNAME", "LANG", "LC_ALL", "LC_CTYPE", "TERM", "TMPDIR",
        "QNX_SDP", "QD_QEMU_ROOT", "QD_QEMU_LOCK", "QD_SMP", "QD_EXEC_TIMEOUT", "QD_BOOT_TIMEOUT")


def base_env() -> dict:
    env = {k: os.environ[k] for k in KEEP if k in os.environ}
    env.setdefault("QNX_SDP", os.path.expanduser("~/personal/qnx/qnx800"))
    env.setdefault("QD_QEMU_ROOT", os.path.expanduser("~/personal/qemu_local/root"))
    env["PATH"] = BIN + os.pathsep + env.get("PATH", "")
    # A clean shell: the SDP is only on PATH when the spec asks for it.
    env["PATH"] = os.pathsep.join(p for p in env["PATH"].split(os.pathsep) if os.path.isabs(p) and "qnx800" not in p)
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
        # From the child's own environment only: os.path.expandvars read the caller's (API key included).
        env[k] = re.sub(r"\$(?:\{(\w+)\}|(\w+))", lambda m: env.get(m[1] or m[2], m[0]),
                        v.replace("$QD_QEMU_ROOT", env["QD_QEMU_ROOT"]).replace("$QNX_SDP", env["QNX_SDP"]))
    return env


def expand(argv, env):
    out = []
    for a in argv:
        for k in ("QD_QEMU_ROOT", "QNX_SDP"):
            a = a.replace("$" + k, env[k])
        out.append(a)
    return out


def licence(env: dict):
    """(licence directory, compiler driver) for sandbox.run, or None where there is no licensed SDP."""
    d = os.path.join(env.get("QNX_CONFIGURATION") or os.path.join(env.get("HOME", "/nonexistent"), ".qnx"), "license")
    qcc = os.path.join(env.get("QNX_SDP", ""), "host/linux/x86_64/usr/bin/qcc")
    return (d, qcc) if os.path.isdir(d) and os.path.exists(qcc) else None


def execute(argv, cwd, env, timeout):
    """Trusted commands (the user's own, the harness): minimal environment, own session, killed whole on a timeout."""
    p = subprocess.Popen(argv, cwd=cwd, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         start_new_session=True)
    try:
        out, err = p.communicate(timeout=timeout)
    except BaseException:
        try:
            os.killpg(p.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass
        p.wait()
        raise
    return p.returncode, (out + err).decode(errors="replace")


def _boxed(argv, cwd, env, workdir, timeout, licensed=False):
    """A command after the AI changed it, its environment or its files. Roots come from the trusted environment."""
    base = base_env()
    lock = base.get("QD_QEMU_LOCK", "/tmp/qd-qemu.lock")
    r = sandbox.run(argv, cwd, env, timeout=timeout, cpu=600,
                    read=[base["QNX_SDP"], base["QD_QEMU_ROOT"], BIN, os.path.join(HERE, "qnx_doctor")],
                    write=[workdir, lock, "/dev/kvm"], licence=licence(base) if licensed else None)
    return r.returncode, r.output, r.timed_out


def may_read_licence(before: dict, after: dict) -> bool:
    """A proposed fix is rerun with licence access only if it still runs the SDP's qcc itself and all it changed is
    sources, sourcing the SDP and -l / -L options. Anything else could make the command run a program of its own."""
    if before.get("env", {}) != after.get("env", {}) or before.get("env_unset", []) != after.get("env_unset", []):
        return False
    old, new = before["argv"], after["argv"]
    if old[0] != "qcc" or new[0] != old[0]:
        return False
    # The original call too: a response file, specs, plugin or linker script edited by the fix could run programs.
    for prev, a in zip(old, old[1:]):
        if prev != "-o" and not re.fullmatch(r"-o|-c|-g|-O\w?|-W[\w-]*|-V\w+|-[lLID][\w./+=-]+|-std=[\w+]+|[\w./+-]+\.(?:c|cc|cpp)", a):
            return False
    return all(a in old or re.fullmatch(r"-l[\w+-]+|-L[\w./+-]+", a) for a in new) and all(a in new for a in old)


def run(spec: dict, workdir: str, boxed: bool = False, licensed: bool = False) -> Result:
    env = build_env(spec)
    cwd = os.path.join(workdir, spec.get("cwd", "."))
    argv = expand(spec["argv"], env)
    try:
        if boxed:
            code, out, late = _boxed(argv, cwd, env, workdir, spec.get("timeout", 120), licensed)
            if late:
                return Result(False, -1, out + "\n[timed out]", "timeout")
        else:
            code, out = execute(argv, cwd, env, spec.get("timeout", 120))
    except (FileNotFoundError, NotADirectoryError) as e:
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
        check = expand(succ["verify"], env)
        try:
            vrc = _boxed(check, cwd, env, workdir, 60)[0] if boxed else execute(check, cwd, env, 60)[0]
        except (OSError, subprocess.TimeoutExpired):
            vrc = 127
        if vrc != 0:
            return Result(False, code, out + f"\n[verify failed: {' '.join(succ['verify'])}]", "verify failed")
    return Result(True, code, out, "ok")


def tail(text: str, n: int = 60) -> str:
    return "\n".join(text.strip().splitlines()[-n:])


def clone(spec: dict) -> dict:
    return copy.deepcopy(spec)
