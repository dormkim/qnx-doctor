#include "../common/qd.h"
static int chid;
static void *worker(void *unused) {   /* the second thread: receives, works a little, replies */
  (void)unused;
  qd_msg_t m;
  for (;;) {
    int r = qd_receive(chid, &m);
    if (r > 0) { usleep(150000); MsgReply(r, EOK, &m.app.v, sizeof m.app.v); }
  }
  return NULL;
}
int main(void) {   /* sends to a channel of its own process; another thread of it replies: healthy */
  pthread_t t;
  chid = ChannelCreate(0);
  pthread_create(&t, NULL, worker, NULL);
  int coid = ConnectAttach(0, 0, chid, _NTO_SIDE_CHANNEL, 0);
  for (int n = 0;; n++) {
    qd_tick("inbox", n);
    qd_send(coid, n);
    usleep(50000);
  }
}
