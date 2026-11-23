/* bgcrc <me>: background flash CRC scrub, priority 15. */
#include "../common/qd.h"
static volatile unsigned crc;
int main(int argc, char **argv) {
  const char *me = argv[1];
  setprio(0, 15);
  usleep(1200000);
  qd_tick(me, 0);
  for (unsigned i = 0;; i++) crc = (crc >> 1) ^ (0xEDB88320u & -(int)((crc ^ i) & 1));
}
