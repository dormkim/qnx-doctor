"""The only place the AI's requests touch the host: read-only look-around commands from a fixed allow-list.

Kept out of ai.py on purpose: ai.py (the model loop) must not import subprocess or the fix actions, so the
model can only ask; code decides what runs (tests/unit/test_boundary.py checks this with the AST).

Four layers since 2026-11-22 (until then the program was checked by base name only, its options not at all, and
`find . -exec env ;` printed the environment, API key included):
  1. the exact name is replaced by a fixed absolute program;
  2. options are an allow-list per command (nothing that runs, writes, follows links or reads a list from a file);
  3. every path argument is judged by realpath: hang mode = the work copy; otherwise the work copy, the SDP and QEMU;
  4. the child runs in sandbox.py with the same roots and an environment without secrets."""
import os
import re

from . import sandbox

BIN = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "bin")
MAX_ARGS, MAX_LEN = 64, 4096

# name -> options: short flags (may be clustered), short options with a value, long flags, long options «--x=value»
OPTIONS = {
    "ls": ("laAhRrStd1nigF", "", (), ()),
    "cat": ("nAbsveEtT", "", (), ()),
    "head": ("qv", "nc", (), ("--lines", "--bytes")),
    "tail": ("qv", "nc", (), ("--lines", "--bytes")),
    "grep": ("nivclLwxohHEFGrIsqa", "eABCm", ("--color", "--color=never"), ("--include", "--exclude")),
    "file": ("bi", "", ("--brief", "--mime"), ()),
    "readelf": ("hlSsdanreVWAu", "", ("--wide",), ()),
    "stat": ("t", "c", (), ("--format",)),
    "du": ("shackm", "d", (), ("--max-depth",)),
    "which": ("a", "", (), ()),
}
NUMERIC = {"head": "nc", "tail": "nc", "grep": "ABCm", "du": "d"}
FIND_FLAGS = ("-print", "-print0", "-empty", "-prune", "-not", "!", "-o", "-a", "-or", "-and", "(", ")")
FIND_VALUE = ("-name", "-iname", "-path", "-ipath", "-type", "-maxdepth", "-mindepth", "-size")
PROBES = {"find", *OPTIONS}


def program(name: str):
    return next((p for p in (f"/usr/bin/{name}", f"/bin/{name}") if os.path.isfile(p) and os.access(p, os.X_OK)), None)


def _find_paths(args):
    paths, i = [], 0
    while i < len(args) and not args[i].startswith("-") and args[i] not in FIND_FLAGS:
        paths.append(args[i])
        i += 1
    while i < len(args):
        if args[i] in FIND_VALUE and i + 1 < len(args):
            i += 2
        elif args[i] in FIND_FLAGS:
            i += 1
        else:
            return None, f"find: {args[i]!r} is not an allowed option"
    return paths, None


def _other_paths(name, args):
    short, valued, long_flags, long_valued = OPTIONS[name]
    rest, pattern, options, i = [], name == "grep", True, 0
    while i < len(args):
        a = args[i]
        i += 1
        if not options or not a.startswith("-"):
            rest.append(a)
        elif a == "--":
            options = False
        elif a in long_flags or any(a.startswith(o + "=") for o in long_valued):
            pass
        elif name in ("head", "tail") and re.fullmatch(r"-\d+", a):
            pass
        elif a.startswith("--") or a == "-":
            return None, f"{name}: {a!r} is not an allowed option"
        else:
            for j, c in enumerate(a[1:], 1):
                if c in short:
                    continue
                if c not in valued:
                    return None, f"{name}: -{c} is not an allowed option"
                value = a[j + 1:]
                if not value:
                    if i >= len(args):
                        return None, f"{name}: -{c} needs a value"
                    value, i = args[i], i + 1
                if c in NUMERIC.get(name, "") and not re.fullmatch(r"[+-]?\d+", value):
                    return None, f"{name}: -{c} takes a number"
                if name == "grep" and c == "e":
                    pattern = False
                break
    if pattern:
        if not rest:
            return None, "grep: no pattern"
        rest = rest[1:]
    return rest, None


def check(argv, cwd, roots):
    """None = may run, else the reason it is refused."""
    name, args = argv[0], argv[1:]
    paths, why = _find_paths(args) if name == "find" else _other_paths(name, args)
    if why:
        return why
    if name == "which":
        return None if all("/" not in p for p in paths) else "which: names only"
    for p in paths or ["."]:
        real = os.path.realpath(os.path.join(cwd, p))
        if p == "-" or not any(sandbox._under(real, r) for r in roots):
            return f"{p!r}: only paths inside the working directory" + (", the SDP or QEMU" if len(roots) > 1 else "")
    return None


def probe(argv, cwd, env, confine=False):
    if (not isinstance(argv, list) or not argv or len(argv) > MAX_ARGS
            or any(not isinstance(a, str) or len(a) > MAX_LEN or "\x00" in a for a in argv)):
        return "probe refused: argv must be a short list of strings"
    if argv[0] not in PROBES or not program(argv[0]):
        return f"probe refused: {argv[:1]} is not a read-only command"
    roots = [os.path.realpath(cwd)]
    if not confine:  # build/boot doctor: also the toolchain it diagnoses, never the rest of the host
        roots += [os.path.realpath(p) for p in (env.get("QNX_SDP"), env.get("QD_QEMU_ROOT"), BIN) if p and os.path.isdir(p)]
    try:
        why = check(argv, cwd, roots)
        if why:
            return f"probe refused: {why}"
        child = {"PATH": env.get("PATH", "") if argv[0] == "which" else "/usr/bin:/bin", "LC_ALL": "C"}
        r = sandbox.run([program(argv[0]), *argv[1:]], cwd, child, read=roots, timeout=30, fsize=8 * 2 ** 20, cpu=20,
                        mem=2 * 2 ** 30)
    except Exception as e:
        return f"probe failed: {type(e).__name__}"
    return r.output[-3000:] or "(no output)"
