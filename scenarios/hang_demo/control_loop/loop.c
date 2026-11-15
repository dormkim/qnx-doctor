/* Demo (outside the sealed set): a 3-process control loop.
 *   sensor   — reads a value every 50 ms and sends it to control (waits for the reply)
 *   control  — computes a command and sends it to the actuator before replying to the sensor
 *   actuator — applies the command; when it applies one, it reports its new position back to control
 * The report back is a synchronous MsgSend while control is still waiting for the actuator's reply. */
#include "../common/qd.h"

static void sensor(void) {
  qd_attach("sensor");
  int ctl = qd_open("control");
  for (int n = 0;; n++) { int cmd = qd_send(ctl, n * 3 % 100); (void)cmd; qd_tick("sensor", n); usleep(50000); }
}

static void control(void) {
  name_attach_t *a = qd_attach("control");
  int act = qd_open("actuator");
  qd_msg_t m; int position = 0;
  for (;;) {
    int rcvid = qd_receive(a->chid, &m);
    if (rcvid == 0) { position = m.pulse.value.sival_int; continue; }
    if (m.app.v == -1) { MsgReply(rcvid, EOK, NULL, 0); continue; }   /* position report */
    int cmd = (m.app.v - position) / 2;
    qd_send(act, cmd);
    MsgReply(rcvid, EOK, &cmd, sizeof cmd);
  }
}

static void actuator(void) {
  name_attach_t *a = qd_attach("actuator");
  int ctl = qd_open("control");
  qd_msg_t m; int position = 0;
  for (;;) {
    int rcvid = qd_receive(a->chid, &m);
    if (rcvid <= 0) continue;
    position += m.app.v;
    qd_send(ctl, -1);          /* report position: blocks until control replies */
    MsgReply(rcvid, EOK, &position, sizeof position);
  }
}

int main(int argc, char **argv) {
  if (argc < 2) return 2;
  if (!strcmp(argv[1], "sensor")) sensor();
  if (!strcmp(argv[1], "control")) control();
  if (!strcmp(argv[1], "actuator")) actuator();
  return 2;
}
