"""What model output may do on the host (freeze blockers 3 and 4, 2026-11-22). Written before the fix.

Dummy values and temporary files only. The tests that need the kernel sandbox are skipped where there is none
(not Linux x86_64 with Landlock); the code refuses to run model-written input there."""
import contextlib
import io
import os
import shutil
import tempfile
import unittest
from types import SimpleNamespace as NS
from unittest import mock

from qnx_doctor import doctor, hang, hangdoctor, probes, runner

try:
    from qnx_doctor import sandbox
    BOXED = sandbox.supported()
except ImportError:  # before the fix: let every test run and fail
    sandbox, BOXED = None, True

MARK, DUMMY = "outside-marker-7731", "dummy-value-not-a-key"


class Dirs(unittest.TestCase):
    def setUp(self):
        self.top = os.path.realpath(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.top, True)
        self.work = os.path.join(self.top, "work")
        self.put("work/s1/a.c", "int main(void) { return 0; }\n")
        self.put("work/local/snippets/list.custom", "x\n")
        self.secret = self.put("outside/secret.txt", MARK + "\n")
        self.sdp = os.path.join(self.top, "sdp")
        self.put("sdp/target/signal.h", "#define SA_X 1\n")
        self.env = {"PATH": "/usr/bin:/bin", "QNX_SDP": self.sdp, "QD_QEMU_ROOT": os.path.join(self.top, "noqemu"),
                    "ANTHROPIC_API_KEY": DUMMY}

    def put(self, rel, text, mode=0o644):
        path = os.path.join(self.top, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(text)
        os.chmod(path, mode)
        return path

    def probe(self, *argv, confine=True):
        return probes.probe(list(argv), self.work, self.env, confine)

    def refused(self, *argv, confine=True):
        out = self.probe(*argv, confine=confine)
        self.assertIn("probe refused", out, argv)
        self.assertNotIn(MARK, out)
        self.assertNotIn(DUMMY, out)


class ProbePrograms(Dirs):
    def test_program_in_the_work_dir_named_like_an_allowed_one(self):
        self.put("work/cat", "#!/bin/sh\necho ran\n", 0o755)
        self.refused("./cat", "s1/a.c")
        self.refused("cat/", "s1/a.c")

    def test_program_given_by_path(self):
        self.refused(self.put("outside/cat", "#!/bin/sh\necho ran\n", 0o755), "s1/a.c")

    def test_search_path_does_not_choose_the_program(self):
        self.put("work/evil/cat", "#!/bin/sh\necho ran\n", 0o755)
        self.env["PATH"] = os.path.join(self.work, "evil") + ":/usr/bin:/bin"
        self.assertNotIn("ran", self.probe("cat", "s1/a.c"))

    def test_malformed_requests_do_not_crash(self):
        for argv in (None, "ls", [1], [["ls"]], ["ls", None], ["ls", "a\x00b"], ["ls"] + ["."] * 500):
            self.assertIn("probe refused", probes.probe(argv, self.work, self.env, True), repr(argv)[:60])


class ProbeOptions(Dirs):
    def test_find_exec(self):
        for opt in ("-exec", "-execdir", "-ok", "-okdir"):
            self.refused("find", ".", "-maxdepth", "0", opt, "env", ";")

    def test_find_write_or_delete(self):
        self.put("work/victim", "x")
        self.refused("find", ".", "-name", "victim", "-delete")
        self.assertTrue(os.path.exists(os.path.join(self.work, "victim")))
        for opt in ("-fprint", "-fprint0", "-fls"):
            self.refused("find", ".", opt, "written")
        self.refused("find", ".", "-fprintf", "written", "%p")
        self.assertFalse(os.path.exists(os.path.join(self.work, "written")))

    def test_find_following_links_or_reading_a_list(self):
        os.symlink(os.path.dirname(self.secret), os.path.join(self.work, "link"))
        self.refused("find", "-L", ".")
        self.refused("find", ".", "-follow")
        self.refused("find", "-files0-from", self.secret)
        self.refused("find", ".", "-newer", self.secret)

    def test_file_options_that_write_or_run(self):
        for args in (["-C", "-m", "s1/a.c"], ["-C"], ["-z", "s1/a.c"], ["-m", self.secret, "s1/a.c"], ["-f", self.secret]):
            self.refused("file", *args)

    def test_options_that_take_a_file(self):
        self.refused("grep", "--file=" + self.secret, "s1/a.c")
        self.refused("grep", "-f" + self.secret, "s1/a.c")
        self.refused("grep", "-f", "s1/a.c", "s1/a.c")
        self.refused("grep", "-nf" + self.secret, "s1/a.c")
        self.refused("du", "--files0-from=" + self.secret)

    def test_options_that_never_end_or_follow_links(self):
        self.refused("grep", "-R", "x", ".")
        self.refused("du", "-L", ".")
        self.refused("ls", "-L", ".")
        self.refused("head", "--unknown", "s1/a.c")


class ProbePaths(Dirs):
    def test_absolute_and_parent_paths(self):
        self.refused("cat", self.secret)
        self.refused("cat", "../outside/secret.txt")
        self.refused("cat", "s1/../../outside/secret.txt")
        self.refused("cat", "--", self.secret)

    def test_symlink_to_a_file(self):
        os.symlink(self.secret, os.path.join(self.work, "innocent.c"))
        self.refused("cat", "innocent.c")
        self.refused("cat", "--", "innocent.c")

    def test_symlink_to_a_directory(self):
        os.symlink(os.path.dirname(self.secret), os.path.join(self.work, "dir"))
        self.refused("cat", "dir/secret.txt")
        self.refused("grep", "-r", "outside", "dir")

    def test_path_named_like_an_option_after_double_dash(self):
        os.symlink(self.secret, os.path.join(self.work, "-n"))
        self.refused("cat", "--", "-n")

    def test_unconfined_probe_is_limited_to_work_sdp_and_qemu(self):
        self.refused("cat", self.secret, confine=False)
        self.refused("cat", "/proc/self/environ", confine=False)
        self.refused("cat", os.path.expanduser("~/.bashrc"), confine=False)
        self.refused("find", self.top, "-name", "secret.txt", confine=False)

    @unittest.skipUnless(BOXED, "no kernel sandbox here")
    def test_recorded_probe_shapes_still_work(self):  # the probes in the committed run records
        for argv in (["ls", "-la", "s1"], ["cat", "s1/a.c"], ["cat", "s1/a.c", "s1/a.c"],
                     ["grep", "-n", "main\\|setprio", "s1/a.c"], ["grep", "-n", "main", "s1/a.c"],
                     ["grep", "-rn", "x", "local"], ["cat", "-A", "local/snippets/list.custom"], ["find", "local", "-type", "f"]):
            out = self.probe(*argv)
            self.assertNotIn("refused", out, argv)
            self.assertNotIn("denied", out, argv)
            self.assertNotEqual(out, "(no output)", argv)
        header = os.path.join(self.sdp, "target", "signal.h")
        self.assertIn("SA_X", self.probe("grep", "-n", "-B3", "-A3", "SA_X", header, confine=False))


class ChildEnvironment(Dirs):
    SET = {"ANTHROPIC_API_KEY": DUMMY, "ANTHROPIC_AUTH_TOKEN": DUMMY, "SOME_OTHER_SECRET": DUMMY, "BASH_ENV": "/dev/null"}

    def test_base_env_is_an_allow_list(self):
        with mock.patch.dict(os.environ, self.SET):
            env = runner.base_env()
        self.assertEqual({k for k in self.SET if k in env}, set())
        for k in ("PATH", "QNX_SDP", "QD_QEMU_ROOT"):
            self.assertIn(k, env)

    def test_relative_search_path_entries_are_dropped(self):
        with mock.patch.dict(os.environ, {"PATH": ".:evil::/usr/bin"}):
            parts = runner.base_env()["PATH"].split(os.pathsep)
        self.assertEqual([p for p in parts if not os.path.isabs(p)], [])

    def test_an_action_cannot_expand_the_parents_secret(self):
        with mock.patch.dict(os.environ, self.SET):
            env = runner.build_env({"env": {"X": "$ANTHROPIC_API_KEY", "Y": "${SOME_OTHER_SECRET}"}})
        self.assertNotIn(DUMMY, env["X"] + env["Y"])

    @unittest.skipUnless(BOXED, "no kernel sandbox here")
    def test_probe_child_has_no_key(self):
        self.put("work/where", "")
        with mock.patch.dict(os.environ, self.SET):
            self.assertIsNotNone(sandbox, "no sandbox module")
            out = sandbox.run(["/usr/bin/env"], self.work, runner.base_env(), read=[self.work]).output
        self.assertIn("PATH=", out)
        self.assertNotIn(DUMMY, out)


class Edits(Dirs):
    def setUp(self):
        super().setUp()
        self.pool = os.path.join(self.top, "pool")
        self.scen = os.path.join(self.pool, "t1")
        self.put("pool/t1/a.c", '#include "../common/qd.h"\nint main(void) { return 0; }\n')
        self.put("pool/t1/run.sh", "/var/qd/t1/a &\n")
        self.put("pool/common/qd.h", "#define QD 1\n")

    def edit(self, *pairs, path="t1/a.c"):
        work, err = hang.apply_fix(self.scen, [{"type": "edit_file", "path": path, "find": f, "replace": r} for f, r in pairs])
        shutil.rmtree(work, True)
        return err

    def line(self, text):
        return self.edit(("int main", text + "\nint main"))

    def test_include_of_a_path_outside(self):
        for text in (f'#include "{self.secret}"', f"#include <{self.secret}>", '#include "../../outside/secret.txt"',
                     "#include <../../outside/secret.txt>", '#include "../answers/labels.json"'):
            self.assertIn("rejected", self.line(text) or "", text)

    def test_include_through_a_macro(self):
        self.assertIn("rejected", self.line(f'#define H "{self.secret}"\n#include H') or "")

    def test_include_written_to_avoid_a_text_search(self):
        for text in ("#inc\\\nlude", "%:include", "??=include", "#/**/include", "  #  include", "#include_next", "#import"):
            self.assertIn("rejected", self.line(f'{text} "{self.secret}"') or "", text)

    def test_embed_and_assembler_and_line_directives(self):
        for text in (f'#embed "{self.secret}"', f'const char *s = ".incbin \\"{self.secret}\\"";', '#line 1 "x.c"'):
            self.assertIn("rejected", self.line(text) or "", text)

    def test_escape_split_over_two_edits(self):
        err = self.edit(("int main", "void __re\nint main"), ("__re\n", "__real_MsgSend(void);\n"))
        self.assertIn("rejected", err or "")

    def test_include_split_over_two_edits(self):
        err = self.edit(("int main", "#inc\nint main"), ("#inc\n", f'#include "{self.secret}"\n'))
        self.assertIn("rejected", err or "")

    def test_ordinary_includes_are_allowed(self):
        for text in ("#include <pthread.h>", "#include <sys/neutrino.h>", '#include "sys/neutrino.h"', '#include "../common/qd.h"'):
            self.assertIsNone(self.line(text), text)

    def test_edit_stays_in_the_scenario(self):
        other = self.put("outside/other.c", "int main(void);\n")
        for path in (other, "../x.c", "out/t1/a.c", "t1/../common/qd.h", "t1/missing.c"):
            self.assertIn("rejected", self.edit(("int main", "int  main"), path=path) or "", path)

    def test_malformed_actions_do_not_crash(self):
        for acts in ([{"type": "edit_file"}], ["x"], "x", {"a": 1}, [{"type": "edit_file", "path": 3, "find": "a", "replace": "b"}],
                     [{"type": "edit_file", "path": "t1/a.c", "find": "", "replace": "b"}]):
            work, err = hang.apply_fix(self.scen, acts)
            shutil.rmtree(work, True)
            self.assertIn("rejected", err or "", acts)

    def test_symlink_inside_a_scenario_is_not_copied(self):
        os.symlink(self.secret, os.path.join(self.scen, "notes.h"))
        with self.assertRaises(ValueError):
            shutil.rmtree(hang.prepare(self.scen), True)

    def test_build_error_text_is_not_returned(self):
        log = f't1/a.c:3:1: error: unknown type name "{MARK}"\n    3 | {MARK}\n{self.secret}:1:1: error: {MARK}\n'
        for stage in ("build", "image", "target"):
            why = hangdoctor.not_restarted({}, {"ok": False, "stage": stage, "log": log})
            self.assertNotIn(MARK, why, stage)
            self.assertNotIn(self.secret, why, stage)
        self.assertIn("t1/a.c:3", hangdoctor.not_restarted({}, {"ok": False, "stage": "build", "log": log}))


class Kernel(Dirs):
    """The barrier that does not depend on reading the source text."""

    def box(self, *argv, read=(), write=()):
        self.assertIsNotNone(sandbox, "no sandbox module")
        return sandbox.run(list(argv), self.work, {"PATH": "/usr/bin:/bin"}, read=[self.work, *read], write=write)

    @unittest.skipUnless(BOXED, "no kernel sandbox here")
    def test_reading_outside_is_denied(self):
        r = self.box("/usr/bin/cat", self.secret)
        self.assertNotEqual(r.returncode, 0)
        self.assertNotIn(MARK, r.output)
        self.assertEqual(self.box("/usr/bin/cat", "s1/a.c").returncode, 0)

    @unittest.skipUnless(BOXED, "no kernel sandbox here")
    def test_reading_outside_through_a_link_is_denied(self):
        os.symlink(self.secret, os.path.join(self.work, "l"))
        self.assertNotIn(MARK, self.box("/usr/bin/cat", "l").output)

    @unittest.skipUnless(BOXED, "no kernel sandbox here")
    def test_parent_environment_is_denied(self):
        r = self.box("/usr/bin/cat", f"/proc/{os.getpid()}/environ", read=["/proc"])
        self.assertNotEqual(r.returncode, 0)

    @unittest.skipUnless(BOXED, "no kernel sandbox here")
    def test_writing_outside_or_to_read_only_is_denied(self):
        self.assertNotEqual(self.box("/usr/bin/cp", "s1/a.c", os.path.join(self.top, "outside", "copy")).returncode, 0)
        self.assertNotEqual(self.box("/usr/bin/cp", "s1/a.c", "copy").returncode, 0)
        self.assertEqual(self.box("/usr/bin/cp", "s1/a.c", "local/copy", write=[os.path.join(self.work, "local")]).returncode, 0)

    @unittest.skipUnless(BOXED, "no kernel sandbox here")
    def test_sockets_are_denied(self):
        for args in ("", "socket.AF_INET, socket.SOCK_DGRAM", "socket.AF_UNIX"):
            r = self.box("/usr/bin/python3", "-I", "-c", f"import socket\nsocket.socket({args})\nprint('open')")
            self.assertNotEqual(r.returncode, 0, args)

    @unittest.skipUnless(BOXED, "no kernel sandbox here")
    def test_probe_is_boxed_even_if_the_argument_check_is_passed(self):
        self.assertTrue(hasattr(probes, "check"), "no argument check to pass")
        with mock.patch.object(probes, "check", return_value=None):
            self.assertNotIn(MARK, probes.probe(["cat", self.secret], self.work, self.env, True))

    def test_no_sandbox_means_no_run(self):
        self.assertIsNotNone(sandbox, "no sandbox module")
        with mock.patch.object(sandbox, "supported", return_value=False):
            r = sandbox.run(["/usr/bin/cat", "s1/a.c"], self.work, {"PATH": "/usr/bin:/bin"}, read=[self.work])
        self.assertNotEqual(r.returncode, 0)
        self.assertNotIn("int main", r.output)


class LicenceWatch(Dirs):
    """sandbox.foreign_opens on made-up strace lines (no licence file is used)."""

    def seen(self, *lines):
        self.assertIsNotNone(sandbox, "no sandbox module")
        return sandbox.foreign_opens("\n".join(lines), os.path.join(self.top, "lic"), "/opt/drv")

    def test_driver_may_read_and_others_may_not(self):
        f = os.path.join(self.top, "lic", "licenses")
        run = ['7 execve("/opt/drv", ["drv"], 0x1 /* 1 var */) = 0', f'7 openat(AT_FDCWD</w>, "{f}", O_RDONLY) = 3<{f}>']
        self.assertEqual(self.seen(*run), [])
        child = ['8 execve("/opt/cc1", ["cc1"], 0x1 /* 1 var */) = 0', f'8 openat(AT_FDCWD</w>, "{f}", O_RDONLY) = 3<{f}>']
        self.assertEqual(self.seen(*run, *child), ["cc1"])
        link = [child[0], f'8 openat(AT_FDCWD</w>, "l", O_RDONLY <unfinished ...>', f"8 <... openat resumed>) = 3<{f}>"]
        self.assertEqual(self.seen(*link), ["cc1"])
        self.assertEqual(self.seen(f'9 openat(AT_FDCWD</w>, "{f}", O_RDONLY) = 3<{f}>'), ["unknown"])

    def test_path_only_descriptor_is_not_a_read_and_cannot_be_faked_by_a_file_name(self):
        f = os.path.join(self.top, "lic", "licenses")
        self.assertEqual(self.seen(f'9 openat(AT_FDCWD</w>, "{f}", O_RDONLY|O_CLOEXEC|O_PATH) = 3<{f}>'), [])
        self.assertEqual(self.seen(f'9 openat(AT_FDCWD</w>, "x\\", O_PATH", O_RDONLY) = 3<{f}>'), ["unknown"])


    def test_scratch_is_only_this_runs_own_directory(self):
        self.assertIsNotNone(sandbox, "no sandbox module")

        def seen(path):
            return sandbox.foreign_opens('7 execve("/opt/drv", ["drv"], 0x1 /* 1 var */) = 0\n'
                                         '8 execve("/opt/cc1", ["cc1"], 0x1 /* 1 var */) = 0\n'
                                         f'8 openat(AT_FDCWD</w>, "{path}", O_RDONLY) = 3<{path}>',
                                         "/lic", "/opt/drv", "/tmp", ["/tmp/qd-hang-x"])
        self.assertEqual(seen("/tmp/fileAb3dE9_qcc_7/a.o"), [])
        self.assertEqual(seen("/tmp/qd-hang-x/s1/a.c"), [])
        self.assertEqual(seen("/tmp/fileAb3dE9_qcc_99/a.o"), ["cc1"])
        self.assertEqual(seen("/tmp/qd_v6_author/answers/labels.json"), ["cc1"])


class BuildDoctor(Dirs):
    @unittest.skipUnless(BOXED, "no kernel sandbox here")
    def test_a_proposed_fix_cannot_read_outside(self):
        scen = {"id": "x", "spec": {"argv": ["cat", "missing"], "cwd": "."}}
        res, msg = doctor.attempt(scen, [{"type": "replace_arg", "old": "missing", "new": self.secret}])
        self.assertNotIn(MARK, (res.output if res else "") + msg)

    def test_a_malformed_fix_does_not_crash(self):
        res, msg = doctor.attempt({"id": "x", "spec": {"argv": ["false"], "cwd": "."}}, [{"type": "edit_file"}])
        self.assertIn("rejected", msg)

    def test_copy_of_the_users_tree_does_not_follow_links(self):
        tree = os.path.join(self.top, "tree")
        os.makedirs(tree)
        os.symlink(self.secret, os.path.join(tree, "link"))
        work = doctor.setup({"id": "x", "copy_from": tree, "spec": {}})
        self.addCleanup(shutil.rmtree, work, True)
        self.assertTrue(os.path.islink(os.path.join(work, "link")))


class LicenceForDoctor(unittest.TestCase):
    def test_only_a_plain_compiler_call_gets_the_licence(self):
        before = {"argv": ["qcc", "-o", "a", "a.c"]}
        ok = lambda argv, **kw: runner.may_read_licence(before, {"argv": argv, **kw})  # noqa: E731
        self.assertTrue(ok(["qcc", "-o", "a", "a.c"], source_sdp=True))
        self.assertTrue(ok(["qcc", "-o", "a", "a.c", "-lsocket"]))
        for argv in (["qcc", "-o", "a", "a.c", "-wrapper", "x"], ["qcc", "@args", "-o", "a", "a.c"], ["sh", "-o", "a", "a.c"],
                     ["qcc", "-o", "a", "a.c", "-Wc,-fplugin=x"], ["qcc", "-o", "a"]):
            self.assertFalse(ok(argv), argv)
        self.assertFalse(ok(before["argv"], env={"PATH": "evil"}))
        self.assertFalse(runner.may_read_licence({"argv": ["make"]}, {"argv": ["make"]}))


class ModelShapes(unittest.TestCase):
    def test_probe_step_that_is_not_an_object(self):
        try:
            from qnx_doctor import ai
        except ImportError:
            self.skipTest("anthropic SDK not installed in this interpreter")
        left = iter(['{"probe": "ls"}', '{"diagnosis": "x"}', '{"give_up": "stop"}'])
        fake = NS(messages=NS(create=lambda **_: NS(content=[NS(type="text", text=next(left))])))
        with mock.patch.object(ai, "_client", return_value=fake), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(ai.think("c", ".", {}, None, [])[0], "give_up")


if __name__ == "__main__":
    unittest.main()
