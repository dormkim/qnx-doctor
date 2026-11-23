/* sessmgr <login role> <reaper role> <watchdog role>: session table with an expiry reaper.
 * The watchdog thread heartbeats so the supervisor can restart us if a worker gets stuck. */
#include "../common/qd.h"

static pthread_mutex_t tbl_mx = PTHREAD_MUTEX_INITIALIZER;   /* session table (list links) */
static pthread_mutex_t sess_mx = PTHREAD_MUTEX_INITIALIZER;  /* the active session record */
static struct { int id, last_seen, expired; } sess;
static const char *r_login, *r_reap, *r_wd;

static void beat(FILE **f, const char *role, int n) {
  if (!*f) { char p[64]; snprintf(p, sizeof p, "/tmp/d0%s.log", role); *f = fopen(p, "a"); }
  if (*f) { fprintf(*f, "TICK %s %d\n", role, n); fflush(*f); }
}

static void *login(void *x) {
  FILE *f = NULL;
  pthread_setname_np(pthread_self(), r_login);
  for (int n = 0;; n++) {
    pthread_mutex_lock(&tbl_mx);                  /* look the session up */
    pthread_mutex_lock(&sess_mx);
    sess.last_seen = n;
    pthread_mutex_unlock(&sess_mx);
    pthread_mutex_unlock(&tbl_mx);
    beat(&f, r_login, n);
    usleep(80000);
  }
  return x;
}

static void *reaper(void *x) {
  FILE *f = NULL;
  pthread_setname_np(pthread_self(), r_reap);
  for (int n = 0;; n++) {
    pthread_mutex_lock(&sess_mx);
    sess.expired = (n == 4);                      /* idle-timeout check (test build: forced on pass 4) */
    if (sess.expired) {
      usleep(250000);                             /* write the audit record before unlinking */
      pthread_mutex_lock(&tbl_mx);
      sess.id++;
      pthread_mutex_unlock(&tbl_mx);
    }
    pthread_mutex_unlock(&sess_mx);
    beat(&f, r_reap, n);
    usleep(150000);
  }
  return x;
}

static void *watchdog(void *x) {
  FILE *f = NULL;
  pthread_setname_np(pthread_self(), r_wd);
  for (int n = 0;; n++) { beat(&f, r_wd, n); usleep(200000); }
  return x;
}

int main(int argc, char **argv) {
  if (argc < 4) return 2;
  r_login = argv[1]; r_reap = argv[2]; r_wd = argv[3];
  pthread_t t[3];
  pthread_create(&t[0], NULL, login, NULL);
  pthread_create(&t[1], NULL, reaper, NULL);
  pthread_create(&t[2], NULL, watchdog, NULL);
  for (int i = 0; i < 3; i++) pthread_join(t[i], NULL);
  return 0;
}
