/* catalogd <me> <ui> <worker role> <worker role>: catalog service, two worker threads on one channel.
 * REFRESH reloads an index page and then asks the ui whether the entry is still on screen (if not, the
 * page is dropped again); HEADER returns the list header. */
#include "../common/qd.h"

#define REFRESH 0x10000
#define HEADER  0x20000
static name_attach_t *att;
static const char *ui_name;

static void *worker(void *arg) {
  const char *role = arg;
  FILE *f = NULL;
  pthread_setname_np(pthread_self(), role);
  int ui = qd_open(ui_name);
  qd_msg_t m;
  for (int n = 0;;) {
    int rcvid = qd_receive(att->chid, &m);
    if (rcvid == 0) continue;
    int v = m.app.v;
    if (v & REFRESH) {
      usleep(100000);                             /* reload the index page from flash */
      if (qd_send(ui, v & 0xffff) < 0) perror("visible?");
    }
    MsgReply(rcvid, EOK, &v, sizeof v);
    if (!f) { char p[64]; snprintf(p, sizeof p, "/tmp/d0%s.log", role); f = fopen(p, "a"); }
    if (f) { fprintf(f, "TICK %s %d\n", role, n++); fflush(f); }
  }
  return NULL;
}

int main(int argc, char **argv) {
  if (argc < 5) return 2;
  att = qd_attach(argv[1]);
  ui_name = argv[2];
  pthread_t a, b;
  pthread_create(&a, NULL, worker, argv[3]);
  pthread_create(&b, NULL, worker, argv[4]);
  pthread_join(a, NULL); pthread_join(b, NULL);
  return 0;
}
