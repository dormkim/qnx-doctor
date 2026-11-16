#include "../common/qd.h"
#include <time.h>
#include <signal.h>
/* indexer: media library indexer; CPU bound by design.
 * usage: <delay_ms> <prio> <threads> [busy_ms idle_ms]   (no idle = run flat out) */

static uint64_t now_ns(void) {
  struct timespec t; clock_gettime(CLOCK_MONOTONIC, &t);
  return (uint64_t)t.tv_sec * 1000000000ULL + (uint64_t)t.tv_nsec;
}

static int prio, busy_ms, idle_ms;
static void *work(void *arg) {
  (void)arg;
  setprio(0, prio);
  volatile unsigned long acc = 0;
  for (;;) {
    if (!idle_ms) { acc++; continue; }
    uint64_t end = now_ns() + (uint64_t)busy_ms * 1000000ULL;
    while (now_ns() < end) acc++;
    usleep(idle_ms * 1000);
  }
  return NULL;
}
int main(int argc, char **argv) {
  if (argc < 4) return 2;
  int delay = atoi(argv[1]), n = atoi(argv[3]);
  prio = atoi(argv[2]);
  if (argc > 5) { busy_ms = atoi(argv[4]); idle_ms = atoi(argv[5]); }
  usleep(delay * 1000);          /* let the rest of the system come up first */
  pthread_t t;
  for (int i = 0; i < n; i++) pthread_create(&t, NULL, work, NULL);
  for (;;) pause();
}
