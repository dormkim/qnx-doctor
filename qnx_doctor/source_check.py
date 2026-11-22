"""Text checks of a C source after an AI edit: the first layer only (the barrier is sandbox.py).

Judged on the whole edited file, not on each replacement, so a directive cannot be split over two edits. Only what
the edit added is rejected; what the original program already had is left alone. Known limit: the preprocessor can
build words (token pasting, string concatenation) that no text search sees."""
import os
import re
from collections import Counter

TRIGRAPH = {"=": "#", "/": "\\", "'": "^", "(": "[", ")": "]", "!": "|", "<": "{", ">": "}", "-": "~"}
LEXEME = re.compile(r'//[^\n]*|/\*.*?\*/|"(?:\\.|[^"\\\n])*"|\'(?:\\.|[^\'\\\n])*\'', re.S)
DIRECTIVE = re.compile(r"^[ \t\f\v]*(?:#|%:)[ \t\f\v]*(\w+)?(.*)$", re.M)
WORDS = re.compile(r"incbin|\.include\b|__has_include|__has_embed|\b(?:u8|[LuU])?R\"|\bGCC\s+dependency")


def normalise(text: str) -> str:
    """Translation phases 1 to 3, roughly: trigraphs, spliced lines, comments (strings kept)."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\?\?([=/'()!<>-])", lambda m: TRIGRAPH[m[1]], text)
    text = re.sub(r"\\[ \t\f\v]*\n", "", text)
    return LEXEME.sub(lambda m: " " if m[0].startswith(("//", "/*")) else m[0], text)


def _bad_include(operand: str, src_dir: str, common: str):
    m = re.fullmatch(r'<([\w./+-]+)>|"([\w./+-]+)"', operand.strip())
    if not m:
        return "an include that is not a plain file name"
    name = m[1] or m[2]
    if name.startswith("/"):
        return "an include by absolute path"
    if ".." in name.split("/"):
        if m[1] or not os.path.realpath(os.path.join(src_dir, name)).startswith(os.path.realpath(common) + os.sep):
            return "an include through '..'"
    return None


def findings(text: str, src_dir: str, common: str, escape) -> Counter:
    flat = normalise(text)
    out = Counter()
    for m in DIRECTIVE.finditer(flat):
        word, rest = m[1] or "", m[2]
        if word == "include":
            why = _bad_include(rest, src_dir, common)
            if why:
                out[(why, rest.strip())] += 1
        elif word in ("include_next", "import", "embed", "line") or word.isdigit():
            out[(f"#{word} is not allowed", rest.strip())] += 1
    for m in WORDS.finditer(flat):
        out[("a word that pulls files into the build", m[0])] += 1
    for m in escape.finditer(flat):
        out[("reaches around the message layer", m[0])] += 1
    return out


def added(before: str, after: str, src_dir: str, common: str, escape):
    """The first thing the edit added that is not allowed (without quoting the file), or None."""
    new = findings(after, src_dir, common, escape) - findings(before, src_dir, common, escape)
    return next(iter(new))[0] if new else None


ERROR = re.compile(r"(?:^|/)([\w.-]+/[\w.-]+\.[ch]):(\d{1,6}):(?:\d{1,6}:)?[ \t]*(?:fatal )?error:")


def locations(log: str, limit: int = 8) -> list:
    """Where a build failed, without the compiler's words: those can quote any file the compiler opened."""
    out = []
    for line in log.splitlines():
        m = ERROR.search(line[:500])
        if m and f"{m[1]}:{m[2]}" not in out:
            out.append(f"{m[1]}:{m[2]}")
    return out[:limit]
