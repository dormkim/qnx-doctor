/* spin_flag <me>: process a few items, then wait for the queue to drain. */
#include "../common/qd.h"
static volatile int drained=0;   /* cleared by the drain path */
int main(int argc,char**argv){
  const char*me=argv[1];
  for(int n=0;n<3;n++){ qd_tick(me,n); usleep(200000); }
  while(!drained){ /* busy-wait for the queue to drain */ }   /* QD-CULPRIT: nothing ever sets it */
  qd_tick(me,99); return 0;
}
