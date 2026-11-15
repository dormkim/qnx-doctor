/* slow client|server: a correct request/response pair where the server takes a while (it sleeps). Not a fault. */
#include "../common/qd.h"
static void client(void) { qd_attach("d06cli"); int s = qd_open("d06srv"); for (int n = 0;; n++) { qd_send(s, n); qd_tick("client", n); } }
static void server(void) {
  name_attach_t *a = qd_attach("d06srv"); qd_msg_t m;
  for (;;) { int rcvid = qd_receive(a->chid, &m); if (rcvid <= 0) continue; sleep(1); MsgReply(rcvid, EOK, &m.app.v, sizeof m.app.v); }
}
int main(int argc, char **argv) { if (!strcmp(argv[1], "client")) client(); if (!strcmp(argv[1], "server")) server(); return 2; }
