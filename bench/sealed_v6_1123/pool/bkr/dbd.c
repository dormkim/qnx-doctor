/* dbd <me> <owner service>: record database with a small cache. On a cache miss the owner of the key is
 * asked first (the owner publishes "pid chid" in /tmp/<owner>.ep). */
#include "../common/qd.h"
static int owner_coid(const char *who) {
  char p[64]; snprintf(p, sizeof p, "/tmp/%s.ep", who);
  for (;;) {
    FILE *f = fopen(p, "r");
    if (f) { int pid, chid, ok = fscanf(f, "%d %d", &pid, &chid) == 2; fclose(f);
      if (ok) { int c = ConnectAttach(0, pid, chid, _NTO_SIDE_CHANNEL, 0); if (c != -1) return c; } }
    usleep(50000);
  }
}
int main(int argc, char **argv) {
  const char *me = argv[1];
  name_attach_t *a = qd_attach(me);
  int owner = owner_coid(argv[2]);
  qd_msg_t m;
  int cache[8] = { 0 };
  for (int n = 0;;) {
    int rcvid = qd_receive(a->chid, &m);
    if (rcvid == 0) continue;
    int key = m.app.v, val;
    if (key < 5) val = cache[key & 7] = key * 3;  /* preloaded keys */
    else val = qd_send(owner, key);               /* miss: ask the owner */
    MsgReply(rcvid, EOK, &val, sizeof val);
    qd_tick(me, n++);
  }
}
