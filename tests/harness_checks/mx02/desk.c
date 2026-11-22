#include "../common/qd.h"
static pthread_mutex_t queue = PTHREAD_MUTEX_INITIALIZER, state = PTHREAD_MUTEX_INITIALIZER;
static volatile int pending;
static void *post(void *unused) {
  (void)unused;
  for (;;) {
    pthread_mutex_lock(&queue);
    usleep(50000);
    pthread_mutex_lock(&state);
    if (pending) { MsgReply(pending, EOK, NULL, 0); pending = 0; }
    pthread_mutex_unlock(&state);
    pthread_mutex_unlock(&queue);
    usleep(20000);
  }
  return NULL;
}
static void *audit(void *unused) {
  (void)unused;
  for (;;) {
    pthread_mutex_lock(&state);
    usleep(50000);
    pthread_mutex_lock(&queue);
    pthread_mutex_unlock(&queue);
    pthread_mutex_unlock(&state);
    usleep(20000);
  }
  return NULL;
}
static void *flusher(void *unused) {
  (void)unused;
  for (;;) {
    usleep(30000);
    pthread_mutex_lock(&queue);
    pthread_mutex_unlock(&queue);
  }
  return NULL;
}
int main(void) {   /* a server: one thread receives, its workers (one of them replies) deadlock on two mutexes */
  name_attach_t *a = qd_attach("mxdesk");
  pthread_t t[3];
  pthread_create(&t[0], NULL, post, NULL);
  pthread_create(&t[1], NULL, audit, NULL);
  pthread_create(&t[2], NULL, flusher, NULL);
  qd_msg_t m;
  for (;;) {
    int r = qd_receive(a->chid, &m);
    if (r > 0) pending = r;
  }
}
