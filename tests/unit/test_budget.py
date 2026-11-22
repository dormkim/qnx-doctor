"""The hard cost cap (qnx_doctor/budget.py). Fake clients and a server on 127.0.0.1 only: no key, no API request."""
import ast
import contextlib
import glob
import http.server
import importlib.util
import io
import json
import multiprocessing
import os
import shutil
import tempfile
import threading
import time
import unittest
from types import SimpleNamespace as NS
from unittest import mock

from qnx_doctor import budget

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
KW = {"model": "fake", "max_tokens": 1000, "messages": [{"role": "user", "content": "hello"}]}


class Fake:
    """Counts requests; `replies` are returned or raised in order, then the last one again."""
    def __init__(self, *replies, log=None, delay=0):
        self.replies, self.n, self.retries, self.log, self.delay = list(replies) or [resp()], 0, None, log, delay
        self.messages = NS(create=self.create)

    def with_options(self, max_retries):
        self.retries = max_retries
        return self

    def create(self, **kw):
        r = self.replies[min(self.n, len(self.replies) - 1)]
        self.n += 1
        time.sleep(self.delay)
        if self.log:
            with open(self.log, "a") as f:
                f.write("call\n")
        if isinstance(r, BaseException):
            raise r
        return r


def resp(inp=10, out=20, **more):
    return NS(content=[NS(type="text", text='{"give_up": "no"}')], usage=NS(input_tokens=inp, output_tokens=out, **more))


class ApiError(Exception):
    def __init__(self, status):
        super().__init__(str(status))
        self.status_code = status


def worker(log):
    try:
        for _ in range(10):
            budget.create(Fake(NS(content=[], usage=None), log=log, delay=0.01), **KW)
    except budget.BudgetStop:
        pass


class Base(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.t, True)
        self.ledger = os.path.join(self.t, "budget.jsonl")
        self.env(1)
        p = mock.patch.object(budget, "_sleep", lambda s: None)
        p.start()
        self.addCleanup(p.stop)

    def env(self, cap, **change):
        values = {"QD_BUDGET_USD": str(cap), "QD_BUDGET_LEDGER": self.ledger, "QD_PRICE_IN": "4", "QD_PRICE_OUT": "20", **change}
        p = mock.patch.dict(os.environ, values)
        p.start()
        self.addCleanup(p.stop)

    def worst(self):
        return budget.worst_usd(KW, 4, 20)


