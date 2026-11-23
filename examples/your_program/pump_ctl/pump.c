/* pump <name>: pump driver. A controller sets the speed with a synchronous message. After every third change the
 * pump reports the speed it reached back to that controller, on the channel id the request carried.
 * Plain QNX 8.0 calls only; nothing here knows about qnx-doctor. */
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <sys/dispatch.h>
#include <sys/iomsg.h>
#include <sys/neutrino.h>

#define SET_SPEED 0x7001
#define REPORT    0x7002
typedef struct { uint16_t type; int32_t chid; int32_t value; } pump_msg_t;

int main(int argc, char **argv) {
  if (argc < 2) return 2;
  name_attach_t *att = name_attach(NULL, argv[1], 0);
  if (!att) { perror("name_attach"); return 1; }
  union { struct _pulse pulse; uint16_t type; pump_msg_t m; char raw[64]; } in;
  for (int n = 0;;) {
    struct _msg_info info;
    rcvid_t rcvid = MsgReceive(att->chid, &in, sizeof in, &info);
    if (rcvid == -1) continue;
    if (rcvid == 0) { if (in.pulse.code == _PULSE_CODE_DISCONNECT) ConnectDetach(in.pulse.scoid); continue; }
    if (in.type == _IO_CONNECT) { MsgReply(rcvid, EOK, NULL, 0); continue; }
    if (in.type != SET_SPEED) { MsgError(rcvid, ENOSYS); continue; }
    int speed = in.m.value;
    if (n % 3 == 2) {                              /* report the speed we reached */
      int coid = ConnectAttach(0, info.pid, in.m.chid, _NTO_SIDE_CHANNEL, 0);
      if (coid != -1) {
        pump_msg_t rep = { REPORT, 0, speed }; int seen = 0;
        if (MsgSend(coid, &rep, sizeof rep, &seen, sizeof seen) == -1) perror("report");
        ConnectDetach(coid);
      }
    }
    MsgReply(rcvid, EOK, &speed, sizeof speed);
    printf("TICK %s %d\n", argv[1], n++); fflush(stdout);
  }
}
