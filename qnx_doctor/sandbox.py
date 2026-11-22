"""The kernel boundary around everything that reads or runs model-written input (freeze blockers 3 and 4, 2026-11-22).

A text check of C or of command arguments cannot be complete, so it is not the barrier. The child process is:
  - given its environment explicitly (runner.base_env is an allow-list: no API key);
  - limited by Landlock to the paths named by the caller, plus the system's programs and libraries;
  - given a seccomp filter: no new sockets, io_uring, ptrace, process memory or kernel keyrings;
  - given file size and CPU limits, its own session, and killed with that session on a timeout.
No privileges, no installation. It needs Linux x86_64 with Landlock ABI 3 or later. Without that, nothing runs
(fail closed).

The SDP's licence file is special. qcc itself has to read it (and to create and remove a lock file next to it, so
that directory is open for writing to whatever runs with `licence`: give it only where no model-written code runs); cc1, as and ld have no need. Landlock cannot tell them
apart (children inherit the rules), so with `licence=(directory, driver)` the run is also watched with strace: if any
program other than the driver opens a file in that directory, the run fails and its output is dropped. The same
watch covers /tmp, which qcc needs for its scratch directory (it ignores TMPDIR, and a private /tmp would need a mount
namespace, which this host does not allow without privileges): a successful open there outside that run's own scratch
directory or the granted paths fails the run. For those two directories the boundary is detect-and-drop, not deny.

Not covered: stat() of outside paths, chmod/utime of the user's own files and signals to the user's own processes
(these matter only where model-written code runs on the host: the build/boot doctor, not `hang`); kernel and QEMU
bugs. See bench/V6_GATES_1122.md.

Run as a script (`python3 -I sandbox.py POLICY -- argv`) this file is the launcher. It imports the standard library
only, and it starts with a clean environment: the child's own environment travels in POLICY, so a variable such as
LD_PRELOAD cannot act before the boundary is up.
"""
import ctypes
import json
import os
import platform
import re
import resource
import shutil
import signal
import struct
import subprocess
import sys
import tempfile
from types import SimpleNamespace

PYTHON = "/usr/bin/python3"
STRACE = "/usr/bin/strace"
CLEAN = {"PATH": "/usr/bin:/bin", "LC_ALL": "C"}
NR_CREATE, NR_ADD_RULE, NR_RESTRICT = 444, 445, 446
EXECUTE, WRITE, READ, READ_DIR, TRUNCATE = 1, 2, 4, 8, 1 << 14
REMOVE_DIR, REMOVE_FILE, MAKE_DIR, MAKE_FILE = 1 << 4, 1 << 5, 1 << 7, 1 << 8
LOCK_DIR = READ | WRITE | MAKE_FILE | REMOVE_FILE  # qcc creates and removes licenses.lck next to the licence
SCRATCH_DIR = LOCK_DIR | READ_DIR | MAKE_DIR | REMOVE_DIR | TRUNCATE  # never EXECUTE
QCC_SCRATCH = "/tmp"  # qcc makes /tmp/file<random>_qcc_<pid> whatever TMPDIR says
ALL = (1 << 15) - 1
FILE_ONLY = EXECUTE | WRITE | READ | TRUNCATE
SYSTEM = ("/usr", "/bin", "/sbin", "/lib", "/lib64", "/etc/ld.so.cache", "/etc/passwd", "/etc/group", "/etc/nsswitch.conf",
          "/etc/alternatives", "/etc/magic", "/etc/magic.mime", "/etc/localtime", "/dev/urandom", "/dev/random", "/dev/zero")
SINKS = ("/dev/null",)
# socket, io_uring_setup, ptrace, process_vm_readv/writev, pidfd_getfd, add_key, request_key, keyctl
DENIED_CALLS = (41, 425, 101, 310, 311, 438, 248, 249, 250)
AUDIT_ARCH_X86_64 = 0xC000003E
MAX_OUTPUT = 2 * 2 ** 20
NO_SANDBOX = "qnx-doctor: no sandbox on this host (Linux x86_64 with Landlock ABI 3+ is needed), not run"


def _libc():
    return ctypes.CDLL(None, use_errno=True)


def supported() -> bool:
    if sys.platform != "linux" or platform.machine() != "x86_64" or not os.path.exists(PYTHON):
        return False
    return _libc().syscall(NR_CREATE, None, ctypes.c_size_t(0), 1) >= 3


def _check(ret, what):
    if ret < 0:
        raise OSError(ctypes.get_errno(), what)
    return ret


