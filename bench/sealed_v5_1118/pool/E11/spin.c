/* spin <me>: process a few items, then busy-wait for a flag that is never set (not a message hang). */
#include "../common/qd.h"
static volatile int done=0;
int main(int argc,char**argv){
  const char*me=argv[1];
  for(int n=0;n<3;n++){ qd_tick(me,n); usleep(200000); }
  while(!done){ }   /* QD-CULPRIT: nothing ever sets done */
  qd_tick(me,99); return 0;
}
