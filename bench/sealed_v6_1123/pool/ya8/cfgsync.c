/* cfgsync <snapshot role> <reader role>: keeps the config block consistent with flash.
 * snapshot holds cfg_mx across the whole flash write; reader must never see a half-written block. */
#include "../common/qd.h"

static pthread_mutex_t cfg_mx = PTHREAD_MUTEX_INITIALIZER;
static int cfg[16];
static const char *r_snap, *r_rd;

static void put(FILE **f, const char *role, int n) {
  if (!*f) { char p[64]; snprintf(p, sizeof p, "/tmp/d0%s.log", role); *f = fopen(p, "a"); }
  if (*f) { fprintf(*f, "TICK %s %d\n", role, n); fflush(*f); }
}

static void *snapshot(void *x) {
  FILE *f = NULL; pthread_setname_np(pthread_self(), r_snap);
  for (int n = 0;; n++) {
    pthread_mutex_lock(&cfg_mx);
    cfg[n & 15] = n;
    usleep(350000);                               /* flash program + verify */
    pthread_mutex_unlock(&cfg_mx);
    usleep(20000);
    put(&f, r_snap, n);
  }
  return x;
}

static void *reader(void *x) {
  FILE *f = NULL; pthread_setname_np(pthread_self(), r_rd);
  static volatile int sum;
  for (int n = 0;; n++) {
    pthread_mutex_lock(&cfg_mx);
    for (int i = 0; i < 16; i++) sum += cfg[i];
    put(&f, r_rd, n);
    pthread_mutex_unlock(&cfg_mx);
    usleep(5000);
  }
  return x;
}

int main(int argc, char **argv) {
  if (argc < 3) return 2;
  r_snap = argv[1]; r_rd = argv[2];
  pthread_t a, b;
  pthread_create(&a, NULL, snapshot, NULL);
  pthread_create(&b, NULL, reader, NULL);
  pthread_join(a, NULL); pthread_join(b, NULL);
  return 0;
}