def _landlock(libc, read, write, lock=(), scratch=()):
    attr = ctypes.create_string_buffer(struct.pack("=Q", ALL))
    rules = _check(libc.syscall(NR_CREATE, attr, ctypes.c_size_t(8), 0), "landlock_create_ruleset")
    for paths, rights in ((read, EXECUTE | READ | READ_DIR), (write, ALL), (lock, LOCK_DIR), (scratch, SCRATCH_DIR)):
        for path in paths:
            try:
                fd = os.open(path, os.O_PATH | os.O_CLOEXEC)
            except FileNotFoundError:
                continue
            allowed = rights if os.path.isdir(path) else rights & FILE_ONLY
            rule = ctypes.create_string_buffer(struct.pack("=Qi", allowed, fd))
            _check(libc.syscall(NR_ADD_RULE, rules, 1, rule, 0), "landlock_add_rule")
            os.close(fd)
    _check(libc.syscall(NR_RESTRICT, rules, 0), "landlock_restrict_self")
    os.close(rules)


def _seccomp(libc):
    load, jeq, jge, ret = 0x20, 0x15, 0x35, 0x06
    eperm, allow, kill = 0x00050001, 0x7FFF0000, 0x80000000
    code = [(load, 0, 0, 4), (jeq, 1, 0, AUDIT_ARCH_X86_64), (ret, 0, 0, kill),
            (load, 0, 0, 0), (jge, 0, 1, 0x40000000), (ret, 0, 0, eperm)]  # the x32 numbers would pass the list below
    for nr in DENIED_CALLS:
        code += [(jeq, 0, 1, nr), (ret, 0, 0, eperm)]
    code.append((ret, 0, 0, allow))
    buf = ctypes.create_string_buffer(b"".join(struct.pack("=HBBI", *c) for c in code))

    class Prog(ctypes.Structure):
        _fields_ = [("len", ctypes.c_ushort), ("filter", ctypes.c_void_p)]
    prog = Prog(len(code), ctypes.cast(buf, ctypes.c_void_p))
    _check(libc.prctl(22, 2, ctypes.byref(prog), 0, 0), "seccomp")


def die_with_parent():
    """PR_SET_PDEATHSIG: a killed caller does not leave this process (or QEMU) behind."""
    if sys.platform == "linux":
        _libc().prctl(1, int(signal.SIGKILL), 0, 0, 0)


def _launch(policy: dict, argv: list):
    die_with_parent()
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    for key, res in (("fsize", resource.RLIMIT_FSIZE), ("cpu", resource.RLIMIT_CPU), ("mem", resource.RLIMIT_AS)):
        if policy.get(key):
            resource.setrlimit(res, (policy[key], policy[key]))
    libc = _libc()
    _check(libc.prctl(38, 1, 0, 0, 0), "no_new_privs")
    _landlock(libc, policy["read"], policy["write"], policy["lock"], policy["scratch"])
    _seccomp(libc)
    os.execve(argv[0], argv, policy["env"])


def command(argv, env, read=(), write=(), fsize=4 * 2 ** 30, cpu=None, mem=None, lock=(), scratch=()) -> list:
    """argv that runs `argv` (absolute program) inside the boundary. Start it with sandbox.CLEAN as environment."""
    policy = {"env": env, "read": [*SYSTEM, *map(str, read)], "write": [*SINKS, *map(str, write)],
              "lock": list(lock), "scratch": list(scratch), "fsize": fsize, "cpu": cpu, "mem": mem}
    return [PYTHON, "-I", os.path.abspath(__file__), json.dumps(policy), "--", *argv]


def _under(path: str, root: str) -> bool:
    return path == root or path.startswith(root.rstrip("/") + "/")


def foreign_opens(trace: str, directory: str, driver: str, scratch: str = None, granted=()) -> list:
    """Programs that opened what they should not, from an `strace -f -y` log: anything but `driver` under
    `directory`; any program under `scratch` outside this run's own qcc directory and the `granted` paths."""
    exe, pending, path_only, bad, drivers, seen = {}, {}, set(), [], set(), []
    directory, driver = os.path.realpath(directory), os.path.realpath(driver)
    for line in trace.splitlines():
        m = re.match(r"(\d+)\s+(.*)$", line)
        if not m:
            continue
        pid, call = m[1], m[2]
        e = re.match(r'execve\("([^"]*)"', call)
        if e:
            pending[pid] = e[1]
        if (e or call.startswith("<... execve resumed")) and re.search(r"= 0$", call) and pid in pending:
            exe[pid] = os.path.realpath(pending.pop(pid))
            if exe[pid] == driver:
                drivers.add(pid)
            continue
        started = re.match(r'(?:open|openat|openat2)\(', call)
        if started:
            # An O_PATH descriptor cannot be read (the launcher takes one to write each rule); opening it again
            # through /proc is an open of its own and is seen. The flags are read outside the quoted file name.
            flags = re.match(r'open(?:at)?\([^"]*"(?:[^"\\]|\\.)*", ([A-Z_|]+)', call)
            (path_only.add if flags and "O_PATH" in flags[1].split("|") else path_only.discard)(pid)
        o = re.search(r"= \d+<(.*)>$", call)
        if not o or pid in path_only:
            continue
        who = os.path.basename(exe.get(pid, "unknown"))
        if _under(o[1], directory):
            if exe.get(pid) != driver:
                bad.append(who)
        elif scratch and _under(o[1], scratch) and not any(_under(o[1], g) for g in granted):
            seen.append((who, o[1]))
    for who, path in seen:
        m = re.match(re.escape(scratch) + r"/file\w{6}_qcc_(\d+)(?:/|$)", path)
        if not m or m[1] not in drivers:
            bad.append(who)
    return bad


