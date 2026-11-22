"""bench/run_sealed3.sh as the v6 runner (blocker 5). Everything is a stand-in in a temporary directory: a fake HOME
with a dummy env file and a fake python. No scenario, boot or model call."""
import os
import shutil
import subprocess
import tempfile
import unittest

SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "bench", "run_sealed3.sh")
FAKE = r'''#!/usr/bin/env bash
args="$*"; out=""; prev=""
for a in "$@"; do [ "$prev" = "--out" ] && out=$a; prev=$a; done
case "$args" in
  *score_structure*) arm=score ;;
  *naive_hang*--attempts*) arm=naive_x2 ;;
  *naive_hang*) arm=naive ;;
  *--no-ai*) arm=code ;;
  *) arm=ai ;;
esac
echo "$arm SMP=${QD_SMP:-} MODEL=${QD_MODEL:-} KEY=${ANTHROPIC_API_KEY:+set} URL=${ANTHROPIC_BASE_URL:-} TOKEN=${ANTHROPIC_AUTH_TOKEN:-} CAP=${QD_BUDGET_USD:-} IN=${QD_PRICE_IN:-} OUT=${QD_PRICE_OUT:-} LEDGER=${QD_BUDGET_LEDGER:-} ARGS=$args" >> "$HOME/calls"
[ "$(cat "$HOME/fail" 2>/dev/null)" = "$arm" ] && exit 7
if [ -n "$out" ]; then
  echo '{"id": "s1", "timeline": [{"kind": "graph"}]}' > "$out"
  [ "$(cat "$HOME/short" 2>/dev/null)" = "$arm" ] || echo '{"id": "s2", "timeline": [{"kind": "graph"}]}' >> "$out"
fi
exit 0
'''


