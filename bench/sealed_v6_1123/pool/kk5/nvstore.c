/* nvstore <writer role> <flusher role>: record store for the parameter partition.
 * The main thread appends records; every 5th record it asks the flusher thread (same process) to push
 * the page out and waits for it, so a power cut never loses more than 5 records.
 * Two channels: ext_chid for clients of the store (name "<writer role>"), int_chid for the flush requests. */
#include "../common/qd.h"

static int ext_chid, int_chid;
static const char *r_fl;

static void *flusher(void *x) {
  FILE *f = NULL;
  pthread_setname_np(pthread_self(), r_fl);
  qd_msg_t m;
  for (int n = 0;;) {
    int rcvid = qd_receive(ext_chid, &m);
    if (rcvid <= 0) continue;
    /* write the page */
    MsgReply(rcvid, EOK, NULL, 0);
    if (!f) { char p[64]; snprintf(p, sizeof p, "/tmp/d0%s.log", r_fl); f = fopen(p, "a"); }
    if (f) { fprintf(f, "TICK %s %d\n", r_fl, n++); fflush(f); }
  }
  return x;
}

int main(int argc, char **argv) {
  if (argc < 3) return 2;
  const char *me = argv[1]; r_fl = argv[2];
  name_attach_t *a = qd_attach(me);
  ext_chid = a->chid;
  int_chid = ChannelCreate(0);
  if (int_chid == -1) { perror("ChannelCreate"); return 1; }
  int flush_coid = ConnectAttach(0, 0, int_chid, _NTO_SIDE_CHANNEL, 0);
  pthread_t t; pthread_create(&t, NULL, flusher, NULL);

  for (int n = 0;; n++) {
    usleep(100000);                               /* append one record */
    if (n % 5 == 4 && qd_send(flush_coid, n) < 0) perror("flush");
    qd_tick(me, n);
  }
}
