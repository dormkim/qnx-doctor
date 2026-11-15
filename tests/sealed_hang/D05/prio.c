/* prio server|client|hog: a high-priority control client uses a low-priority server.
 * The server's channel does not pass on the client's priority, so while CPU hogs of middle priority run,
 * the client waits on a server that never gets the CPU (priority inversion chain). */
#include "../common/qd.h"
#include <pthread.h>
#include <sched.h>
#include <time.h>
static void server(void) {
  setprio(0, 5);
  int chid = ChannelCreate(_NTO_CHF_FIXED_PRIORITY);   /* QD-CULPRIT: fixed priority — no priority inheritance from clients */
  FILE *f = fopen("/tmp/d05srv.id", "w"); fprintf(f, "%d %d\n", getpid(), chid); fclose(f);
  qd_msg_t m;
  for (;;) {
    int rcvid = qd_receive(chid, &m);
    if (rcvid <= 0) continue;
    volatile long x = 0; for (long i = 0; i < 2000000; i++) x += i;   /* a little real work */
    MsgReply(rcvid, EOK, &m.app.v, sizeof m.app.v);
  }
}
static void client(void) {
  setprio(0, 30);
  int pid = 0, chid = 0; FILE *f = NULL;
  for (int i = 0; i < 100 && !f; i++) { f = fopen("/tmp/d05srv.id", "r"); if (!f) usleep(50000); }
  if (!f || fscanf(f, "%d %d", &pid, &chid) != 2) { perror("server id"); exit(1); }
  fclose(f);
  int coid = ConnectAttach(0, pid, chid, _NTO_SIDE_CHANNEL, 0);
  for (int n = 0;; n++) { qd_send(coid, n); qd_tick("control", n); usleep(20000); }
}
static void *spin(void *arg) { time_t end = time(NULL) + (long)arg; volatile long x = 0; while (time(NULL) < end) x++; return NULL; }
static void hog(long secs) {
  setprio(0, 20);
  pthread_attr_t at; pthread_attr_init(&at); pthread_attr_setinheritsched(&at, PTHREAD_INHERIT_SCHED);
  pthread_t t[2]; for (int i = 0; i < 2; i++) pthread_create(&t[i], &at, spin, (void *)secs);
  for (int i = 0; i < 2; i++) pthread_join(t[i], NULL);
}
int main(int argc, char **argv) {
  if (!strcmp(argv[1], "server")) server();
  if (!strcmp(argv[1], "client")) client();
  if (!strcmp(argv[1], "hog")) hog(argc > 2 ? atol(argv[2]) : 20);
  return 2;
}