class Cap(Base):
    def test_call_over_the_cap_is_never_sent(self):
        self.env(self.worst() * 0.99)
        c = Fake()
        with self.assertRaises(budget.BudgetStop):
            budget.create(c, **KW)
        self.assertEqual(c.n, 0)

    def test_a_stop_holds_for_every_later_call(self):
        self.env(self.worst() * 0.99)
        with self.assertRaises(budget.BudgetStop):
            budget.create(Fake(), **KW)
        self.env(100)
        c = Fake()
        with self.assertRaises(budget.BudgetStop):
            budget.create(c, **KW)
        self.assertEqual(c.n, 0)

    def test_success_is_charged_as_counted(self):
        budget.create(Fake(resp(100, 200)), **KW)
        self.assertAlmostEqual(budget.spent(self.ledger), (100 * 4 + 200 * 20) / 1e6)

    def test_cache_tokens_are_charged_high(self):
        budget.create(Fake(resp(100, 200, cache_creation_input_tokens=50, cache_read_input_tokens=50)), **KW)
        self.assertAlmostEqual(budget.spent(self.ledger), ((100 + 2 * 100) * 4 + 200 * 20) / 1e6)

    def test_missing_usage_keeps_the_worst_case(self):
        for r in (NS(content=[], usage=None), resp(None, 5), resp(5, None)):
            before = budget.spent(self.ledger)
            budget.create(Fake(r), **KW)
            self.assertAlmostEqual(budget.spent(self.ledger) - before, self.worst())

    def test_each_retry_is_paid_for_and_the_sdk_does_not_retry(self):
        c = Fake(ApiError(529), ApiError(500), resp(100, 200))
        budget.create(c, **KW)
        self.assertEqual((c.n, c.retries), (3, 0))
        self.assertAlmostEqual(budget.spent(self.ledger), 2 * self.worst() + (100 * 4 + 200 * 20) / 1e6)

    def test_retry_cannot_cross_the_cap(self):
        self.env(self.worst() * 1.5)
        c = Fake(ApiError(529))
        with self.assertRaises(budget.BudgetStop):
            budget.create(c, **KW)
        self.assertEqual(c.n, 1)

    def test_retries_end(self):
        c = Fake(ApiError(529))
        with self.assertRaises(ApiError):
            budget.create(c, **KW)
        self.assertEqual(c.n, 3)

    def test_client_error_is_not_retried(self):
        c = Fake(ApiError(400))
        with self.assertRaises(ApiError):
            budget.create(c, **KW)
        self.assertEqual(c.n, 1)

    def test_crash_during_a_call_keeps_the_worst_case(self):
        with self.assertRaises(KeyboardInterrupt):
            budget.create(Fake(KeyboardInterrupt()), **KW)
        self.assertAlmostEqual(budget.spent(self.ledger), self.worst())

    def test_usage_above_the_bound_stops_everything(self):
        with self.assertRaises(budget.BudgetStop):
            budget.create(Fake(resp(10 ** 6, 20)), **KW)
        c = Fake()
        with self.assertRaises(budget.BudgetStop):
            budget.create(c, **KW)
        self.assertEqual(c.n, 0)

    def test_bad_settings_send_nothing(self):
        for name in ("QD_BUDGET_USD", "QD_PRICE_IN", "QD_PRICE_OUT", "QD_BUDGET_LEDGER"):
            for bad in ("", "0", "-1", "nan", "inf", "abc") if name != "QD_BUDGET_LEDGER" else ("",):
                c = Fake()
                with mock.patch.dict(os.environ, {name: bad}), self.assertRaises(budget.BudgetStop, msg=(name, bad)):
                    budget.create(c, **KW)
                self.assertEqual(c.n, 0)

    def test_damaged_ledger_sends_nothing(self):
        for text in ("not json\n", '{"id": "a", "usd": -5}\n', '{"id": "a", "usd": NaN}\n', "[]\n"):
            with open(self.ledger, "w") as f:
                f.write(text)
            c = Fake()
            with self.assertRaises(budget.BudgetStop, msg=text):
                budget.create(c, **KW)
            self.assertEqual(c.n, 0)

    def test_unwritable_ledger_sends_nothing(self):
        self.env(1, QD_BUDGET_LEDGER=os.path.join(self.t, "no", "dir", "x"))
        c = Fake()
        with self.assertRaises(budget.BudgetStop):
            budget.create(c, **KW)
        self.assertEqual(c.n, 0)

    def test_an_exception_handler_does_not_swallow_the_stop(self):
        self.assertFalse(issubclass(budget.BudgetStop, Exception))

    def test_the_ledger_holds_no_request_text(self):
        budget.create(Fake(), **{**KW, "messages": [{"role": "user", "content": "private-marker"}]})
        with open(self.ledger) as f:
            self.assertNotIn("private-marker", f.read())

    def test_processes_share_one_cap(self):
        self.env(self.worst() * 5.5)
        log = os.path.join(self.t, "calls")
        ctx = multiprocessing.get_context("fork")
        ps = [ctx.Process(target=worker, args=(log,)) for _ in range(8)]
        for p in ps:
            p.start()
        for p in ps:
            p.join(30)
        with open(log) as f:
            self.assertEqual(len(f.readlines()), 5)
        self.assertLessEqual(budget.spent(self.ledger), self.worst() * 5.5)

    def test_without_settings_the_call_is_unchanged(self):
        with mock.patch.dict(os.environ):
            for k in budget.SETTINGS:
                os.environ.pop(k, None)
            c = Fake()
            budget.create(c, **KW)
        self.assertEqual((c.n, c.retries), (1, None))
        self.assertFalse(os.path.exists(self.ledger))


