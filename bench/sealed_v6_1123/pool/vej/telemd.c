/* telemd <ctl role> <uplink role> <compress role>: telemetry daemon.
 *   ctl      (prio 30) samples the command queue every 100 ms
 *   uplink   (prio  5) packs queued records for the radio
 *   compress (prio 15) compresses a full batch when uplink hands one over
 * q_mx uses PTHREAD_PRIO_NONE: the critical sections are a few microseconds and we measured the
 * inheritance bookkeeping on this board. */
#include <semaphore.h>
#include <time.h>
#include "../common/qd.h"

static pthread_mutex_t q_mx;
static sem_t batch_ready;
static int queue_len;
static const char *r_ctl, *r_up, *r_cmp;

static void burn_ms(int ms) {
  struct timespec t0, t; clock_gettime(CLOCK_MONOTONIC, &t0);
  do clock_gettime(CLOCK_MONOTONIC, &t);
  while ((t.tv_sec - t0.tv_sec) * 1000 + (t.tv_nsec - t0.tv_nsec) / 1000000 < ms);
}
static void out(FILE **f, const char *role, int n) {
  if (!*f) { char p[64]; snprintf(p, sizeof p, "/tmp/d0%s.log", role); *f = fopen(p, "a"); }
  if (*f) { fprintf(*f, "TICK %s %d\n", role, n); fflush(*f); }
}

static void *ctl(void *x) {
  FILE *f = NULL; setprio(0, 30); pthread_setname_np(pthread_self(), r_ctl);
  for (int n = 0;; n++) {
    pthread_mutex_lock(&q_mx);
    queue_len++;
    pthread_mutex_unlock(&q_mx);
    out(&f, r_ctl, n);
    usleep(100000);
  }
  return x;
}

static void *uplink(void *x) {
  FILE *f = NULL; setprio(0, 5); pthread_setname_np(pthread_self(), r_up);
  for (int n = 0;; n++) {
    pthread_mutex_lock(&q_mx);
    burn_ms(10);                                  /* pack */
    if (n == 6) sem_post(&batch_ready);           /* first full batch */
    burn_ms(10);
    queue_len = 0;
    pthread_mutex_unlock(&q_mx);
    out(&f, r_up, n);
    usleep(50000);
  }
  return x;
}

static void *compress(void *x) {
  FILE *f = NULL; setprio(0, 15); pthread_setname_np(pthread_self(), r_cmp);
  int n = 0;
  for (;;) {
    sem_wait(&batch_ready);
    for (int blk = 0; blk < 1200; blk++) {        /* 1200 blocks of ~50 ms */
      burn_ms(50);
      if (blk % 4 == 3) out(&f, r_cmp, n++);
    }
  }
  return x;
}

int main(int argc, char **argv) {
  if (argc < 4) return 2;
  r_ctl = argv[1]; r_up = argv[2]; r_cmp = argv[3];
  pthread_mutexattr_t ma; pthread_mutexattr_init(&ma);
  pthread_mutexattr_setprotocol(&ma, PTHREAD_PRIO_NONE);
  pthread_mutex_init(&q_mx, &ma);
  sem_init(&batch_ready, 0, 0);
  pthread_t t[3];
  pthread_create(&t[0], NULL, compress, NULL);
  pthread_create(&t[1], NULL, uplink, NULL);
  pthread_create(&t[2], NULL, ctl, NULL);
  for (int i = 0; i < 3; i++) pthread_join(t[i], NULL);
  return 0;
}
