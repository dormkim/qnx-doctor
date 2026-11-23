/* bus <me> <eeprom>: I2C bus arbiter; serialises access and forwards to the device server. Priority 14. */
#include "../common/qd.h"
int main(int argc, char **argv) {
  const char *me = argv[1];
  name_attach_t *a = qd_attach(me);
  setprio(0, 14);
  int dev = qd_open_fixed(argv[2]);
  qd_msg_t m;
  for (int n = 0;;) {
    int rcvid = qd_receive(a->chid, &m);
    if (rcvid == 0) continue;
    int r = qd_send(dev, m.app.v);
    MsgReply(rcvid, EOK, &r, sizeof r);
    qd_tick(me, n++);
  }
}