class CallSites(Base):
    def test_no_call_goes_around_the_cap(self):
        seen = []
        for path in glob.glob(os.path.join(ROOT, "**", "*.py"), recursive=True):
            rel = os.path.relpath(path, ROOT)
            if rel.startswith(("tests" + os.sep, ".venv", "runs" + os.sep)) or rel == os.path.join("qnx_doctor", "budget.py"):
                continue
            with open(path) as f:
                tree = ast.parse(f.read())
            for n in ast.walk(tree):
                if isinstance(n, ast.Attribute) and n.attr in ("create", "stream", "parse") and \
                        isinstance(n.value, ast.Attribute) and n.value.attr in ("messages", "batches"):
                    seen.append((rel, n.lineno))
        self.assertEqual(seen, [])

    @unittest.skipUnless(importlib.util.find_spec("anthropic"), "anthropic SDK not installed in this interpreter")
    def test_both_arms_stop(self):
        import sys
        sys.path.insert(0, os.path.join(ROOT, "bench"))
        import naive_hang
        from qnx_doctor import ai
        self.env(0.000001)
        c = Fake()
        with mock.patch.object(ai, "_client", return_value=c), self.assertRaises(budget.BudgetStop):
            ai.think("context", ".", {}, None, [])
        with mock.patch("anthropic.Anthropic", return_value=c), self.assertRaises(budget.BudgetStop):
            naive_hang.ask("context")
        self.assertEqual(c.n, 0)


@unittest.skipUnless(importlib.util.find_spec("anthropic"), "anthropic SDK not installed in this interpreter")
class RealSdk(Base):
    def serve(self, answers):
        seen = []

        class H(http.server.BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_POST(self):
                seen.append(self.rfile.read(int(self.headers["content-length"])))
                code, body = answers[min(len(seen) - 1, len(answers) - 1)]
                data = json.dumps(body).encode()
                self.send_response(code)
                self.send_header("content-type", "application/json")
                self.send_header("content-length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

        s = http.server.HTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=s.serve_forever, daemon=True).start()
        self.addCleanup(s.server_close)
        self.addCleanup(s.shutdown)
        from anthropic import Anthropic
        c = Anthropic(api_key="dummy-not-a-key", base_url=f"http://127.0.0.1:{s.server_port}")
        self.addCleanup(c.close)
        return c, seen

    def test_sdk_sends_one_request_per_reservation(self):
        self.env(10)
        c, seen = self.serve([(529, {"type": "error", "error": {"type": "overloaded_error", "message": "x"}})])
        from anthropic import APIStatusError
        with self.assertRaises(APIStatusError):
            budget.create(c, **KW)
        self.assertEqual(len(seen), 3)
        self.assertAlmostEqual(budget.spent(self.ledger), 3 * self.worst())

    def test_bound_covers_the_bytes_the_sdk_sends(self):
        self.env(10)
        ok = {"id": "m", "type": "message", "role": "assistant", "model": "fake", "stop_reason": "end_turn",
              "stop_sequence": None, "usage": {"input_tokens": 10, "output_tokens": 20},
              "content": [{"type": "thinking", "thinking": "t" * 500, "signature": "s" * 3000},
                          {"type": "text", "text": "한글과 \"따옴표\"\n" * 50}]}
        c, seen = self.serve([(200, ok)])
        first = budget.create(c, **KW)
        kw = {**KW, "messages": KW["messages"] + [{"role": "assistant", "content": first.content}, {"role": "user", "content": "next"}]}
        budget.create(c, **kw)
        self.assertGreaterEqual(budget.input_bound(kw), len(seen[1]))


if __name__ == "__main__":
    unittest.main()
