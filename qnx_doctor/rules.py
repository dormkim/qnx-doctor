"""Baseline without AI: a fixed table of well-known messages (QNX docs + generic Linux knowledge).
Used both as the "AI off" comparison and as the first thing the doctor tries.
Rules may look at the local disk (read-only) to fill in a path, the way a careful person would."""
import os
import re
import subprocess

QNX_TOOLS = ("qcc", "q++", "mkqnximage", "mkifs", "mkqnx6fsimg", "ntox86_64-gcc", "ntoaarch64-gcc")
SOCKET_SYMS = {"socket", "connect", "bind", "listen", "accept", "inet_pton", "inet_ntop", "inet_addr",
               "getaddrinfo", "freeaddrinfo", "gethostbyname", "setsockopt", "recvfrom", "sendto"}


def _program(argv):
    return argv[1] if argv and os.path.basename(argv[0]) == "qd-boot" and len(argv) > 1 else argv[0]


def _prefix(prog_path):
    # .../root/usr/bin/qemu -> .../root
    p = os.path.dirname(os.path.dirname(os.path.dirname(prog_path)))
    return p if os.path.isdir(p) else None


def _find(root, name, kind="f"):
    try:
        out = subprocess.run(["find", root, "-name", name, "(", "-type", "f", "-o", "-type", "l", ")"], capture_output=True, timeout=30, text=True).stdout
    except Exception:
        return None
    hits = [l for l in out.splitlines() if l]
    return hits[0] if hits else None


def suggest(argv_expanded, output):
    """Return (cause, actions, why) or None."""
    prog = _program(argv_expanded)
    base = os.path.basename(prog)
    if ("command not found" in output or "No such file" in output) and base in QNX_TOOLS:
        return ("sdp_env_not_sourced", [{"type": "source_sdp"}], f"{base} is an SDP tool; source qnxsdp-env.sh")
    if re.search(r"QNX_(HOST|TARGET)", output):
        return ("qnx_env_vars_missing", [{"type": "source_sdp"}], "QNX_HOST/QNX_TARGET are set by qnxsdp-env.sh")
    m = re.search(r"error while loading shared libraries: (\S+?):", output)
    if m and _prefix(prog):
        hit = _find(_prefix(prog), m.group(1))
        if hit:
            return ("shared_libs", [{"type": "set_env", "name": "LD_LIBRARY_PATH", "value": os.path.dirname(hit)}],
                    f"found {m.group(1)} under the program's install prefix")
    if "could not load module for type" in output and _prefix(prog):
        hit = _find(_prefix(prog), "accel-tcg-*.so") or _find(_prefix(prog), "accel-*.so")
        if hit:
            return ("qemu_module_dir", [{"type": "set_env", "name": "QEMU_MODULE_DIR", "value": os.path.dirname(hit)}],
                    "QEMU looks for accelerator modules in QEMU_MODULE_DIR")
    m = re.search(r"could not load PC BIOS '([^']+)'", output)
    if m and _prefix(prog):
        hit = _find(_prefix(prog), os.path.basename(m.group(1)))
        if hit:
            return ("qemu_bios_path", [{"type": "add_args", "args": ["-L", os.path.dirname(hit)], "position": "start"}],
                    "QEMU -L sets the firmware directory")
    syms = set(re.findall(r"undefined reference to `(\w+)'", output))
    if syms and syms & SOCKET_SYMS:
        return ("missing_link_library", [{"type": "add_args", "args": ["-lsocket"], "position": "end"}],
                "on QNX the socket API lives in libsocket")
    return None
