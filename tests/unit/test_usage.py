"""Per-call response.usage (2026-11-22, bench/V6_PLAN.md section 5). Fake responses only: the client class is replaced
in every test, so no request is made."""
import contextlib
import importlib.util
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from types import SimpleNamespace as NS
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "bench"))
import naive_hang as nh  # noqa: E402
import score_structure as ss  # noqa: E402

HAVE_SDK = importlib.util.find_spec("anthropic") is not None


def reply(text, inp=100, out=20, thinking=7):
    """The SDK's own Message type, so a renamed field fails here and not in the one paid run."""
    from anthropic.types import Message
    return Message.model_validate({
        "id": "msg_fake", "type": "message", "role": "assistant", "model": "fake-model", "stop_reason": "end_turn",
        "stop_sequence": None, "content": [{"type": "text", "text": text}],
        "usage": {"input_tokens": inp, "output_tokens": out, "cache_creation_input_tokens": 0,
                  "cache_read_input_tokens": 0, "output_tokens_details": {"thinking_tokens": thinking}}})


def client(replies):
    left = iter(replies)

    def create(**_):
        r = next(left)
        if isinstance(r, Exception):
            raise r
        return r
    return NS(messages=NS(create=create))


@unittest.skipUnless(HAVE_SDK, "anthropic SDK not installed in this interpreter")
class OurArm(unittest.TestCase):
    def think(self, replies, **kw):
        from qnx_doctor import ai
        log, err = [], io.StringIO()
        with mock.patch.object(ai, "_client", return_value=client(replies)), contextlib.redirect_stderr(err):
            try:
                kind = ai.think("context", ".", {}, None, log, **kw)[0]
            except RuntimeError:
                kind = "raised"
        printed = [json.loads(x[len("qd-usage "):]) for x in err.getvalue().splitlines() if x.startswith("qd-usage ")]
        return kind, [t for t in log if t.get("kind") == "usage"], printed, log

    def test_one_record_per_call(self):
        kind, used, printed, log = self.think([reply('{"search_docs": "x"}', 100), reply("not json", 200),
                                               reply('{"diagnosis": {"cause": "c", "actions": []}}', 300)])
        self.assertEqual(kind, "diagnosis")
        self.assertEqual([u["input_tokens"] for u in used], [100, 200, 300])  # the unreadable one is counted too
        self.assertEqual(printed, used)
        self.assertEqual([t["kind"] for t in log], ["usage", "docs", "usage", "usage"])
        self.assertEqual(used[0], {"kind": "usage", "model": "fake-model", "stop_reason": "end_turn", "input_tokens": 100,
                                   "output_tokens": 20, "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0,
                                   "thinking_tokens": 7})

    def test_give_up_and_turn_limit(self):
        self.assertEqual(len(self.think([reply('{"give_up": "no"}')])[1]), 1)
        kind, used, _, _ = self.think([reply("?"), reply("?")], max_turns=2)
        self.assertEqual((kind, len(used)), ("give_up", 2))

    def test_earlier_calls_survive_a_failed_call(self):
        kind, used, printed, _ = self.think([reply('{"search_docs": "x"}'), RuntimeError("fake API error")])
        self.assertEqual((kind, len(used), len(printed)), ("raised", 1, 1))

    def test_no_usage_is_none_not_zero(self):
        bare = NS(content=[NS(type="text", text='{"give_up": "no"}')])
        used = self.think([bare])[1][0]
        self.assertEqual((used["input_tokens"], used["output_tokens"], used["thinking_tokens"]), (None, None, None))


@unittest.skipUnless(HAVE_SDK, "anthropic SDK not installed in this interpreter")
class Baseline(unittest.TestCase):
    def setUp(self):
        self.pool = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.pool, True)
        os.makedirs(os.path.join(self.pool, "u1"))
        with open(os.path.join(self.pool, "u1", "a.c"), "w") as f:
            f.write("int main(void){for(;;);}\n")

    def one(self, replies, **kw):
        with mock.patch("anthropic.Anthropic", return_value=client(replies)), contextlib.redirect_stderr(io.StringIO()), \
                mock.patch.object(nh, "_try", return_value=({"solved": False, "result": "still hung"}, "still hung")):
            return nh.one(self.pool, "u1", {"d0a": 1}, 1, **kw)

    def test_both_tries_are_recorded(self):
        fix = json.dumps({"kind": "deadlock", "actions": [{"type": "edit_file", "path": "u1/a.c", "find": "x", "replace": "y"}]})
        row = self.one([reply(fix, 111), reply(fix, 222)], attempts=2)
        self.assertEqual([u["input_tokens"] for u in row["usage"]], [111, 222])

    def test_unreadable_reply_is_recorded(self):
        row = self.one([reply("no idea", 333)])
        self.assertEqual((row["detected"], row["usage"][0]["input_tokens"]), (None, 333))

    def test_models_own_usage_key_is_not_taken(self):
        row = self.one([reply('{"kind": "none", "usage": {"input_tokens": 1}}', 444)])
        self.assertEqual([u["input_tokens"] for u in row["usage"]], [444])


class Scorer(unittest.TestCase):
    def test_usage_entries_do_not_move_a_score(self):
        graph = {"kind": "graph", "ticks": {"d0a": 1}}
        fix = {"kind": "ai_fix", "result": "still hung", "live": False}
        base = {"id": "a", "detected": "deadlock", "solved": False}
        plain = ss.rows_from([{**base, "timeline": [graph, fix]}])
        logged = ss.rows_from([{**base, "timeline": [graph, {"kind": "usage", "input_tokens": 5}, fix]}])
        self.assertEqual(plain, logged)


if __name__ == "__main__":
    unittest.main()
