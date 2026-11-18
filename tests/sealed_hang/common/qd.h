/* Small helpers shared by the sealed hang scenarios (QNX 8.0, message passing).
 * Every scenario process names itself, opens peers by name, and prints "TICK <role> <n>" when its loop
 * completes one round. A healthy system keeps printing TICKs; a hung one stops. */
#ifndef QD_H
#define QD_H
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/iomsg.h>
#include <sys/neutrino.h>
#include <sys/dispatch.h>
#include <pthread.h>
/* QNX 8.0 has no setprio(); set the calling thread's priority (policy kept). Compile fix, 2026-11-15, before any run. */
#define setprio(pid, prio) pthread_setschedprio(pthread_self(), (prio))

#define QD_MSG 0x7000            /* application message type, outside the _IO_* range */
typedef union { struct _pulse pulse; uint16_t type; struct { uint16_t type; int32_t v; } app; char raw[64]; } qd_msg_t;

static name_attach_t *qd_attach(const char *me) {
  name_attach_t *a = name_attach(NULL, me, 0);
  if (!a) { perror("name_attach"); exit(1); }
  return a;
}
static int qd_open(const char *peer) {
  for (int i = 0; i < 100; i++) { int c = name_open(peer, 0); if (c != -1) return c; usleep(50000); }
  perror("name_open"); exit(1);
}
/* Receive one thing. Returns rcvid (>0 message, 0 pulse). Connect/close messages from name_open are answered here. */
static int qd_receive(int chid, qd_msg_t *m) {
  for (;;) {
    int rcvid = MsgReceive(chid, m, sizeof *m, NULL);
    if (rcvid == -1) continue;
    if (rcvid == 0) { if (m->pulse.code == _PULSE_CODE_DISCONNECT) { ConnectDetach(m->pulse.scoid); continue; } return 0; }
    if (m->type == _IO_CONNECT) { MsgReply(rcvid, EOK, NULL, 0); continue; }
    if (m->type > _IO_BASE && m->type <= _IO_MAX) { MsgError(rcvid, ENOSYS); continue; }
    return rcvid;
  }
}
static int qd_send(int coid, int v) {      /* synchronous: blocks until the peer replies */
  qd_msg_t m; m.app.type = QD_MSG; m.app.v = v; int r = 0;
  return MsgSend(coid, &m.app, sizeof m.app, &r, sizeof r) == -1 ? -1 : r;
}
/* A genuinely fixed-priority named endpoint. name_attach() ignores its flags arg (QNX lib ref: "Currently
 * not used"), so a channel it makes is NOT _NTO_CHF_FIXED_PRIORITY and its receiver inherits the caller's
 * priority — a "low" server then runs at the client's priority and is never starved. ChannelCreate() does honor
 * the flag. We publish pid+chid at /tmp/<me>.id (direct write; shmem has no working rename, see below) so a peer connects by ConnectAttach instead of
 * name_open. Harness helper added 2026-11-18 (sealed v4 reproducibility fix); labels unchanged. */
static int qd_fixed_chan(const char *me) {
  int chid = ChannelCreate(_NTO_CHF_FIXED_PRIORITY | _NTO_CHF_DISCONNECT | _NTO_CHF_UNBLOCK | _NTO_CHF_COID_DISCONNECT);
  if (chid == -1) { perror("ChannelCreate"); exit(1); }
  /* Write the id file directly, NOT via a temp + rename(): /tmp is a /dev/shmem link (check.sh) and shmem does
   * not honor rename() across names, so the final /tmp/<me>.id never appeared and a peer could never connect —
   * the hang was a failed connect, not the priority inversion (found 2026-11-18, explains v4 priority_chain 0/5).
   * A reader (qd_open_fixed) that catches a half-written file just gets fscanf != 2 and retries, so one write is safe. */
  char p[64]; snprintf(p, sizeof p, "/tmp/%s.id", me);
  FILE *f = fopen(p, "w"); if (!f) { perror("fopen id"); exit(1); }
  fprintf(f, "%d %d\n", getpid(), chid); fflush(f); fclose(f);
  return chid;
}
static int qd_open_fixed(const char *peer) {   /* connect to a qd_fixed_chan() endpoint by name */
  char p[64]; snprintf(p, sizeof p, "/tmp/%s.id", peer);
  for (int i = 0; i < 200; i++) {
    FILE *f = fopen(p, "r");
    if (f) { int pid = -1, chid = -1, ok = (fscanf(f, "%d %d", &pid, &chid) == 2); fclose(f);
      if (ok) { int c = ConnectAttach(0, pid, chid, _NTO_SIDE_CHANNEL, 0); if (c != -1) return c; } }
    usleep(50000);
  }
  perror("qd_open_fixed"); exit(1);
}
static void qd_tick(const char *role, int n) { printf("TICK %s %d\n", role, n); fflush(stdout); }
#endif
