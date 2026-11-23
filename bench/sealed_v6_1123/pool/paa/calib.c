/* calib <ctrl role> <loader role>: control loop with calibration limits.
 * ctrl runs on the built-in defaults for the first 5 cycles, then waits for the loader to publish the
 * board's own limits. The loader keeps retrying until the limits file can be read. */
#include "../common/qd.h"

#define LIMITS_FILE "/etc/calib/limits.cfg"
static pthread_mutex_t lim_mx = PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t lim_cv = PTHREAD_COND_INITIALIZER;
static int have_limits, lo = 0, hi = 100;
static const char *r_ctrl, *r_load;

static void *ctrl(void *x) {
  FILE *f = NULL; pthread_setname_np(pthread_self(), r_ctrl);
  char p[64]; snprintf(p, sizeof p, "/tmp/d0%s.log", r_ctrl); f = fopen(p, "a");
  for (int n = 0;; n++) {
    if (n >= 5) {
      pthread_mutex_lock(&lim_mx);
      while (!have_limits) pthread_cond_wait(&lim_cv, &lim_mx);
      pthread_mutex_unlock(&lim_mx);
    }
    int out = (n * 7) % (hi - lo + 1) + lo;      /* clamp the actuator command */
    (void)out;
    if (f) { fprintf(f, "TICK %s %d\n", r_ctrl, n); fflush(f); }
    usleep(100000);
  }
  return x;
}

static void *loader(void *x) {
  pthread_setname_np(pthread_self(), r_load);
  for (;;) {
    FILE *f = fopen(LIMITS_FILE, "r");
    if (f) {
      int a, b;
      if (fscanf(f, "%d %d", &a, &b) == 2) {
        pthread_mutex_lock(&lim_mx); lo = a; hi = b; have_limits = 1;
        pthread_cond_broadcast(&lim_cv); pthread_mutex_unlock(&lim_mx);
        fclose(f);
        return x;
      }
      fclose(f);
    }
    usleep(250000);
  }
}

int main(int argc, char **argv) {
  if (argc < 3) return 2;
  r_ctrl = argv[1]; r_load = argv[2];
  pthread_t a, b;
  pthread_create(&a, NULL, ctrl, NULL);
  pthread_create(&b, NULL, loader, NULL);
  pthread_join(a, NULL); pthread_join(b, NULL);
  return 0;
}