def run(argv, cwd, env, read=(), write=(), timeout=120, licence=None, fsize=4 * 2 ** 30, cpu=None, mem=None,
        licence_lock=None):
    """-> returncode, output (stdout + stderr, the tail), timed_out. Never falls back to an unboxed run.
    `licence_lock`: the licence directory for SDP tools that read no model-written text (the image tools, which call
    qcc to link the boot image): the same two directories, unwatched.
    Raises FileNotFoundError if the program is not found in env's PATH."""
    if not supported():
        return SimpleNamespace(returncode=126, output=NO_SANDBOX, timed_out=False)
    prog = argv[0]
    if os.path.sep in prog:
        prog = os.path.join(os.path.abspath(cwd), prog)
    else:
        found = [os.path.join(d, prog) for d in env.get("PATH", "").split(os.pathsep) if os.path.isabs(d)]
        prog = next((p for p in found if os.path.isfile(p) and os.access(p, os.X_OK)), None)
    if not prog or not os.path.exists(prog):
        raise FileNotFoundError(argv[0])
    if licence and not os.path.exists(STRACE):
        return SimpleNamespace(returncode=126, output="qnx-doctor: strace is needed to guard the licence file, not run",
                               timed_out=False)
    box = tempfile.mkdtemp(prefix="qd-box-")
    try:
        tmp = os.path.join(box, "tmp")
        os.mkdir(tmp)
        env = {**env, "TMPDIR": tmp}
        read, write = list(read), [*write, tmp]
        lock, scratch = ([licence[0]], [QCC_SCRATCH]) if licence else ([licence_lock], [QCC_SCRATCH]) if licence_lock else ([], [])
        cmd = command([prog, *argv[1:]], env, read, write, fsize, cpu, mem, lock, scratch)
        trace = os.path.join(box, "trace")
        if licence:
            cmd = [STRACE, "-f", "--seccomp-bpf", "-qq", "-y", "-e", "signal=none", "-e",
                   "trace=execve,execveat,open,openat,openat2", "-o", trace, *cmd]
        timed_out = False
        with open(os.path.join(box, "output"), "w+b") as out:
            p = subprocess.Popen(cmd, cwd=cwd, env=CLEAN, stdin=subprocess.DEVNULL, stdout=out, stderr=out,
                                 start_new_session=True)
            try:
                rc = p.wait(timeout)
            except subprocess.TimeoutExpired:
                timed_out, rc = True, -1
            finally:
                try:
                    os.killpg(p.pid, signal.SIGKILL)  # whatever the child left behind in its session
                except (ProcessLookupError, PermissionError):
                    pass
                p.wait()
            out.seek(max(0, os.fstat(out.fileno()).st_size - MAX_OUTPUT))
            text = out.read().decode(errors="replace")
        if licence:
            try:
                with open(trace, errors="replace") as f:
                    bad = foreign_opens(f.read(), licence[0], licence[1], os.path.realpath(QCC_SCRATCH),
                                        [os.path.realpath(p) for p in (*read, *write)])
            except OSError:
                bad = ["(no trace)"]
            if bad:
                return SimpleNamespace(returncode=126, timed_out=False,
                                       output="qnx-doctor: the build opened a file it must not (licence or another "
                                              f"/tmp entry; by {', '.join(sorted(set(bad)))}); output dropped")
        return SimpleNamespace(returncode=rc, output=text, timed_out=timed_out)
    finally:
        shutil.rmtree(box, ignore_errors=True)


if __name__ == "__main__":
    cut = sys.argv.index("--")
    try:
        _launch(json.loads(sys.argv[cut - 1]), sys.argv[cut + 1:])
    except Exception as err:  # never continue without the boundary
        print(f"qnx-doctor sandbox: {err}", file=sys.stderr)
        sys.exit(126)
