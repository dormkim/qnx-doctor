#include "../common/qd.h"
#include <semaphore.h>
static int chid;
static sem_t go;   /* initialised to 3, never posted */
static void *worker(void *unused) {   /* a receiver exists, but it waits for a permit first */
  (void)unused;
  qd_msg_t m;
  for (;;) {
    sem_wait(&go);
    int r = qd_receive(chid, &m);
    if (r > 0) MsgReply(r, EOK, &m.app.v, sizeof m.app.v);
  }
  return NULL;
}
int main(void) {   /* looks like ss01 in the wait states, but the cause is the semaphore */
  pthread_t t;
  sem_init(&go, 0, 3);
  chid = ChannelCreate(0);
  pthread_create(&t, NULL, worker, NULL);
  int coid = ConnectAttach(0, 0, chid, _NTO_SIDE_CHANNEL, 0);
  for (int n = 0;; n++) {
    qd_tick("gated", n);
    qd_send(coid, n);
    usleep(100000);
  }
}
