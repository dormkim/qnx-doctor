/* lidar <me>: scan server. Returns the latest scan; the driver answers within a few ms. */
#include "../common/qd.h"
int main(int argc, char **argv) {
  const char *me = argv[1];
  name_attach_t *a = qd_attach(me);
  qd_msg_t m;
  for (int n = 0;;) {
    int rcvid = qd_receive(a->chid, &m);
    if (rcvid == 0) continue;
    usleep(350000);                               /* wait for the mirror to complete a revolution */
    int scan = n;
    qd_tick(me, n++);
    MsgReply(rcvid, EOK, &scan, sizeof scan);
  }
}
