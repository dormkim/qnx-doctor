"""Naive baseline for the hang doctor: the same model reads only what a developer has without qnx-doctor —
the program's source and its logs (TICK counts per role) — and guesses the cause and a fix in one reply (or, with --attempts 2, gets one more try after
seeing the rerun's TICK counts and the verifier's verdict, like our arm's retry, but never the wait graph).
No pidin snapshot, no wait graph, no docs search, no probes. Its fix (edit_file) goes through the same check
as ours: apply to a fresh copy → qcc → boot → rerun; «fixed» only if the rerun shows no cycle/chain and the
stopped loop ticks again. The answer key (labels.json) is never read here; bench/score_hang.py does that.

  python3 bench/naive_hang.py --pool DIR --code runs/x_code.jsonl --out runs/x_naive.jsonl
  python3 bench/naive_hang.py --pool DIR --code runs/x_code.jsonl --out runs/x_naive2.jsonl --attempts 2   # + same retries
`--code` = the AI-off run of the same scenarios; only its TICK counts are used (the logs a developer would see).

`--allow-unknown` (2026-11-21, for sealed v6; not used in any run up to v5): the baseline gets a fifth answer,
«unknown», with the meaning our tool gives the word. Up to v5 it had four words, so on an «unknown» label it could
only score 0 (v5: the whole 10:8 gap was two such labels, where the baseline's free text had the cause right). With
the flag, «unknown» is scored like ours: a hit on an «unknown» label, a false alarm on a healthy one, and no fix is
tried. Design and the reason for the wording: bench/V6_PLAN.md.
"""
import argparse
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from qnx_doctor import hang  # noqa: E402
from qnx_doctor import structure as st  # noqa: E402
from qnx_doctor.hangdoctor import result_text, verdict  # noqa: E402

KINDS = ("deadlock", "priority_chain", "missing_reply", "none")
NAIVE_SYSTEM = """You are an experienced QNX 8.0 developer. A message-passing program was started on the target with
run.sh. You have its source files and its logs: for each role log, how many TICK lines it printed in the observation
window (a working loop prints TICK lines; 0 = that loop printed nothing). You have no other tools or observations.
Decide what is wrong. Reply with exactly ONE JSON object, nothing else:
  {"kind": "deadlock" | "priority_chain" | "missing_reply" | "none", "roles": ["role names involved"], "cause": "short cause",
   "actions": [{"type": "edit_file", "path": "relative path", "find": "exact text", "replace": "new text"}]}
kind: deadlock = processes wait on each other in a cycle of synchronous messages; priority_chain = a high-priority
client waits on a low-priority server that cannot get the CPU (priority inversion); missing_reply = a server received
a message on a code path that never replies, so its client waits forever; none = nothing is hung (long
waits can be normal). For none give no actions. Only edit_file actions, paths relative to the working directory,
`find` copied exactly from the file. Keep the program's intent; a timeout or sleep that only hides the wait is not a fix.
""" + st.RULES


UNKNOWN = "unknown"
FIXABLE = ("deadlock", "priority_chain", "missing_reply")  # only these are followed by a rerun
# The fifth answer, in the words of our own tool's «unknown» (progress.classify: stopped, but not one of the three
# kinds, or not enough to tell). Appended to the kind list and the kind text; nothing else in the prompt changes.
UNKNOWN_KIND = ' | "unknown"'
UNKNOWN_TEXT = ("; unknown = a loop that should run has stopped, but the cause is not one of these three kinds or cannot "
                "be decided from what you have (for example a CPU loop, a wait outside message passing, or a cause "
                "that is not in the given sources). For none and unknown give no actions.")


def kinds(allow_unknown: bool = False) -> tuple:
    return KINDS + (UNKNOWN,) if allow_unknown else KINDS


def system_prompt(allow_unknown: bool = False) -> str:
    """The baseline's instructions. Without the flag: byte for byte the prompt of every run up to v5."""
    if not allow_unknown:
        return NAIVE_SYSTEM
    out = NAIVE_SYSTEM.replace('| "none", "roles"', '| "none"' + UNKNOWN_KIND + ', "roles"', 1)
    out = out.replace("waits can be normal). For none give no actions.", "waits can be normal)" + UNKNOWN_TEXT, 1)
    if UNKNOWN_TEXT not in out or UNKNOWN_KIND not in out:  # the base prompt was reworded: do not run with half a prompt
        raise ValueError("NAIVE_SYSTEM no longer has the text the unknown wording is attached to")
    return out


def read_reply(text: str, allowed: tuple = KINDS) -> dict:
    """The model's reply as a row. An unreadable reply or a word outside `allowed` is a wrong answer, not a crash."""
    from qnx_doctor.ai import _json
    try:
        out = _json(text)
    except Exception as e:
        return {"kind": None, "error": f"no JSON: {e}", "actions": []}
    if out.get("kind") not in allowed:
        out["error"] = f"kind not in {allowed}: {out.get('kind')!r}"
    return out


def ask(context: str, allow_unknown: bool = False) -> dict:
    from anthropic import Anthropic
    from qnx_doctor import budget
    from qnx_doctor.ai import MODEL, usage_record
    resp = budget.create(Anthropic(), model=MODEL, max_tokens=4000, system=system_prompt(allow_unknown),
                         thinking={"type": "adaptive"}, messages=[{"role": "user", "content": context}])
    used = usage_record(resp)  # before the reply is read: an unreadable reply is billed too
    out = read_reply("".join(b.text for b in resp.content if getattr(b, "type", "") == "text"), kinds(allow_unknown))
    out["usage"] = used  # written last: a «usage» key in the model's own JSON never stands in for the API's count
    return out


