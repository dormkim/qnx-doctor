"""The model loop can only ask; code decides what runs. Checked on the source (AST), not by trusting comments.

ai.py must not import subprocess/shutil or the fix actions, and must not call os.system/popen/exec*/spawn*/remove.
The one host-touching path it may use is probes.probe, which only runs a fixed read-only allow-list."""
import ast
import os
import unittest

from qnx_doctor import probes

PKG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "qnx_doctor")
BANNED_MODULES = {"subprocess", "shutil", "actions", "qnx_doctor.actions", "pty", "multiprocessing"}
BANNED_OS = ("system", "popen", "exec", "spawn", "remove", "unlink", "rename", "rmdir", "kill", "fork")


def tree(name):
    return ast.parse(open(os.path.join(PKG, name)).read())


class AiBoundary(unittest.TestCase):
    def test_ai_imports_nothing_that_changes_the_system(self):
        found = set()
        for n in ast.walk(tree("ai.py")):
            if isinstance(n, ast.Import):
                found |= {a.name for a in n.names}
            elif isinstance(n, ast.ImportFrom):
                mod = ("." * n.level) + (n.module or "")
                found.add(mod.lstrip("."))
                found |= {a.name for a in n.names if mod.startswith(".") and not n.module}
        self.assertFalse(found & BANNED_MODULES, found & BANNED_MODULES)

    def test_ai_calls_no_os_process_or_file_mutation(self):
        bad = [ast.unparse(n) for n in ast.walk(tree("ai.py"))
               if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) and n.value.id == "os"
               and n.attr.startswith(BANNED_OS)]
        self.assertEqual(bad, [])

    def test_ai_opens_no_file_for_writing(self):
        for n in ast.walk(tree("ai.py")):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "open":
                self.fail("ai.py opens a file: " + ast.unparse(n))


class ProbeAllowList(unittest.TestCase):
    def test_refuses_commands_outside_the_list(self):
        for argv in (["rm", "-rf", "x"], ["sh", "-c", "ls"], ["python3", "-c", "1"], ["/bin/rm", "x"], []):
            self.assertIn("refused", probes.probe(argv, ".", dict(os.environ)))

    def test_confined_probe_stays_inside_the_work_dir(self):
        for argv in (["cat", "/etc/passwd"], ["ls", "../labels.json"], ["grep", "x", "a/../../b"]):
            self.assertIn("refused", probes.probe(argv, ".", dict(os.environ), confine=True))

    def test_allowed_probe_runs(self):
        self.assertNotIn("refused", probes.probe(["ls"], ".", dict(os.environ), confine=True))


if __name__ == "__main__":
    unittest.main()
