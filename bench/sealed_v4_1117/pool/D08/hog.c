/* hog <me>: a mid-priority compute job. */
#include "../common/qd.h"
int main(int argc,char**argv){
  const char*me=argv[1]; pthread_setschedprio(pthread_self(),20);
  qd_tick(me,0); volatile long x=0; for(;;) x++;
}
