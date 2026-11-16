#include "../common/qd.h"
#include <time.h>
#include <signal.h>

/* framestore: keeps camera frames. Every 8th frame it asks the journal to flush, synchronously,
 * so the frame is durable before the camera gets its ack. Stats queries (v < 0) are answered at once. */
static int frames;
int main(void) {
  name_attach_t *a = qd_attach("framestore");
  int jr = -1;
  qd_msg_t m;
  for (;;) {
    int rcvid = qd_receive(a->chid, &m);
    if (rcvid <= 0) continue;
    if (m.app.v < 0) { int f = frames; MsgReply(rcvid, EOK, &f, sizeof f); continue; }
    frames++;
    if (frames % 8 == 0) {
      if (jr == -1) jr = qd_open("journal");
      qd_send(jr, frames);
    }
    MsgReply(rcvid, EOK, &frames, sizeof frames);
  }
}
