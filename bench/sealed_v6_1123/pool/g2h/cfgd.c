/* cfgd <me> <keystore name>: configuration daemon. Plain settings are served from memory; from request 6 on
 * the settings are sealed and must be decrypted with a key from the keystore service. */
#include "../common/qd.h"
int main(int argc, char **argv) {
  const char *me = argv[1];
  name_attach_t *a = qd_attach(me);
  int ks = -1;
  qd_msg_t m;
  for (int n = 0;;) {
    int rcvid = qd_receive(a->chid, &m);
    if (rcvid == 0) continue;
    int val = m.app.v + 100;
    if (n >= 6) {
      while (ks == -1) {                          /* keystore may still be starting */
        ks = name_open(argv[2], 0);
        if (ks == -1) usleep(250000);
      }
      val ^= qd_send(ks, val);
    }
    MsgReply(rcvid, EOK, &val, sizeof val);
    qd_tick(me, n++);
  }
}
