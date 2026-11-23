/* lru <me>: route cache with move-to-front on hit. One lookup batch per 100 ms. */
#include "../common/qd.h"

struct node { int key; struct node *next; };
static struct node pool[32], *head;
static volatile unsigned long probes, misses;   /* exported to the stats page */

static struct node *find(int key) {
  for (struct node *p = head; p; p = p->next) { probes++; if (p->key == key) return p; }
  return NULL;
}
static void touch(struct node *p) {               /* move to front */
  if (p == head) return;
  p->next = head;
  head = p;
}

int main(int argc, char **argv) {
  const char *me = argv[1];
  for (int i = 0; i < 8; i++) { pool[i].key = i * 10; pool[i].next = head; head = &pool[i]; }
  for (int n = 0;; n++) {
    struct node *p = find((n % 8) * 10);
    if (p && n >= 6) touch(p);                    /* warm cache: enable move-to-front */
    if (!find(-1)) misses++;                      /* negative lookup for the miss counter */
    qd_tick(me, n);
    usleep(100000);
  }
}
