/* batchd <me> <flush role>: batches log writes. The main thread queues each request; the flush thread
 * writes the batch out and replies to everyone in it every 250 ms, or earlier when the queue is full. */
#include <time.h>
#include "../common/qd.h"
#define QMAX 16
static pthread_mutex_t q_mx = PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t q_cv;
static int q[QMAX], qn;
static const char *r_fl;

static void *flusher(void *x) {
  FILE *f = NULL; pthread_setname_np(pthread_self(), r_fl);
  char p[64]; snprintf(p, sizeof p, "/tmp/d0%s.log", r_fl); f = fopen(p, "a");
  int n = 0;
  pthread_mutex_lock(&q_mx);
  for (;;) {
    struct timespec dl; clock_gettime(CLOCK_MONOTONIC, &dl);
    dl.tv_nsec += 250000000; if (dl.tv_nsec >= 1000000000) { dl.tv_sec++; dl.tv_nsec -= 1000000000; }
    while (qn < QMAX && pthread_cond_timedwait(&q_cv, &q_mx, &dl) == 0) { }
    for (int i = 0; i < qn; i++) MsgReply(q[i], EOK, &n, sizeof n);
    qn = 0;
    if (f) { fprintf(f, "TICK %s %d\n", r_fl, n++); fflush(f); }
  }
  return x;
}

int main(int argc, char **argv) {
  if (argc < 3) return 2;
  const char *me = argv[1]; r_fl = argv[2];
  name_attach_t *a = qd_attach(me);
  pthread_condattr_t ca; pthread_condattr_init(&ca);
  pthread_condattr_setclock(&ca, CLOCK_MONOTONIC);
  pthread_cond_init(&q_cv, &ca);
  pthread_t t; pthread_create(&t, NULL, flusher, NULL);
  qd_msg_t m;
  for (int n = 0;;) {
    int rcvid = qd_receive(a->chid, &m);
    if (rcvid == 0) continue;
    pthread_mutex_lock(&q_mx);
    if (qn < QMAX) q[qn++] = rcvid; else MsgError(rcvid, EAGAIN);
    if (qn == QMAX) pthread_cond_signal(&q_cv);
    pthread_mutex_unlock(&q_mx);
    qd_tick(me, n++);
  }
}
