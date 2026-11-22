"""A killed qnx-doctor leaves no child behind (2026-11-22: children now have their own session, so a signal to the
caller's group no longer reaches them). Only processes this test starts are signalled, by PID."""
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest

from qnx_doctor import sandbox

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")


def running(pid):
    try:
        with open(f"/proc/{pid}/stat") as f:
            return f.read().rsplit(")", 1)[1].split()[0] != "Z"
    except OSError:
        return False


@unittest.skipUnless(sys.platform == "linux", "Linux only")
class Orphans(unittest.TestCase):
    def killed_parent(self, call):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)
        pidfile = os.path.join(d, "pid")
        argv = ["/bin/sh", "-c", f"echo $$ > {pidfile}; exec sleep 20"]
        code = (f"import sys; sys.dont_write_bytecode = True; sys.path.insert(0, {ROOT!r})\n"
                f"from qnx_doctor import runner, sandbox\n{call.format(argv=argv, d=d)}\n")
        parent = subprocess.Popen([sys.executable, "-c", code], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            end = time.time() + 10
            while time.time() < end and not (os.path.exists(pidfile) and os.path.getsize(pidfile)):
                time.sleep(0.05)
            child = int(open(pidfile).read())
            parent.kill()
            parent.wait()
            end = time.time() + 5
            while time.time() < end and running(child):
                time.sleep(0.05)
            left = running(child)
            if left:
                os.kill(child, signal.SIGKILL)
            self.assertFalse(left, "the child outlived its killed parent")
        finally:
            if parent.poll() is None:
                parent.kill()
                parent.wait()

    def test_trusted_command(self):
        self.killed_parent("runner.execute({argv!r}, {d!r}, {{'PATH': '/usr/bin:/bin'}}, 30)")

    @unittest.skipUnless(sandbox.supported(), "no kernel sandbox here")
    def test_boxed_command(self):
        self.killed_parent("sandbox.run({argv!r}, {d!r}, {{'PATH': '/usr/bin:/bin'}}, read=[{d!r}], write=[{d!r}])")


if __name__ == "__main__":
    unittest.main()
