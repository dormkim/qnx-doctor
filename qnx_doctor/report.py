"""Human-readable timeline of one diagnosis, for the terminal and for the demo video.

Stages shown in order: symptom → rule table → AI look-around / docs search → fix (as data) → re-run verdict.
  python3 -m qnx_doctor.report runs/x.jsonl --id X04            # terminal
  python3 -m qnx_doctor.report runs/x.jsonl --id X04 --html out.html
"""
import argparse
import html
import json

ICON = {"symptom": "❌ symptom", "rule": "📏 rule table", "probe": "🔍 AI looks", "docs": "📚 QNX docs",
        "ai_fix": "🛠 fix (data)", "give_up": "🤷 gave up"}


def steps(r):
    out = []
    for t in r.get("timeline", []):
        k = t.get("kind")
        if k == "symptom":
            out.append((ICON[k], f"{t.get('reason')}", "\n".join((t.get("out") or "").splitlines()[-4:])))
        elif k == "rule":
            out.append((ICON[k], f"cause = {t.get('cause')}", f"{t.get('why')}\nactions: {json.dumps(t.get('actions'), ensure_ascii=False)}\nre-run: {t.get('result')}"))
        elif k in ("probe", "look", "tool"):
            out.append((ICON["probe"], t.get("cmd") or t.get("argv") or "", (t.get("out") or "")[:400]))
        elif k in ("docs", "search"):
            out.append((ICON["docs"], f"query: {t.get('query')}", "\n".join(t.get("hits", [])[:3]) if isinstance(t.get("hits"), list) else str(t.get("hits"))[:300]))
        elif k == "ai_fix":
            refs = ", ".join(t.get("doc_refs") or [])
            out.append((ICON[k], f"cause = {t.get('cause')}", f"evidence: {t.get('evidence')}\ndocs: {refs}\nactions: {json.dumps(t.get('actions'), ensure_ascii=False)}\nre-run: {t.get('result')}"))
        elif k == "give_up":
            out.append((ICON[k], "", str(t.get("why"))))
    verdict = "✅ SOLVED — proven by re-run" if r.get("solved") else ("— command did not fail" if r.get("solved") is None else "⛔ not solved (nothing claimed)")
    out.append(("⚖️ verdict", verdict, f"by: {r.get('by')} · {r.get('seconds')} s"))
    return out


def to_text(r):
    lines = [f"qnx-doctor · {r.get('id')}", ""]
    for i, (stage, head, body) in enumerate(steps(r), 1):
        lines.append(f"{i}. {stage}  {head}")
        for b in (body or "").splitlines():
            lines.append(f"     {b}")
    return "\n".join(lines)


def to_html(r):
    rows = "".join(f"<li><div class=s>{html.escape(st)}</div><div class=h>{html.escape(str(h))}</div><pre>{html.escape(b or '')}</pre></li>"
                   for st, h, b in steps(r))
    return f"""<!doctype html><meta charset=utf-8><title>qnx-doctor {html.escape(str(r.get('id')))}</title>
<style>body{{font:16px/1.5 -apple-system,system-ui,sans-serif;background:#0f1420;color:#e8ecf3;max-width:900px;margin:32px auto;padding:0 20px}}
ol{{list-style:none;padding:0}}li{{border-left:3px solid #3b82f6;margin:0 0 18px;padding:6px 16px}}.s{{font-weight:700;font-size:18px}}
.h{{color:#93c5fd}}pre{{white-space:pre-wrap;background:#161d2e;padding:10px;border-radius:6px;font-size:13px}}</style>
<h1>qnx-doctor · {html.escape(str(r.get('id')))}</h1><ol>{rows}</ol>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("jsonl"); ap.add_argument("--id", required=True); ap.add_argument("--html")
    a = ap.parse_args()
    r = next(json.loads(l) for l in open(a.jsonl) if l.strip() and json.loads(l).get("id") == a.id)
    if a.html:
        open(a.html, "w").write(to_html(r)); print(a.html)
    else:
        print(to_text(r))


if __name__ == "__main__":
    main()
