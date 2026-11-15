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
static void qd_tick(const char *role, int n) { printf("TICK %s %d\n", role, n); fflush(stdout); }
#endif
