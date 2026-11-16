/* qd_trace: message-structure recorder, linked into every scenario program by the harness (hang.py build) with
 * `-Wl,--wrap=<call>` for each send/receive call. The scenario source is never changed and cannot opt out: the
 * linker routes every MsgSend, MsgSendPulse and MsgReceive variant referenced in the program's own objects through here.
 *
 * Why (verifier, 2026-11-16): on the first held-out run a «fix» could rewire run.sh or make one peer stop sending,
 * and the rerun still looked alive. qnx-doctor now accepts a fix only if every process pair that tried to exchange
 * messages before the fix really exchanges them after it — the sender's call returned (MsgSend: the peer replied;
 * pulse: delivered) AND the receiver got it. This file only counts; hang.py decides.
 *
 * Record per (direction, kind, peer pid): attempts and completions. Kept in RAM and rewritten to
 * /dev/shmem/qdm.<pid> (RAM, served by procnto: no disk driver involved) on small counts and powers of two.
 * Line format: "<S|R> <M|P> <peer pid> <attempts> <done>". snap prints these files with the pidin snapshot.
 * Counts are states for the verifier, not timing (QNX licence 4.2(i)). */
#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <sys/iomsg.h>
#include <sys/neutrino.h>
#include <pthread.h>

#define QDT_MAX 32
struct qdt_rec { char dir, kind; int peer; unsigned att, done; };
static struct qdt_rec qdt[QDT_MAX];
static int qdt_n;
static pthread_mutex_t qdt_mx = PTHREAD_MUTEX_INITIALIZER;

static int qdt_mark(unsigned v) { return v <= 4 || (v & (v - 1)) == 0; }

static void qdt_flush(void) {   /* caller holds qdt_mx */
  char path[48], buf[QDT_MAX * 40];
  int n = 0;
  for (int i = 0; i < qdt_n; i++)
    n += snprintf(buf + n, sizeof buf - n, "%c %c %d %u %u\n", qdt[i].dir, qdt[i].kind, qdt[i].peer, qdt[i].att, qdt[i].done);
  snprintf(path, sizeof path, "/dev/shmem/qdm.%d", getpid());
  int fd = open(path, O_WRONLY | O_CREAT | O_TRUNC, 0644);
  if (fd >= 0) { (void)!write(fd, buf, n); close(fd); }
}

static void qdt_add(char dir, char kind, int peer, int att, int done) {
  if (peer <= 1) return;        /* unknown peer or procnto: not an application pair */
  int s = errno;
  pthread_mutex_lock(&qdt_mx);
  int i = 0;
  while (i < qdt_n && !(qdt[i].dir == dir && qdt[i].kind == kind && qdt[i].peer == peer)) i++;
  if (i == qdt_n && qdt_n < QDT_MAX) { qdt[i] = (struct qdt_rec){dir, kind, peer, 0, 0}; qdt_n++; }
  if (i < qdt_n) {
    qdt[i].att += att; qdt[i].done += done;
    if ((att && qdt_mark(qdt[i].att)) || (done && qdt_mark(qdt[i].done))) qdt_flush();
  }
  pthread_mutex_unlock(&qdt_mx);
  errno = s;
}

static int qdt_server(int coid) {   /* pid that owns the channel behind our connection */
  struct _server_info si;
  int s = errno, r = ConnectServerInfo(0, coid, &si);
  errno = s;
  return r == coid ? si.pid : -1;
}

static void qdt_got(long rcvid, const void *msg, size_t bytes) {   /* receiver side */
  if (rcvid > 0) {
    if (msg && bytes >= 2) {
      uint16_t t = *(const uint16_t *)msg;
      if (t >= _IO_BASE && t <= _IO_MAX) return;   /* name_open connect/close traffic, not the program's own */
    }
    struct _msg_info mi;
    int s = errno;
    if (MsgInfo(rcvid, &mi) != -1) qdt_add('R', 'M', mi.pid, 1, 1);
    errno = s;
  } else if (rcvid == 0 && msg && bytes >= sizeof(struct _pulse)) {
    const struct _pulse *p = msg;
    if (p->code < 0) return;                        /* kernel pulses (disconnect, ...) */
    struct _client_info ci;
    int s = errno;
    if (ConnectClientInfo(p->scoid, &ci, 0) != -1) qdt_add('R', 'P', ci.pid, 1, 1);
    errno = s;
  }
}

