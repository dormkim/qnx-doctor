/* stage <me> <next>: one stage of the frame pipeline (acquire -> scale -> encode -> acquire).
 * Each stage pushes its frame index downstream, then takes the frame coming from upstream.
 * Endpoints are published as "pid chid" in /tmp/<name>.ep so stages do not wait on the name server at boot. */
#include "../common/qd.h"

static void ep_publish(const char *me, int chid) {
  char p[64]; snprintf(p, sizeof p, "/tmp/%s.ep", me);
  FILE *f = fopen(p, "w"); if (!f) { perror("ep_publish"); exit(1); }
  fprintf(f, "%d %d\n", getpid(), chid); fclose(f);
}
static int ep_connect(const char *peer) {
  char p[64]; snprintf(p, sizeof p, "/tmp/%s.ep", peer);
  for (;;) {
    FILE *f = fopen(p, "r");
    if (f) { int pid = -1, chid = -1, ok = fscanf(f, "%d %d", &pid, &chid) == 2; fclose(f);
      if (ok) { int c = ConnectAttach(0, pid, chid, _NTO_SIDE_CHANNEL, 0); if (c != -1) return c; } }
    usleep(50000);
  }
}

int main(int argc, char **argv) {
  if (argc < 3) return 2;
  const char *me = argv[1], *next = argv[2];
  int chid = ChannelCreate(0);
  if (chid == -1) { perror("ChannelCreate"); exit(1); }
  ep_publish(me, chid);
  for (int w = 0; w < 3; w++) { usleep(100000); qd_tick(me, w); }   /* warm-up: prime the local buffers */
  int down = ep_connect(next);
  qd_msg_t m;
  for (int n = 3;; n++) {
    qd_send(down, n);                      /* downstream acks as soon as the frame is queued */
    int rcvid = qd_receive(chid, &m);
    if (rcvid > 0) MsgReply(rcvid, EOK, &n, sizeof n);
    qd_tick(me, n);
  }
}
