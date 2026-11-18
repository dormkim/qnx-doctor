/* sem <me>: process a few items, then wait on a semaphore whose count starts at 0 and is never posted. */
#include "../common/qd.h"
#include <semaphore.h>
int main(int argc,char**argv){
  const char*me=argv[1]; sem_t s; sem_init(&s,0,0);
  for(int n=0;n<3;n++){ qd_tick(me,n); usleep(200000); }
  sem_wait(&s);   /* QD-CULPRIT: count is 0 and nobody posts -> blocks forever (no message edge) */
  qd_tick(me,99); return 0;
}