#define QDT_SEND(name, A, B, C, D)                                                       \
  extern long __real_##name(int, A, size_t, B, size_t);                                \
  long __wrap_##name(int coid, A s, size_t sn, B r, size_t rn) {                        \
    int peer = qdt_server(coid);                                                         \
    qdt_add('S', 'M', peer, 1, 0);                                                       \
    long v = __real_##name(coid, s, sn, r, rn);                                          \
    if (v != -1 && !(v < 0 && (C))) qdt_add('S', 'M', peer, 0, 1);                       \
    (void)(D);                                                                           \
    return v;                                                                            \
  }
/* _r variants return -errno instead of -1; (C) says whether the name is an _r variant */
QDT_SEND(MsgSend, const void *, void *, 0, 0)
QDT_SEND(MsgSend_r, const void *, void *, 1, 0)
QDT_SEND(MsgSendnc, const void *, void *, 0, 0)
QDT_SEND(MsgSendnc_r, const void *, void *, 1, 0)
QDT_SEND(MsgSendsv, const void *, const struct iovec *, 0, 0)
QDT_SEND(MsgSendsv_r, const void *, const struct iovec *, 1, 0)
QDT_SEND(MsgSendsvnc, const void *, const struct iovec *, 0, 0)
QDT_SEND(MsgSendsvnc_r, const void *, const struct iovec *, 1, 0)
QDT_SEND(MsgSendvs, const struct iovec *, void *, 0, 0)
QDT_SEND(MsgSendvs_r, const struct iovec *, void *, 1, 0)
QDT_SEND(MsgSendvsnc, const struct iovec *, void *, 0, 0)
QDT_SEND(MsgSendvsnc_r, const struct iovec *, void *, 1, 0)
QDT_SEND(MsgSendv, const struct iovec *, const struct iovec *, 0, 0)
QDT_SEND(MsgSendv_r, const struct iovec *, const struct iovec *, 1, 0)
QDT_SEND(MsgSendvnc, const struct iovec *, const struct iovec *, 0, 0)
QDT_SEND(MsgSendvnc_r, const struct iovec *, const struct iovec *, 1, 0)

#define QDT_PULSE(name, V, C)                                                            \
  extern int __real_##name(int, int, int, V);                                          \
  int __wrap_##name(int coid, int prio, int code, V val) {                              \
    int peer = qdt_server(coid);                                                         \
    qdt_add('S', 'P', peer, 1, 0);                                                       \
    int v = __real_##name(coid, prio, code, val);                                        \
    if (v != -1 && !(v < 0 && (C))) qdt_add('S', 'P', peer, 0, 1);                       \
    return v;                                                                            \
  }
QDT_PULSE(MsgSendPulse, long, 0)
QDT_PULSE(MsgSendPulse_r, long, 1)
QDT_PULSE(MsgSendPulsePtr, void *, 0)
QDT_PULSE(MsgSendPulsePtr_r, void *, 1)

#define QDT_RECV(name, B, RET, C)                                                        \
  extern RET __real_##name(int, B, size_t, struct _msg_info *);                        \
  RET __wrap_##name(int chid, B m, size_t n, struct _msg_info *info) {                  \
    RET v = __real_##name(chid, m, n, info);                                             \
    if (v >= 0) qdt_got(v, (C) ? NULL : (const void *)m, (C) ? 0 : n);                   \
    return v;                                                                            \
  }
/* For the iovec variants the buffer is not one block: only messages (via MsgInfo) are counted, pulses are not. */
QDT_RECV(MsgReceive, void *, rcvid_t, 0)
QDT_RECV(MsgReceive_r, void *, rcvid_t, 0)
QDT_RECV(MsgReceivev, const struct iovec *, rcvid_t, 1)
QDT_RECV(MsgReceivev_r, const struct iovec *, rcvid_t, 1)
QDT_RECV(MsgReceivePulse, void *, int, 0)
QDT_RECV(MsgReceivePulse_r, void *, int, 0)
