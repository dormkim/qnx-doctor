#include "../common/qd.h"
#include <time.h>
#include <signal.h>

/* sampler: sends each sample to fltr and waits for the filtered value; a second thread takes fltr's
 * early-ack pulses. Prints a watchdog line when a reply seems late. */
static volatile int acks;
static void *ack_thread(void *arg) {
  name_attach_t *a = arg; qd_msg_t m;
  for (;;) if (qd_receive(a->chid, &m) == 0) acks++;
  return NULL;
}
int main(void) {
  name_attach_t *a = qd_attach("sampler");
  pthread_t t; pthread_create(&t, NULL, ack_thread, a);
  int f = qd_open("fltr");
  for (int n = 0;; n++) {
    qd_send(f, n);
    qd_tick("sampler", n);
    if (n % 15 == 14) { printf("sampler: ERROR deadlock suspected with fltr (acks %d behind), retrying\n", n + 1 - acks); fflush(stdout); }
    usleep(20000);
  }
}
