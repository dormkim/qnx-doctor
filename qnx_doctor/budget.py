"""A hard cost cap for model calls. Every request is paid for in a ledger before it is sent.

Set QD_BUDGET_USD, QD_BUDGET_LEDGER, QD_PRICE_IN and QD_PRICE_OUT (USD per million tokens) together. With none of
them set a call is passed through unchanged (bench/run_sealed3.sh always sets them).

Before a request its worst case is reserved under a file lock: one input token per byte of the request plus
OVERHEAD, and max_tokens of output. If that does not fit, nothing is sent and the ledger refuses every later call.
Afterwards the reservation becomes what response.usage counted. A failed or killed request, and one without usage,
keeps the worst case. The cap is in the prices given here: with wrong prices it caps the wrong amount.
"""
import fcntl
import json
import math
import os
import time
import uuid

SETTINGS = ("QD_BUDGET_USD", "QD_BUDGET_LEDGER", "QD_PRICE_IN", "QD_PRICE_OUT")
OVERHEAD = 4096   # tokens the API adds around a request (framing, thinking instructions)
CACHE_RATE = 2    # cache tokens are not used here; if counted, they are charged at twice the input price
WAITS = (5, 20)   # seconds before the second and the third attempt
_sleep = time.sleep


class BudgetStop(BaseException):
    """Not an Exception: a handler for a bad model reply must not turn a stop into a row."""


def _settings():
    values = [os.environ.get(k) for k in SETTINGS]
    if all(v is None for v in values):
        return None
    usd, path, pin, pout = values
    try:
        nums = [float(v) for v in (usd, pin, pout)]
    except (TypeError, ValueError):
        raise BudgetStop("budget settings are incomplete or not numbers") from None
    if not path or not all(math.isfinite(n) and n > 0 for n in nums):
        raise BudgetStop("budget settings must be positive, with a ledger path")
    return (nums[0], path, nums[1], nums[2])


def _plain(obj):
    dump = getattr(obj, "model_dump", None)
    return dump(mode="json") if dump else vars(obj)


def input_bound(kw: dict) -> int:
    return len(json.dumps(kw, ensure_ascii=False, default=_plain).encode()) + OVERHEAD


def worst_usd(kw: dict, pin: float, pout: float) -> float:
    return (input_bound(kw) * pin + kw["max_tokens"] * pout) / 1e6


def _read(f):
    """(what each request costs so far, whether the ledger is stopped)"""
    f.seek(0)
    cost, stopped = {}, False
    for line in f:
        e = json.loads(line)
        if e.get("stop"):
            stopped = True
            continue
        usd = e["usd"]
        if not (math.isfinite(usd) and usd >= 0):
            raise ValueError("bad amount")
        cost[e["id"]] = usd
    return cost, stopped


def spent(path: str) -> float:
    if not os.path.exists(path):
        return 0.0
    with open(path) as f:
        fcntl.flock(f, fcntl.LOCK_SH)
        return sum(_read(f)[0].values())


def _book(path: str, decide):
    """Run decide(cost, stopped) -> (entry, why to stop) under the lock and write its entry."""
    try:
        with open(path, "a+") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            entry, why = decide(*_read(f))
            if entry:
                f.write(json.dumps(entry, allow_nan=False) + "\n")
                f.flush()
                os.fsync(f.fileno())
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as e:
        raise BudgetStop(f"budget ledger unusable: {type(e).__name__}") from None
    if why:
        raise BudgetStop(why)


def _reserve(cap, path, rid, usd):
    def decide(cost, stopped):
        if stopped:
            return None, "budget already stopped"
        if sum(cost.values()) + usd > cap:
            return {"stop": "cap", "refused_usd": usd}, f"budget cap {cap} USD: the next request could cross it"
        return {"id": rid, "usd": usd}, None
    _book(path, decide)


def _count(usage, name, default=None):
    v = getattr(usage, name, None)
    if v is None:
        return default
    return v if type(v) is int and v >= 0 else None


def _settle(path, rid, reserved, usage, pin, pout):
    inp, out = _count(usage, "input_tokens"), _count(usage, "output_tokens")
    made, read = _count(usage, "cache_creation_input_tokens", 0), _count(usage, "cache_read_input_tokens", 0)
    if None in (inp, out, made, read):
        return  # not counted: the reservation stays
    usd = ((inp + CACHE_RATE * (made + read)) * pin + out * pout) / 1e6
    if usd > reserved * (1 + 1e-9):
        _book(path, lambda cost, stopped: ({"id": rid, "usd": usd}, None))
        _book(path, lambda cost, stopped: ({"stop": "bound"}, "a request cost more than its bound"))
    _book(path, lambda cost, stopped: ({"id": rid, "usd": usd}, None))


def _again(e: Exception) -> bool:
    status = getattr(e, "status_code", None)
    if isinstance(status, int):
        return status in (408, 409, 429) or status >= 500
    return type(e).__name__ in ("APIConnectionError", "APITimeoutError")


def create(client, **kw):
    """The only place that sends a model request."""
    conf = _settings()
    if conf is None:
        return client.messages.create(**kw)
    cap, path, pin, pout = conf
    client = client.with_options(max_retries=0)  # the SDK's own retries would be requests nobody reserved
    usd = worst_usd(kw, pin, pout)
    for wait in (*WAITS, None):
        rid = uuid.uuid4().hex
        _reserve(cap, path, rid, usd)
        try:
            resp = client.messages.create(**kw)
        except Exception as e:
            if wait is None or not _again(e):
                raise
            _sleep(wait)
            continue
        _settle(path, rid, usd, getattr(resp, "usage", None), pin, pout)
        return resp
