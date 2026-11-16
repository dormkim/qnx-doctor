#include "../common/qd.h"
#include <time.h>
#include <signal.h>

/* codecd: the receive thread only queues requests. A background worker at a low, fixed priority decodes
 * and replies, so a burst of requests cannot starve the receive thread. */
static pthread_mutex_t mu = PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t cv = PTHREAD_COND_INITIALIZER;
static int qr[64], qv[64], head, tail;
static void *worker(void *arg) {
  (void)arg;
  setprio(0, 6);
  for (;;) {
    pthread_mutex_lock(&mu);
    while (head == tail) pthread_cond_wait(&cv, &mu);
    int rcvid = qr[head % 64], v = qv[head % 64]; head++;
    pthread_mutex_unlock(&mu);
    volatile long x = 0;
    for (long i = 0; i < 100000; i++) x += i;          /* decode one block */
    int out = v + (int)(x & 1);
    MsgReply(rcvid, EOK, &out, sizeof out);
  }
  return NULL;
}
int main(void) {
  name_attach_t *a = qd_attach("codecd");
  pthread_t t; pthread_create(&t, NULL, worker, NULL);
  qd_msg_t m;
  for (;;) {
    int rcvid = qd_receive(a->chid, &m);
    if (rcvid <= 0) continue;
    pthread_mutex_lock(&mu);
    qr[tail % 64] = rcvid; qv[tail % 64] = m.app.v; tail++;
    pthread_cond_signal(&cv);
    pthread_mutex_unlock(&mu);
  }
}
