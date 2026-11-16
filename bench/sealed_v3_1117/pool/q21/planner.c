#include "../common/qd.h"
#include <time.h>
#include <signal.h>

/* The channel id is published in /tmp so clients can attach without the name service. */
static void publish(const char *name, int chid) {
  char p[64], t[64];
  snprintf(p, sizeof p, "/tmp/%s.id", name); snprintf(t, sizeof t, "/tmp/%s.new", name);
  FILE *f = fopen(t, "w");
  if (!f) { perror("publish"); exit(1); }
  fprintf(f, "%d %d\n", getpid(), chid); fclose(f); rename(t, p);
}
static int lookup(const char *name) {
  char p[64]; snprintf(p, sizeof p, "/tmp/%s.id", name);
  for (int i = 0; i < 200; i++) {
    FILE *f = fopen(p, "r"); int pid, chid;
    if (f) {
      int ok = fscanf(f, "%d %d", &pid, &chid) == 2; fclose(f);
      if (ok) { int c = ConnectAttach(0, pid, chid, _NTO_SIDE_CHANNEL, 0); if (c != -1) return c; }
    }
    usleep(25000);
  }
  fprintf(stderr, "lookup %s failed\n", name); exit(1);
}

/* planner: path planner on a fixed-priority channel (priority 7). Every 30th plan is sent to auditd
 * for the safety log before the pilot gets it. Queries (v < 0) return the plan count. */
int main(void) {
  int chid = ChannelCreate(_NTO_CHF_FIXED_PRIORITY);
  setprio(0, 7);
  publish("planner", chid);
  int au = -1, plans = 0;
  qd_msg_t m;
  for (;;) {
    int rcvid = MsgReceive(chid, &m, sizeof m, NULL);
    if (rcvid <= 0) continue;
    if (m.app.v < 0) { MsgReply(rcvid, EOK, &plans, sizeof plans); continue; }
    volatile long x = 0;
    for (long i = 0; i < 50000; i++) x += i;
    plans++;
    if (plans % 30 == 0) {
      if (au == -1) au = qd_open("auditd");
      qd_send(au, plans);
    }
    MsgReply(rcvid, EOK, &plans, sizeof plans);
  }
}
