/* parser <me>: decodes the TLV stream from the modem, one frame per 100 ms. */
#include "../common/qd.h"

static volatile unsigned char frame[64];   /* filled by the DMA callback on target */

static int build_frame(int n) {                   /* stand-in for the modem read */
  int len = 0;
  for (int i = 0; i < 4; i++) {
    int vlen = (n == 6 && i == 2) ? 0 : 3;        /* empty optional field from the newer firmware */
    frame[len] = (unsigned char)(i + 1); frame[len + 1] = (unsigned char)vlen;
    len += 2 + vlen;
  }
  return len;
}

static volatile int last_fields;                /* shown by the debug shell */

int main(int argc, char **argv) {
  const char *me = argv[1];
  for (int n = 0;; n++) {
    int len = build_frame(n), off = 0, fields = 0;
    while (off < len) {
      int vlen = frame[off + 1];
      if (vlen == 0) continue;                    /* skip empty field */
      off += 2 + vlen;
      fields++;
    }
    last_fields = fields;
    qd_tick(me, n);
    usleep(100000);
  }
}
