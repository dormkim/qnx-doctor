/* camsvc <isr role> <dma role> <stats role>: camera service.
 *   isr   (prio 28) acknowledges frame interrupts, needs the frame descriptor briefly
 *   dma   (prio  6) copies a frame out while holding the descriptor
 *   stats (prio 12) exports frame statistics every 6th frame, right after that frame's copy finishes
 * frame_mx is PRIO_NONE on purpose: we do not want the isr thread's priority lent to bulk copies. */
#include <time.h>
#include "../common/qd.h"

static pthread_mutex_t frame_mx;
static pthread_mutex_t st_mx = PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t st_cv = PTHREAD_COND_INITIALIZER;
static volatile int dma_done, export_req;
static const char *r_isr, *r_dma, *r_st;

static void spin_ms(int ms) {
  struct timespec a, b; clock_gettime(CLOCK_MONOTONIC, &a);
  do clock_gettime(CLOCK_MONOTONIC, &b);
  while ((b.tv_sec - a.tv_sec) * 1000 + (b.tv_nsec - a.tv_nsec) / 1000000 < ms);
}
static void mark(FILE **f, const char *role, int n) {
  if (!*f) { char p[64]; snprintf(p, sizeof p, "/tmp/d0%s.log", role); *f = fopen(p, "a"); }
  if (*f) { fprintf(*f, "TICK %s %d\n", role, n); fflush(*f); }
}

static void *isr(void *x) {
  FILE *f = NULL; setprio(0, 28); pthread_setname_np(pthread_self(), r_isr);
  for (int n = 0;; n++) {
    pthread_mutex_lock(&frame_mx);
    /* ack */
    pthread_mutex_unlock(&frame_mx);
    mark(&f, r_isr, n);
    usleep(100000);
  }
  return x;
}

static void *dma(void *x) {
  FILE *f = NULL; setprio(0, 6); pthread_setname_np(pthread_self(), r_dma);
  for (int n = 0;; n++) {
    pthread_mutex_lock(&frame_mx);
    dma_done = 0;
    if (n % 6 == 5) {                             /* stats wants this frame */
      pthread_mutex_lock(&st_mx); export_req = 1; pthread_cond_signal(&st_cv); pthread_mutex_unlock(&st_mx);
    }
    spin_ms(20);                                  /* copy */
    dma_done = 1;
    pthread_mutex_unlock(&frame_mx);
    mark(&f, r_dma, n);
    usleep(40000);
  }
  return x;
}

static void *stats(void *x) {
  FILE *f = NULL; setprio(0, 12); pthread_setname_np(pthread_self(), r_st);
  for (int n = 0;; n++) {
    pthread_mutex_lock(&st_mx);
    while (!export_req) pthread_cond_wait(&st_cv, &st_mx);
    export_req = 0;
    pthread_mutex_unlock(&st_mx);
    while (!dma_done) { }                         /* copy finishes within ~20 ms */
    mark(&f, r_st, n);
  }
  return x;
}

int main(int argc, char **argv) {
  if (argc < 4) return 2;
  r_isr = argv[1]; r_dma = argv[2]; r_st = argv[3];
  pthread_mutexattr_t ma; pthread_mutexattr_init(&ma);
  pthread_mutexattr_setprotocol(&ma, PTHREAD_PRIO_NONE);
  pthread_mutex_init(&frame_mx, &ma);
  pthread_t t[3];
  pthread_create(&t[0], NULL, stats, NULL);
  pthread_create(&t[1], NULL, dma, NULL);
  pthread_create(&t[2], NULL, isr, NULL);
  for (int i = 0; i < 3; i++) pthread_join(t[i], NULL);
  return 0;
}