@unittest.skipUnless(shutil.which("bash"), "no bash")
class Runner(unittest.TestCase):
    def setUp(self):
        self.t = os.path.realpath(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.t, True)
        # old and new script alike find the repository at $HOME/personal/qnx-doctor
        self.repo = os.path.join(self.t, "personal", "qnx-doctor")
        self.write("personal/qnx-doctor/bench/run_sealed3.sh", open(SCRIPT).read())
        self.py = self.write("personal/qnx-doctor/.venv/bin/python", FAKE, 0o755)
        for s in ("s1", "s2", "common"):
            self.write(f"set/pool/{s}/x", "")
        self.write("set/answers/labels.json", "{}")
        self.envfile("ANTHROPIC_API_KEY=dummy-not-a-key\n")

    def write(self, rel, text, mode=0o644):
        p = os.path.join(self.t, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w") as f:
            f.write(text)
        os.chmod(p, mode)
        return p

    def envfile(self, text):
        self.write(".config/qnx-doctor/env", text)

    def run_it(self, out="out", **extra):
        env = {"HOME": self.t, "PATH": "/usr/bin:/bin", "QD_BUDGET_USD": "40", "QD_PRICE_IN": "4", "QD_PRICE_OUT": "20", **extra}
        p = subprocess.run(["bash", os.path.join(self.repo, "bench", "run_sealed3.sh"), os.path.join(self.t, "set", "pool"),
                            os.path.join(self.t, "set", "answers", "labels.json"), os.path.join(self.t, out)],
                           env=env, capture_output=True, text=True, timeout=30, cwd=self.t)
        return p.returncode

    def read(self, rel):
        p = os.path.join(self.t, rel)
        return open(p).read() if os.path.exists(p) else ""

    def arm(self, name):
        return next(l for l in self.read("calls").splitlines() if l.startswith(name + " "))

    def test_planned_flags(self):
        self.assertEqual(self.run_it(), 0)
        self.assertEqual(self.read("out/state").strip(), "done")
        for a in ("code", "ai", "naive", "naive_x2"):
            self.assertIn("SMP=1", self.arm(a))
            self.assertIn("MODEL=claude-opus-5-5", self.arm(a))
        for a in ("naive", "naive_x2"):
            self.assertIn("--allow-unknown", self.arm(a))

    def test_any_failed_arm_is_not_done(self):
        for a in ("code", "ai", "naive", "naive_x2", "score"):
            self.write("fail", a)
            self.assertNotEqual(self.run_it(out="out_" + a), 0, a)
            self.assertTrue(self.read(f"out_{a}/state").startswith("fail"), a)
            if a != "score":
                self.assertNotIn("score ", self.read("calls"), a)

    def test_an_arm_that_wrote_too_few_rows_is_not_done(self):
        for a in ("code", "ai", "naive"):
            self.write("short", a)
            self.assertNotEqual(self.run_it(out="out_" + a), 0, a)
            self.assertTrue(self.read(f"out_{a}/state").startswith("fail"), a)

    def test_empty_key_stops_before_anything_runs(self):
        for text in ("", "ANTHROPIC_API_KEY=\n"):
            self.envfile(text)
            self.assertNotEqual(self.run_it(out=f"out_{len(text)}", ANTHROPIC_API_KEY="from-the-calling-shell"), 0)
        self.assertEqual(self.read("calls"), "")

    def test_missing_env_file_stops(self):
        os.remove(os.path.join(self.t, ".config", "qnx-doctor", "env"))
        self.assertNotEqual(self.run_it(ANTHROPIC_API_KEY="from-the-calling-shell"), 0)
        self.assertEqual(self.read("calls"), "")

    def test_callers_shell_does_not_choose_account_model_or_endpoint(self):
        self.assertEqual(self.run_it(ANTHROPIC_BASE_URL="http://elsewhere", ANTHROPIC_AUTH_TOKEN="t", QD_MODEL="other", QD_SMP="2"), 0)
        line = self.arm("ai")
        self.assertIn("URL= ", line)
        self.assertIn("TOKEN= ", line)
        self.assertIn("MODEL=claude-opus-5-5", line)

    def test_used_directory_is_refused_and_left_alone(self):
        self.write("out/state", "fail:fix\n")
        self.assertNotEqual(self.run_it(), 0)
        self.assertEqual(self.read("out/state"), "fail:fix\n")
        self.assertEqual(self.read("calls"), "")

    def test_no_cap_or_price_stops_before_anything_runs(self):
        for name in ("QD_BUDGET_USD", "QD_PRICE_IN", "QD_PRICE_OUT"):
            for i, bad in enumerate(("", "0", "0.00", "-3", "nan", "$40", "1e9")):
                out = f"out_{name}_{i}"
                self.assertNotEqual(self.run_it(out=out, **{name: bad}), 0, (name, bad))
                self.assertFalse(os.path.exists(os.path.join(self.t, out)), "the run-once directory must stay unused")
        self.assertEqual(self.read("calls"), "")

    def test_every_arm_shares_the_cap_and_one_ledger(self):
        self.assertEqual(self.run_it(), 0)
        for a in ("ai", "naive", "naive_x2"):
            self.assertIn(f"CAP=40 IN=4 OUT=20 LEDGER={self.t}/out/budget.jsonl ", self.arm(a))

    def test_env_file_cannot_change_the_cap(self):
        self.envfile("ANTHROPIC_API_KEY=dummy-not-a-key\nQD_BUDGET_USD=999\nQD_PRICE_OUT=0.01\nQD_BUDGET_LEDGER=/dev/null\n")
        self.assertEqual(self.run_it(), 0)
        self.assertIn(f"CAP=40 IN=4 OUT=20 LEDGER={self.t}/out/budget.jsonl ", self.arm("naive"))

    def test_runs_the_checkout_it_belongs_to(self):
        other = os.path.join(self.t, "freeze")
        shutil.copytree(self.repo, other, symlinks=True)
        shutil.rmtree(self.repo)
        self.repo = other
        self.assertEqual(self.run_it(), 0)


if __name__ == "__main__":
    unittest.main()
