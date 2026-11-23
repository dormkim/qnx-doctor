/* ui <me> <catalogd> <req role> <req role> <event role>: list view.
 * Two request threads keep the visible rows fresh; the event thread answers catalogd's visibility queries
 * and, when a refresh has started, fetches the new list header so the view redraws without a flicker. */
#include <time.h>
#include "../common/qd.h"

#define REFRESH 0x10000
#define HEADER  0x20000
static name_attach_t *att;
static int cat;
static volatile int want_header;
static pthread_barrier_t bar;
static const char *r_ev;

static void tick_to(FILE **f, const char *role, int n) {
  if (!*f) { char p[64]; snprintf(p, sizeof p, "/tmp/d0%s.log", role); *f = fopen(p, "a"); }
  if (*f) { fprintf(*f, "TICK %s %d\n", role, n); fflush(*f); }
}

static void *rows(void *arg) {
  const char *role = arg; FILE *f = NULL;
  pthread_setname_np(pthread_self(), role);
  for (int n = 0;; n++) {
    int v = n;
    if (n == 8) {                                 /* both halves of the page refresh together */
      pthread_barrier_wait(&bar);
      want_header = 1;
      v |= REFRESH;
    }
    if (qd_send(cat, v) < 0) perror("row");
    tick_to(&f, role, n);
    usleep(100000);
  }
  return NULL;
}

static void *events(void *arg) {
  FILE *f = NULL; qd_msg_t m;
  pthread_setname_np(pthread_self(), r_ev);
  for (int n = 0, idle = 0;;) {
    uint64_t to = 50000000;                       /* 50 ms */
    TimerTimeout(CLOCK_MONOTONIC, _NTO_TIMEOUT_RECEIVE, NULL, &to, NULL);
    rcvid_t rcvid = MsgReceive(att->chid, &m, sizeof m, NULL);
    if (rcvid > 0) {
      if (m.type == _IO_CONNECT) { MsgReply(rcvid, EOK, NULL, 0); continue; }
      if (m.type != QD_MSG) { MsgError(rcvid, ENOSYS); continue; }
      int on = 1;                                 /* still on screen */
      MsgReply(rcvid, EOK, &on, sizeof on);
      tick_to(&f, r_ev, n++);
      continue;
    }
    if (want_header) { want_header = 0; if (qd_send(cat, HEADER) < 0) perror("header"); }
    if (++idle % 4 == 0) tick_to(&f, r_ev, n++);
  }
  return arg;
}

int main(int argc, char **argv) {
  if (argc < 6) return 2;
  att = qd_attach(argv[1]);
  r_ev = argv[5];
  pthread_barrier_init(&bar, NULL, 2);
  pthread_t e, a, b;
  pthread_create(&e, NULL, events, NULL);
  cat = qd_open(argv[2]);
  pthread_create(&a, NULL, rows, argv[3]);
  pthread_create(&b, NULL, rows, argv[4]);
  pthread_join(a, NULL); pthread_join(b, NULL); pthread_join(e, NULL);
  return 0;
}
