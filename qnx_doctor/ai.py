"""The AI part: read the failure, look around (read-only probes), search the local QNX docs,
and propose a fix as data. Code applies the fix and re-runs; only the re-run decides «solved»."""
import json
import os
import re
import sys

from anthropic import Anthropic

from .probes import probe

MODEL = os.environ.get("QD_MODEL", "claude-opus-5-5")
USAGE_FIELDS = ("input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")

SYSTEM = """You are qnx-doctor, a build/boot troubleshooter for QNX SDP 8.0 on a Linux host.
You get a command that failed, its output, and what was already tried. Work step by step.
Reply with exactly ONE JSON object per turn, nothing else:
  {"probe": {"argv": ["ls", "-la", "some/dir"]}}       read-only look at the host (allowed: ls find which cat head tail grep file readelf stat du)
  {"search_docs": "words to search in the QNX docs"}  searches the QNX documentation installed with the SDP
  {"diagnosis": {"cause": "short cause", "evidence": "the log line or doc that proves it", "doc_refs": ["doc path"], "actions": [ ... ]}}
  {"give_up": "why"}
Fix actions (data only, applied by code, then the command is re-run):
  {"type":"source_sdp"} | {"type":"set_env","name":N,"value":V} | {"type":"unset_env","name":N}
  {"type":"add_args","args":[...],"position":"start"|"end"} ("start" = right after the program)
  {"type":"replace_arg","old":A,"new":B} | {"type":"remove_arg","arg":A}
  {"type":"edit_file","path":P,"find":F,"replace":R}   (P relative to the command's working directory)
Prefer the smallest fix that keeps the user's intent. If the user's goal itself is impossible (for example a target the SDP no longer supports), say so with give_up and explain the supported alternative instead of silently changing the goal.
Use probes and docs before guessing paths. Never invent paths you have not seen."""


def _client():
    return Anthropic()


def usage_record(resp) -> dict:
    """One model call as the API counted it (response.usage). A count the API did not send is None, never 0.
    Also printed to stderr at once, so the calls of a case that crashes before its row is written stay in the log."""
    u = getattr(resp, "usage", None)
    rec = {"kind": "usage", "model": getattr(resp, "model", None), "stop_reason": getattr(resp, "stop_reason", None),
           **{f: getattr(u, f, None) for f in USAGE_FIELDS},
           "thinking_tokens": getattr(getattr(u, "output_tokens_details", None), "thinking_tokens", None)}
    print("qd-usage " + json.dumps(rec), file=sys.stderr, flush=True)
    return rec


def _json(text):
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError("no JSON in reply")
    return json.loads(m.group(0))


def think(context: str, cwd: str, env: dict, index, log, max_turns: int = 8, system: str = SYSTEM, confine: bool = False):
    """Run the look-around loop until the model proposes a diagnosis or gives up.
    Returns ("diagnosis", dict) | ("give_up", str). `log` collects visible steps for the timeline."""
    client = _client()
    messages = [{"role": "user", "content": context}]
    for _ in range(max_turns):
        resp = client.messages.create(model=MODEL, max_tokens=4000, system=system, messages=messages,
                                      thinking={"type": "adaptive"})
        log.append(usage_record(resp))  # before the reply is read: an unreadable reply is billed too
        text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
        messages.append({"role": "assistant", "content": resp.content})
        try:
            step = _json(text)
        except Exception as e:
            messages.append({"role": "user", "content": f"Reply with one JSON object only ({e})."})
            continue
        if "probe" in step:
            argv = step["probe"].get("argv", [])
            out = probe(argv, cwd, env, confine)
            log.append({"kind": "probe", "argv": argv, "out": out[-400:]})
            messages.append({"role": "user", "content": f"probe output:\n{out}"})
        elif "search_docs" in step:
            hits = index.search(step["search_docs"], k=4) if index else []
            log.append({"kind": "docs", "query": step["search_docs"], "hits": [h["doc"] for h in hits]})
            messages.append({"role": "user", "content": "docs:\n" + json.dumps(hits, ensure_ascii=False)[:9000]})
        elif "diagnosis" in step:
            return "diagnosis", step["diagnosis"], messages
        elif "give_up" in step:
            return "give_up", step["give_up"], messages
        else:
            messages.append({"role": "user", "content": "Unknown step. Use probe, search_docs, diagnosis or give_up."})
    return "give_up", "turn limit reached", messages


def follow_up(messages, text):
    messages.append({"role": "user", "content": text})
    return messages
