"""The only place the AI's requests touch the host: read-only look-around commands from a fixed allow-list.

Kept out of ai.py on purpose: ai.py (the model loop) must not import subprocess or the fix actions, so the
model can only ask; code decides what runs (tests/unit/test_boundary.py checks this with the AST)."""
import os
import subprocess

PROBES = {"ls", "find", "which", "cat", "head", "tail", "grep", "file", "readelf", "stat", "du"}


def probe(argv, cwd, env, confine=False):
    if not argv or os.path.basename(argv[0]) not in PROBES:
        return f"probe refused: {argv[:1]} is not a read-only command"
    if confine and any(a.startswith("/") or ".." in a.split("/") for a in argv[1:]):
        return "probe refused: only paths inside the working directory"  # hang mode: the answer key lives outside
    try:
        p = subprocess.run(argv, cwd=cwd, env=env, capture_output=True, timeout=30)
        return (p.stdout + p.stderr).decode(errors="replace")[-3000:] or "(no output)"
    except Exception as e:
        return f"probe failed: {e}"
