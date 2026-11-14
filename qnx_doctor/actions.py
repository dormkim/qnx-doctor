"""Fix actions are data, applied by code — the AI never runs a shell command that changes the system.

Allowed actions (everything stays inside the work directory or the command's own environment):
  {"type": "source_sdp"}
  {"type": "set_env", "name": N, "value": V}
  {"type": "unset_env", "name": N}
  {"type": "add_args", "args": [...], "position": "start"|"end"}   # "start" = right after the program
  {"type": "replace_arg", "old": A, "new": B}
  {"type": "remove_arg", "arg": A}
  {"type": "edit_file", "path": P, "find": F, "replace": R}        # P relative to the command's cwd
"""
import os

ALLOWED = {"source_sdp", "set_env", "unset_env", "add_args", "replace_arg", "remove_arg", "edit_file"}


class Rejected(Exception):
    pass


def _program_index(argv):
    # qd-boot / wrappers: the real program is the next token
    return 1 if argv and os.path.basename(argv[0]) in ("qd-boot",) else 0


def apply(spec: dict, actions: list, workdir: str) -> dict:
    s = dict(spec)
    s["argv"] = list(spec["argv"])
    s["env"] = dict(spec.get("env", {}))
    s["env_unset"] = list(spec.get("env_unset", []))
    for a in actions:
        t = a.get("type")
        if t not in ALLOWED:
            raise Rejected(f"action not allowed: {t}")
        if t == "source_sdp":
            s["source_sdp"] = True
        elif t == "set_env":
            s["env"][a["name"]] = str(a["value"])
            if a["name"] in s["env_unset"]:
                s["env_unset"].remove(a["name"])
        elif t == "unset_env":
            s["env"].pop(a["name"], None)
            s["env_unset"].append(a["name"])
        elif t == "add_args":
            args = [str(x) for x in a["args"]]
            if a.get("position", "end") == "start":
                i = _program_index(s["argv"]) + 1
                s["argv"][i:i] = args
            else:
                s["argv"] += args
        elif t == "replace_arg":
            if a["old"] not in s["argv"]:
                raise Rejected(f"replace_arg: {a['old']!r} is not in the command")
            s["argv"] = [a["new"] if x == a["old"] else x for x in s["argv"]]
        elif t == "remove_arg":
            if a["arg"] not in s["argv"]:
                raise Rejected(f"remove_arg: {a['arg']!r} is not in the command")
            s["argv"].remove(a["arg"])
        elif t == "edit_file":
            base = os.path.realpath(os.path.join(workdir, spec.get("cwd", ".")))
            path = os.path.realpath(os.path.join(base, a["path"]))
            if not path.startswith(os.path.realpath(workdir) + os.sep):
                raise Rejected("edit_file outside the work directory")
            text = open(path).read()
            if a["find"] not in text:
                raise Rejected(f"edit_file: text to replace not found in {a['path']}")
            open(path, "w").write(text.replace(a["find"], a["replace"], 1))
    return s
