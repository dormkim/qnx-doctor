"""QNX-specific trap scenarios for the DEV pool only (2026-11-17, deep-research item 3). Never held-out or sealed:
gen2.py adds these only when it renders `--pool dev`, so the sealed v2 hashes do not move.

  notify_back     a server notifies its client with a synchronous MsgSend while that client is still REPLY-blocked
                  on the server: the «sends go one way» rule of the MsgDeliverEvent() docs. QNX idiom: reply, then
                  notify with a pulse (MsgSendPulse, or a registered event and MsgDeliverEvent)
  fixed_flags     _NTO_CHF_FIXED_PRIORITY hidden in a flag constant in a header next to _NTO_CHF_DISCONNECT, with a
                  CPU load between the server's and the client's priority (priority inversion)
  missing_reply   a server path that takes the client's first message (a «hello») and never replies; the server keeps
                  serving another client, so it looks alive
_NTO_SIDE_CHANNEL (a connection id in the file-descriptor range) is not here yet: its failures seen so far are errors
(EBADF/ENOSYS) or a wait on procnto, not a wait between two programs that the graph can show.
Sources carry no comments; the answer key goes to labels.json like gen2.
"""
import hashlib
import os
import random

import gen2

TRAPS = {"notify_back": [7101, 7102], "fixed_flags": [7201, 7202], "missing_reply": [7301, 7302]}


def _main(funcs, indirect=False):
    disp = "\n".join(f"  if (!strcmp(argv[1], \"{fn}\")) {fn}(argv[2], argc > 3 ? argv[3] : \"\", argc > 4 ? atoi(argv[4]) : 0, "
                     f"argc > 5 ? atoi(argv[5]) : 0);" for fn in funcs)
    return f"\nint main(int argc, char **argv) {{\n  if (argc < 3) return 2;\n{disp}\n  return 2;\n}}\n"


def notify_back(p, r):
    hub, sub, rv, m, c, us = p.ident(), p.ident(), p.ident(), p.ident(), p.ident(), r.choice([10000, 20000, 50000])
    src = (f"static void {hub}(const char *me, const char *nx, int a, int b) {{\n  (void)a; (void)b;\n"
           f"  name_attach_t *at = qd_attach(me);\n  int {c} = -1;\n  qd_msg_t {m};\n" + p.loop(
               f"    int {rv} = qd_receive(at->chid, &{m});\n    if ({rv} <= 0) continue;\n    if ({c} == -1) {c} = qd_open(nx);\n"
               f"    qd_send({c}, {m}.app.v);\n    MsgReply({rv}, EOK, &{m}.app.v, sizeof {m}.app.v);\n") + "}\n\n"
           f"static void {sub}(const char *me, const char *nx, int a, int b) {{\n  (void)a; (void)b;\n"
           f"  name_attach_t *at = qd_attach(me);\n  int {c} = qd_open(nx);\n  qd_msg_t {m};\n" + p.loop(
               f"    qd_send({c}, n);\n    int {rv} = qd_receive(at->chid, &{m});\n    if ({rv} > 0) MsgReply({rv}, EOK, &n, sizeof n);\n"
               f"    qd_tick(me, n);\n    usleep({us});\n") + "}\n")
    return src, {"hub": hub, "sub": sub}


def missing_reply(p, r):
    srv, cli, rv, m, c, us = p.ident(), p.ident(), p.ident(), p.ident(), p.ident(), r.choice([10000, 20000, 50000])
    src = (f"static void {srv}(const char *me, const char *nx, int a, int b) {{\n  (void)nx; (void)a; (void)b;\n"
           f"  name_attach_t *at = qd_attach(me);\n  int {c} = 0;\n  qd_msg_t {m};\n" + p.loop(
               f"    int {rv} = qd_receive(at->chid, &{m});\n    if ({rv} <= 0) continue;\n"
               f"    if ({m}.app.v < 0) {{ {c}++; fprintf(stderr, \"hello %d\\n\", {c}); continue; }}\n"
               f"    MsgReply({rv}, EOK, &{m}.app.v, sizeof {m}.app.v);\n") + "}\n\n"
           f"static void {cli}(const char *me, const char *nx, int a, int b) {{\n  (void)a; (void)b;\n"
           f"  int {c} = qd_open(nx);\n  qd_send({c}, -1);\n" + p.loop(f"    qd_send({c}, n);\n    qd_tick(me, n);\n    usleep({us});\n") + "}\n")
    return src, {"store": srv, "hello_client": cli}


