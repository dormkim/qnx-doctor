"""Checks of a fix that the rerun cannot see (v7, bench/V7_VERIFY_PLAN.md section 2). Pure text, no target, no AI.

v6 (bench/sealed_v6_1123/RESULT.md, bkr): every arm replaced a synchronous request whose reply the program used by a
pulse and an invented value. The receiver took the pulse and dropped it, so the pair still "exchanged messages" and
the rerun check accepted the fix. Whether a received value is used cannot be seen in the message records, so these
fixes are not rejected here: they get the verdict `review`, naming the call, and a person reads them.

  1. reply_dropped: a file has fewer synchronous sends whose reply is used (assigned, tested, returned, or a
     MsgSend with a reply buffer) after the fix than before.
  2. pulse_skipped: the fix adds pulses, a receiver in the program drops pulses (`if (rcvid == 0) continue;`),
     and the fix changes no receiver's pulse handling.
"""
import re

SYNC = re.compile(r"\b(MsgSend(?:v|vs|sv)?(?:_r)?|qd_send)\s*\(")
PULSE = re.compile(r"\bMsgSendPulse\w*\s*\(")
SKIP = re.compile(r"if\s*\(\s*\w+\s*==\s*0\s*\)\s*(?:continue|\{\s*continue\s*;\s*\})")
COMMENT = re.compile(r"/\*.*?\*/|//[^\n]*", re.S)


def _args(text: str, start: int) -> list[str]:
    """Top-level arguments of the call whose '(' is at start."""
    depth, cur, out = 0, "", []
    for ch in text[start:]:
        if ch == "(":
            depth += 1
            if depth == 1:
                continue
        elif ch == ")":
            depth -= 1
            if depth == 0:
                out.append(cur)
                return [a.strip() for a in out]
        elif ch == "," and depth == 1:
            out.append(cur)
            cur = ""
            continue
        cur += ch
    return [a.strip() for a in out]


def used_sync(src: str) -> list[str]:
    """Synchronous sends whose reply the sender uses, as short call texts."""
    code = COMMENT.sub(" ", src)
    out = []
    for m in SYNC.finditer(code):
        stmt = code[max(code.rfind(";", 0, m.start()), code.rfind("{", 0, m.start()), code.rfind("}", 0, m.start())) + 1:m.start()]
        s = stmt.strip()
        end, depth = m.end() - 1, 0
        for end in range(m.end() - 1, len(code)):
            depth += {"(": 1, ")": -1}.get(code[end], 0)
            if depth == 0:
                break
        rest = code[end + 1:end + 40]
        # The reply is used when the call's value is stored, returned, passed on, or compared with something other
        # than an error value. «if (send(...) < 0) error» only checks that the call worked.
        stored = bool(re.search(r"(?:(?<![=!<>])=|\breturn|,|[+\-*/%^]|(?<![&|])[&|]|\b(?!if\b|while\b)\w+\s*\()\s*$", s))
        compared = bool(re.match(r"\s*(?:[<>]=?|[!=]=)", rest)) and not re.match(
            r"\s*(?:<\s*0|==\s*-1|!=\s*-1|>=\s*0|==\s*EOK|!=\s*EOK)\b", rest)
        used = stored or compared
        if m.group(1).startswith("MsgSend"):
            a = _args(code, m.end() - 1)
            if len(a) >= 4 and a[3] not in ("NULL", "0", "(void *)0"):
                used = True
        if used:
            out.append(re.sub(r"\s+", " ", code[m.start():m.end() + 40]).split(";")[0])
    return out


def review(files_before: dict[str, str], files_after: dict[str, str]) -> list[str]:
    """Reasons a passing rerun cannot vouch for this fix. [] = nothing found."""
    why = []
    for path, before in sorted(files_before.items()):
        after = files_after.get(path, before)
        b, a = used_sync(before), used_sync(after)
        if len(a) < len(b):
            gone = [c for c in b if c not in a] or b[len(a):]
            why.append(f"{path}: a synchronous request whose reply is used is gone ({'; '.join(gone[:2])}); "
                       "the rerun cannot tell whether the value the program now uses is real")
    added = sum(len(PULSE.findall(COMMENT.sub(' ', files_after.get(p, s)))) - len(PULSE.findall(COMMENT.sub(' ', s)))
                for p, s in files_before.items())
    if added > 0:
        skips = lambda s: bool(SKIP.search(COMMENT.sub(" ", s)))
        skippers = [p for p, s in sorted(files_after.items()) if skips(s)]
        # A fix that sends new pulses and teaches a receiver to handle them (its pulse-dropping line changed) is
        # not flagged: that is how a request legitimately becomes a pulse (v6 epe).
        taught = [p for p, s in files_before.items() if skips(s) and not skips(files_after.get(p, s))]
        if skippers and not taught:
            why.append(f"the fix adds pulses and {', '.join(skippers)} drops pulses it receives; "
                       "a request sent as a pulse there may be read and ignored")
    return why
