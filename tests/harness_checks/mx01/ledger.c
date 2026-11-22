#include "../common/qd.h"
static pthread_mutex_t book = PTHREAD_MUTEX_INITIALIZER, indx = PTHREAD_MUTEX_INITIALIZER;
struct job { const char *role; pthread_mutex_t *first, *second; };
static void *worker(void *arg) {   /* each thread writes its own role log */
  struct job *j = arg;
  char path[64];
  snprintf(path, sizeof path, "/tmp/%s.log", j->role);
  FILE *f = fopen(path, "w");
  if (!f) return NULL;
  for (int n = 0;; n++) {
    fprintf(f, "TICK %s %d\n", j->role, n); fflush(f);
    pthread_mutex_lock(j->first);
    usleep(50000);
    pthread_mutex_lock(j->second);
    pthread_mutex_unlock(j->second);
    pthread_mutex_unlock(j->first);
    usleep(20000);
  }
  return NULL;
}
int main(void) {   /* two threads take two mutexes in opposite order */
  static struct job jobs[2] = { { "d0post", &book, &indx },
                                { "d0audit", &indx, &book } };
  pthread_t t[2];
  for (int i = 0; i < 2; i++) pthread_create(&t[i], NULL, worker, &jobs[i]);
  for (;;) pthread_join(t[0], NULL);
}
