"""Local search over the QNX documentation that ships inside the user's own SDP install.
Nothing from the SDP is copied into this repository; the index is built on the user's machine."""
import html
import json
import math
import os
import re
from collections import Counter

DOC_ROOT_REL = "target/qnx/usr/help/eclipse/plugins"
CACHE = os.path.expanduser("~/.cache/qnx-doctor/docs-index.json")
TOKEN = re.compile(r"[A-Za-z_][A-Za-z0-9_\-]{1,40}")


def _text(path):
    raw = open(path, errors="replace").read()
    title = re.search(r"<title>(.*?)</title>", raw, re.S)
    body = re.sub(r"<script.*?</script>|<style.*?</style>", " ", raw, flags=re.S)
    body = html.unescape(re.sub(r"<[^>]+>", " ", body))
    return (html.unescape(title.group(1)).strip() if title else os.path.basename(path)), re.sub(r"\s+", " ", body)


def build(sdp):
    root = os.path.join(sdp, DOC_ROOT_REL)
    docs = []
    for d, _, files in os.walk(root):
        for f in files:
            if f.endswith(".html"):
                p = os.path.join(d, f)
                title, body = _text(p)
                docs.append({"path": os.path.relpath(p, root), "title": title, "body": body[:20000]})
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    json.dump(docs, open(CACHE, "w"))
    return docs


def load(sdp):
    if os.path.exists(CACHE):
        return json.load(open(CACHE))
    return build(sdp)


class Index:
    def __init__(self, sdp):
        self.docs = load(sdp)
        self.tf = [Counter(t.lower() for t in TOKEN.findall(d["title"] + " " + d["title"] + " " + d["body"])) for d in self.docs]
        self.len = [sum(c.values()) for c in self.tf]
        self.avg = sum(self.len) / max(1, len(self.len))
        df = Counter()
        for c in self.tf:
            df.update(c.keys())
        n = len(self.docs)
        self.idf = {t: math.log(1 + (n - v + 0.5) / (v + 0.5)) for t, v in df.items()}

    def search(self, query, k=5):
        q = [t.lower() for t in TOKEN.findall(query)]
        scores = []
        for i, c in enumerate(self.tf):
            s = 0.0
            for t in q:
                f = c.get(t)
                if f:
                    s += self.idf.get(t, 0) * f * 2.2 / (f + 1.2 * (0.25 + 0.75 * self.len[i] / self.avg))
            if s:
                scores.append((s, i))
        scores.sort(reverse=True)
        out = []
        for s, i in scores[:k]:
            d = self.docs[i]
            body = d["body"]
            pos = min([body.lower().find(t) for t in q if body.lower().find(t) >= 0] or [0])
            out.append({"doc": d["path"], "title": d["title"], "excerpt": body[max(0, pos - 300): pos + 900]})
        return out
