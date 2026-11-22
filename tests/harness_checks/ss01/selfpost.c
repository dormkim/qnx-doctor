#include "../common/qd.h"
int main(void) {   /* sends to a channel of its own process; no thread receives on it */
  int chid = ChannelCreate(0);
  int coid = ConnectAttach(0, 0, chid, _NTO_SIDE_CHANNEL, 0);
  for (int n = 0;; n++) {
    qd_tick("selfpost", n);
    qd_send(coid, n);
    usleep(100000);
  }
}
