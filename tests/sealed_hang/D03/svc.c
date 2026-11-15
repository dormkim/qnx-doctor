/* svc client|server|logger: request/response service with a logger on the side. */
#include "../common/qd.h"
static void client(void) {
  qd_attach("d03cli"); int s = qd_open("d03srv");
  for (int n = 0;; n++) { qd_send(s, n); qd_tick("client", n); usleep(100000); }
}
static void server(void) {
  name_attach_t *a = qd_attach("d03srv"); int lg = qd_open("d03log"); qd_msg_t m;
  for (;;) {
    int rcvid = qd_receive(a->chid, &m);
    if (rcvid <= 0) continue;
    qd_send(lg, m.app.v);             /* ask the logger to record the request before answering */
    MsgReply(rcvid, EOK, &m.app.v, sizeof m.app.v);
  }
}
static void logger(void) {
  name_attach_t *a = qd_attach("d03log"); int s = qd_open("d03srv"); qd_msg_t m;
  for (int n = 0;; n++) {
    qd_send(s, -n);                   /* QD-CULPRIT: logger pushes its status to the server synchronously */
    int rcvid = qd_receive(a->chid, &m);
    if (rcvid > 0) MsgReply(rcvid, EOK, NULL, 0);
  }
}
int main(int argc, char **argv) {
  if (!strcmp(argv[1], "client")) client();
  if (!strcmp(argv[1], "server")) server();
  if (!strcmp(argv[1], "logger")) logger();
  return 2;
}
