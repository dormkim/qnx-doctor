#include "../common/qd.h"
#include <time.h>
#include <signal.h>

/* telemetryd: collects telemetry samples. */
int main(void) {
  name_attach_t *a = qd_attach("telemetry-d");
  qd_msg_t m;
  for (;;) { int rcvid = qd_receive(a->chid, &m); if (rcvid > 0) MsgReply(rcvid, EOK, NULL, 0); }
}
