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

/* auditd: safety log. Each entry records the planner's own plan count, read back from the planner. */
int main(void) {
  name_attach_t *a = qd_attach("auditd");
  int pl = -1;
  qd_msg_t m;
  for (;;) {
    int rcvid = qd_receive(a->chid, &m);
    if (rcvid <= 0) continue;
    if (pl == -1) pl = lookup("planner");
    int count = qd_send(pl, -1);
    fprintf(stderr, "auditd: entry %d (planner says %d)\n", m.app.v, count);
    MsgReply(rcvid, EOK, NULL, 0);
  }
}
