"""The AI part: read the failure, look around (read-only probes), search the local QNX docs,
and propose a fix as data. Code applies the fix and re-runs; only the re-run decides «solved»."""
import json
import os
import re
import subprocess

from anthropic import Anthropic

MODEL = os.environ.get("QD_MODEL", "claude-opus-5-5")
PROBES = {"ls", "find", "which", "cat", "head", "tail", "grep", "file", "readelf", "stat", "du"}

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


def _probe(argv, cwd, env):
    if not argv or os.path.basename(argv[0]) not in PROBES:
        return f"probe refused: {argv[:1]} is not a read-only command"
    try:
        p = subprocess.run(argv, cwd=cwd, env=env, capture_output=True, timeout=30)
        return (p.stdout + p.stderr).decode(errors="replace")[-3000:] or "(no output)"
    except Exception as e:
        return f"probe failed: {e}"


def _json(text):
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError("no JSON in reply")
    return json.loads(m.group(0))


def think(context: str, cwd: str, env: dict, index, log, max_turns: int = 8):
    """Run the look-around loop until the model proposes a diagnosis or gives up.
    Returns ("diagnosis", dict) | ("give_up", str). `log` collects visible steps for the timeline."""
    client = _client()
    messages = [{"role": "user", "content": context}]
    for _ in range(max_turns):
        resp = client.messages.create(model=MODEL, max_tokens=4000, system=SYSTEM, messages=messages,
                                      thinking={"type": "adaptive"})
        text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
        messages.append({"role": "assistant", "content": resp.content})
        try:
            step = _json(text)
        except Exception as e:
            messages.append({"role": "user", "content": f"Reply with one JSON object only ({e})."})
            continue
        if "probe" in step:
            argv = step["probe"].get("argv", [])
            out = _probe(argv, cwd, env)
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
