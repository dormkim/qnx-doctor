/* logrot <ingest role> <rotate role>: log writer with in-process rotation.
 * ingest formats records into buf and appends them to the file; rotate closes and reopens the file
 * every few cycles. Both touch buf and file, each under its own mutex. */
#include "../common/qd.h"

static pthread_mutex_t buf_mx = PTHREAD_MUTEX_INITIALIZER;   /* protects buf[] */
static pthread_mutex_t file_mx = PTHREAD_MUTEX_INITIALIZER;  /* protects the output file */
static char buf[512];
static const char *role_in, *role_rot;

static void note(FILE **f, const char *role, int n) {
  if (!*f) { char p[64]; snprintf(p, sizeof p, "/tmp/d0%s.log", role); *f = fopen(p, "a"); }
  if (*f) { fprintf(*f, "TICK %s %d\n", role, n); fflush(*f); }
}

static void *ingest(void *arg) {
  FILE *log = NULL;
  pthread_setname_np(pthread_self(), role_in);
  for (int n = 0;; n++) {
    pthread_mutex_lock(&buf_mx);
    snprintf(buf, sizeof buf, "rec %d", n);
    usleep(20000);                                /* format + checksum */
    pthread_mutex_lock(&file_mx);
    /* append buf */
    pthread_mutex_unlock(&file_mx);
    pthread_mutex_unlock(&buf_mx);
    note(&log, role_in, n);
    usleep(50000);
  }
  return arg;
}

static void *rotate(void *arg) {
  FILE *log = NULL;
  pthread_setname_np(pthread_self(), role_rot);
  for (int n = 0;; n++) {
    if (n > 0 && n % 5 == 0) {
      pthread_mutex_lock(&file_mx);               /* rotation: close, rename, reopen */
      usleep(300000);
      pthread_mutex_lock(&buf_mx);                /* drop what was formatted for the old file */
      buf[0] = 0;
      pthread_mutex_unlock(&buf_mx);
      pthread_mutex_unlock(&file_mx);
    } else {
      pthread_mutex_lock(&buf_mx);
      pthread_mutex_lock(&file_mx);
      /* size check */
      pthread_mutex_unlock(&file_mx);
      pthread_mutex_unlock(&buf_mx);
    }
    note(&log, role_rot, n);
    usleep(150000);
  }
  return arg;
}

int main(int argc, char **argv) {
  if (argc < 3) return 2;
  role_in = argv[1]; role_rot = argv[2];
  pthread_t a, b;
  pthread_create(&a, NULL, ingest, NULL);
  pthread_create(&b, NULL, rotate, NULL);
  pthread_join(a, NULL);
  pthread_join(b, NULL);
  return 0;
}