def _feedback(res, v, err):
    """What a developer sees after trying a fix without qnx-doctor: whether it built, the TICK counts of the
    rerun and the verifier's verdict text. Never the wait graph or pidin lines (those are what our arm adds)."""
    if err:
        return err
    if not res.get("ok"):
        return f"{res.get('stage')} failed"
    state = ("fixed" if v["fixed"] else
             "came back alive but the message structure changed: " + "; ".join(v["structure"]) if v["live"] else
             _plain(v["why_not_live"]))
    return f"{state}; TICK counts per role log after the rerun: {json.dumps(res.get('ticks'))}"


def _plain(why: str) -> str:
    """The failed condition without the wait graph: «still hung: <graph text>» is cut to «still hung» (the graph is
    what our arm adds); the other conditions speak of TICK counts and processes only, which a developer sees too."""
    return "still hung (a wait cycle, chain or lost reply is still there)" if str(why).startswith("still hung") else str(why)


def _try(scen, sid, acts, ticks, alive, structure, progress=None):
    fixed, err = hang.apply_fix(scen, acts)
    try:
        if err:
            return {"solved": False, "result": err, "static_reject": err.startswith(st.STATIC)}, _feedback(None, None, err)
        res = hang.observe(fixed, sid)
        v = verdict({"ticks": ticks, "alive": alive or 0, "structure": structure, "progress": progress}, res)
        row = {"solved": v["fixed"], "live": v["live"], "structure_why": v["structure"], "unread": v["unread"],
               "result": "rerun: no cycle/chain, loop ticks again, same message structure" if v["fixed"] else
               "rejected: alive again but the message structure changed" if v["live"] else result_text(v)}
        if res.get("ok"):  # states for the scorer's loop_logs rule (sealed v3), same fields as our arm's timeline
            row["rerun_tick_counts"] = res.get("ticks")
            row["rerun_alive"], row["rerun_progress"] = res.get("alive"), res.get("progress")  # since 2026-11-21
            row["rerun_structure"] = res.get("structure")  # since 2026-11-22, as in our arm's timeline
        return row, _feedback(res, v, None)
    finally:
        shutil.rmtree(fixed, ignore_errors=True)


def one(pool: str, sid: str, ticks: dict, alive, structure=None, attempts: int = 1, progress=None,
        allow_unknown: bool = False, ask=None) -> dict:
    """attempts=1 is the original one-shot baseline. attempts=2 is the «baseline + same retries» arm (2026-11-16,
    red team): the same number of tries as our arm, and after a failed try it is told what the rerun showed in
    the terms a developer has (TICK counts, verifier text), never the wait graph. So a difference between this arm
    and ours is what the pidin graph, the docs and the probes add, not the retry loop."""
    scen = os.path.join(pool, sid)
    work = hang.prepare(scen)
    base = [f"Program: {sid} (working directory {work})",
            "TICK counts per role log in the observation window: " + json.dumps(ticks),
            "Sources:\n" + hang.sources(work, sid)]
    shutil.rmtree(work, ignore_errors=True)
    tries, notes, g, usage = [], [], {}, []
    ask = ask or globals()["ask"]  # a test passes its own; no model is called there
    for _ in range(attempts):
        g = ask("\n\n".join(base + notes), allow_unknown)
        if g.get("usage"):
            usage.append(g.pop("usage"))
        acts = g.get("actions") or []
        if g.get("kind") not in FIXABLE:
            break  # «none», «unknown» or unreadable: nothing to rerun, and no fix is claimed
        if not acts:
            tries.append({"actions": [], "solved": False, "result": "no fix proposed"})
            break
        t, fb = _try(scen, sid, acts, ticks, alive, structure, progress)
        tries.append({"actions": acts, **t})
        if t["solved"]:
            break
        notes.append(f"Already tried: {json.dumps(acts)} -> {fb}")
    row = {"id": sid, "mode": "naive" if attempts == 1 else f"naive_x{attempts}", "detected": g.get("kind"),
           "vocabulary": list(kinds(allow_unknown)),
           "roles": g.get("roles"), "cause": g.get("cause"), "error": g.get("error"), "solved": None, "attempts": tries,
           "first_ticks": ticks, "first_progress": progress, "usage": usage,
           "actions": tries[-1]["actions"] if tries else (g.get("actions") or [])}
    if tries:  # top-level fields = the last try (as before), first_solved = the first try alone
        row.update({k: v for k, v in tries[-1].items() if k != "actions"})
        row["solved"] = any(t["solved"] for t in tries)
        row["first_solved"] = tries[0]["solved"]
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pool", required=True); ap.add_argument("--code", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--attempts", type=int, default=1, help="1 = one-shot baseline; 2 = same retries as our arm")
    ap.add_argument("--allow-unknown", action="store_true", help="give the baseline the answer «unknown» (sealed v6 on)")
    a = ap.parse_args()
    done = {json.loads(l)["id"] for l in open(a.out)} if os.path.exists(a.out) else set()
    with open(a.out, "a") as out:
        for line in open(a.code):
            r = json.loads(line)
            if r["id"] in done:
                continue
            g = [t for t in r["timeline"] if t["kind"] == "graph"]
            if not g:  # harness failure in the AI-off run: nothing a developer would have seen either
                continue
            row = one(a.pool, r["id"], g[0]["ticks"], g[0].get("alive"), g[0].get("structure"), a.attempts, g[0].get("progress"),
                      a.allow_unknown)
            print(json.dumps({k: row.get(k) for k in ("id", "detected", "solved")}), flush=True)
            out.write(json.dumps(row, ensure_ascii=False) + "\n"); out.flush()


if __name__ == "__main__":
    main()
