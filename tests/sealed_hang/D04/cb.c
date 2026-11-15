/* cb client|server: the server notifies the client of progress. */
#include "../common/qd.h"
static void client(void) {
  name_attach_t *a = qd_attach("d04cli"); int s = qd_open("d04srv"); (void)a;
  for (int n = 0;; n++) { qd_send(s, n); qd_tick("client", n); usleep(100000); }
}
static void server(void) {
  name_attach_t *a = qd_attach("d04srv"); int cli = -1; qd_msg_t m;
  for (;;) {
    int rcvid = qd_receive(a->chid, &m);
    if (rcvid <= 0) continue;
    if (cli == -1) cli = qd_open("d04cli");
    qd_send(cli, m.app.v);            /* QD-CULPRIT: synchronous callback to the client that is waiting for our reply */
    MsgReply(rcvid, EOK, &m.app.v, sizeof m.app.v);
  }
}
int main(int argc, char **argv) {
  if (!strcmp(argv[1], "client")) client();
  if (!strcmp(argv[1], "server")) server();
  return 2;
}