def render(trap, seed, out_root):
    r = random.Random(seed)
    p = gen2.Prog(r)
    names = set()

    def role():
        while True:
            n = gen2.word(r, r.choice([2, 3]))
            if n not in names:
                names.add(n); return n

    sid = "t" + hashlib.sha256(f"qd-trap-{trap}-{seed}".encode()).hexdigest()[:6]
    d = os.path.join(out_root, sid); os.makedirs(d, exist_ok=True)
    exe, hdr, lines, extra_src, header = p.ident(), p.ident() + ".h", ["#!/bin/sh"], "", ""
    label = {"seed": seed, "gen_version": gen2.GEN_VERSION, "trap": trap, "axes": ["qnx_trap"], "files": 1}

    def start(fn, *args, log=None):
        lines.append(f"/var/qd/{sid}/{exe} {fn} {' '.join(str(x) for x in args)} > {log or '/dev/null'} 2>&1 &")

    funcs = []
    if trap == "notify_back":
        extra_src, fn = notify_back(p, r)
        h, s = role(), role()
        funcs += [fn["hub"], fn["sub"]]
        start(fn["hub"], h, s, log=f"/tmp/q_{h}.err"); start(fn["sub"], s, h, log=f"/tmp/d0{s}.log")
        label.update(kind="deadlock", cause="send_on_reply_path", members=[s, h], loop_logs=[s],
                     culprit=f"{h} sends synchronously to {s} before replying, while {s} is REPLY-blocked on {h}",
                     fix=f"{h} replies first and notifies {s} with a pulse (MsgSendPulse, or MsgDeliverEvent with an event {s} registered)")
    elif trap == "fixed_flags":
        cfg = {"rt_prio": False, "lo": r.randint(3, 8), "hi": r.randint(25, 40), "work": r.choice([1000000, 2000000, 4000000])}
        cfg["mid"] = r.randint(max(cfg["lo"] + 1, 15), 22)
        flag = hdr[:-2].upper() + "_CHFLAGS"
        header = f"#pragma once\n#define {flag} (_NTO_CHF_DISCONNECT | _NTO_CHF_FIXED_PRIORITY)\n"
        bodies = {k: gen2.body_of(p, k, cfg) for k in ("pserver", "pclient", "hog")}
        bodies["pserver"] = bodies["pserver"].replace("ChannelCreate(_NTO_CHF_FIXED_PRIORITY)", f"ChannelCreate({flag})")
        # The id file appears whole (write a temp file, then rename). gen2's server writes it in place, and a client
        # at a higher priority could open it empty and exit (seen once on this trap, 2026-11-17, rerun 3 of 3).
        old_w = 'FILE *f = fopen(path, "w"); fprintf(f, "%d %d\\n", getpid(), ch); fclose(f);'
        assert old_w in bodies["pserver"], "gen2 pserver id-file line changed"
        bodies["pserver"] = bodies["pserver"].replace(old_w, 'char tmp[72]; snprintf(tmp, sizeof tmp, "%s.w", path);\n'
                                                      '  FILE *f = fopen(tmp, "w"); fprintf(f, "%d %d\\n", getpid(), ch); fclose(f); rename(tmp, path);')
        fns = {k: p.ident() for k in bodies}
        extra_src = "\n".join(bodies[k].replace("FN", fns[k], 1) for k in ("hog", "pserver", "pclient"))
        funcs += list(fns.values())
        srv, cli, hog = role(), role(), role()
        start(fns["pserver"], srv, "-", log=f"/tmp/q_{srv}.err"); start(fns["pclient"], cli, srv, log=f"/tmp/d0{cli}.log")
        lines.append("sleep 1"); lines.append(f": > /tmp/d0{cli}.log")
        start(fns["hog"], hog, "-", cfg["mid"], 20)
        label.update(kind="priority_chain", cause="fixed_priority_channel", members=[cli, srv], loop_logs=[cli], prio_client=cli,
                     culprit=f"{flag} in {hdr} includes _NTO_CHF_FIXED_PRIORITY, so {srv} does not inherit {cli}'s priority while a CPU load sits between them",
                     fix=f"drop _NTO_CHF_FIXED_PRIORITY from {flag} (keep _NTO_CHF_DISCONNECT)")
    else:
        extra_src, fn = missing_reply(p, r)
        wbody = gen2.body_of(p, "waiter", {})
        wfn = p.ident()
        extra_src += "\n" + wbody.replace("FN", wfn, 1)
        funcs += [fn["store"], fn["hello_client"], wfn]
        s, c, w = role(), role(), role()
        start(fn["store"], s, "-", log=f"/tmp/q_{s}.err"); lines.append("sleep 1")
        start(wfn, w, s, log=f"/tmp/d0{w}.log"); start(fn["hello_client"], c, s, log=f"/tmp/d0{c}.log")
        label.update(kind="missing_reply", cause="missing_reply", members=[c, s], loop_logs=[c, w],
                     culprit=f"{s} takes {c}'s first message (a negative value) and goes back to MsgReceive without MsgReply",
                     fix=f"{s} replies (MsgReply or MsgError) on that path too")
    lines.append("sleep 4")
    if header:
        open(os.path.join(d, hdr), "w").write(header)
    inc = '#include "../common/qd.h"\n#include <pthread.h>\n#include <time.h>\n' + (f'#include "{hdr}"\n' if header else "")
    open(os.path.join(d, f"{exe}.c"), "w").write(inc + "\n" + extra_src + _main(funcs))
    open(os.path.join(d, "run.sh"), "w").write("\n".join(lines) + "\n")
    label["procs"] = sum(l.startswith("/var/qd") for l in lines) - (trap == "fixed_flags")  # the CPU load is not counted
    return sid, label


def render_all(out_root):
    return dict(render(t, s, out_root) for t, seeds in TRAPS.items() for s in seeds)
