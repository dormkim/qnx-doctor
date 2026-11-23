"""qnx_doctor.verify.load_patch: a diff or JSON actions become edit_file actions (no boot)."""
import json
import os
import subprocess
import tempfile
import unittest

from qnx_doctor.verify import load_patch


class LoadPatch(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.s = os.path.join(self.d, "s1")
        os.makedirs(self.s)
        with open(os.path.join(self.s, "a.c"), "w") as f:
            f.write("/* a comment, as most programs have */\nint main(void) {\n  int v = qd_send(c, 1);\n  return v;\n}\n")
        with open(os.path.join(self.s, "run.sh"), "w") as f:
            f.write("./a &\n")

    def _diff(self, new, name="a.c"):
        b = os.path.join(self.d, "b")
        os.makedirs(b, exist_ok=True)
        with open(os.path.join(b, name), "w") as f:
            f.write(new)
        os.symlink(self.s, os.path.join(self.d, "a")) if not os.path.exists(os.path.join(self.d, "a")) else None
        out = subprocess.run(["diff", "-u", f"a/{name}", f"b/{name}"], cwd=self.d, capture_output=True, text=True).stdout
        p = os.path.join(self.d, "fix.diff")
        with open(p, "w") as f:
            f.write(out)
        return p

    def test_unified_diff_becomes_a_whole_file_edit(self):
        p = self._diff("/* a comment, as most programs have */\nint main(void) {\n  int v = 1;\n  return v;\n}\n")
        acts, err = load_patch(self.s, p)
        self.assertIsNone(err)
        self.assertEqual([a["path"] for a in acts], ["s1/a.c"])
        self.assertIn("int v = 1;", acts[0]["replace"])

    def test_the_edit_applies_to_the_copy_the_run_builds(self):
        from qnx_doctor import actions as act, hang
        p = self._diff("/* a comment, as most programs have */\nint main(void) {\n  int v = 1;\n  return v;\n}\n")
        acts, err = load_patch(self.s, p)
        self.assertIsNone(err)
        work = hang.prepare(self.s)
        act.apply({"argv": ["true"], "cwd": "."}, acts, work)
        self.assertIn("int v = 1;", open(os.path.join(work, "s1", "a.c")).read())

    def test_json_actions_pass_through(self):
        p = os.path.join(self.d, "fix.json")
        with open(p, "w") as f:
            json.dump([{"type": "edit_file", "path": "s1/a.c", "find": "qd_send(c, 1)", "replace": "1"}], f)
        acts, err = load_patch(self.s, p)
        self.assertIsNone(err)
        self.assertEqual(acts[0]["replace"], "1")

    def test_a_diff_that_does_not_apply_is_rejected(self):
        p = os.path.join(self.d, "bad.diff")
        with open(p, "w") as f:
            f.write("--- a/a.c\n+++ b/a.c\n@@ -1,1 +1,1 @@\n-nothing like this\n+x\n")
        acts, err = load_patch(self.s, p)
        self.assertEqual(acts, [])
        self.assertTrue(err.startswith("rejected"))


if __name__ == "__main__":
    unittest.main()
