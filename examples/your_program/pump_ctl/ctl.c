/* ctl <name> <pump name>: controller. Once per cycle it sets the pump speed, then reads the pump's reports on its
 * own channel for a short while. Plain QNX 8.0 calls only. */
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <time.h>
#include <unistd.h>
#include <sys/dispatch.h>
#include <sys/iomsg.h>
#include <sys/neutrino.h>

#define SET_SPEED 0x7001
#define REPORT    0x7002
typedef struct { uint16_t type; int32_t chid; int32_t value; } pump_msg_t;

int main(int argc, char **argv) {
  if (argc < 3) return 2;
  int chid = ChannelCreate(0);
  if (chid == -1) { perror("ChannelCreate"); return 1; }
  int pump = -1;
  for (int i = 0; i < 100 && pump == -1; i++) { pump = name_open(argv[2], 0); if (pump == -1) usleep(50000); }
  if (pump == -1) { perror("name_open"); return 1; }
  union { struct _pulse pulse; uint16_t type; pump_msg_t m; char raw[64]; } in;
  for (int n = 0;; n++) {
    pump_msg_t set = { SET_SPEED, chid, 100 + n % 50 }; int reached = 0;
    if (MsgSend(pump, &set, sizeof set, &reached, sizeof reached) == -1) perror("set speed");
    printf("TICK %s %d\n", argv[1], n); fflush(stdout);
    for (;;) {                                     /* read reports for 20 ms */
      uint64_t to = 20000000;
      TimerTimeout(CLOCK_MONOTONIC, _NTO_TIMEOUT_RECEIVE, NULL, &to, NULL);
      rcvid_t rcvid = MsgReceive(chid, &in, sizeof in, NULL);
      if (rcvid == -1) break;
      if (rcvid == 0) continue;
      if (in.type != REPORT) { MsgError(rcvid, ENOSYS); continue; }
      int seen = 1; MsgReply(rcvid, EOK, &seen, sizeof seen);
    }
    usleep(80000);
  }
}
