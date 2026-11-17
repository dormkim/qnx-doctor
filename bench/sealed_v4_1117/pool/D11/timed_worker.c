/* timed_worker <me>: wake every 300ms on a receive timeout and do a slice. */
#include "../common/qd.h"
int main(int argc,char**argv){
  const char*me=argv[1]; int chid=ChannelCreate(0);
  for(int n=0;;n++){
    uint64_t to=300000000ULL;
    TimerTimeout(CLOCK_MONOTONIC,_NTO_TIMEOUT_RECEIVE,NULL,&to,NULL);
    qd_msg_t m; MsgReceive(chid,&m,sizeof m,NULL);   /* times out -> returns */
    qd_tick(me,n);
  }
}
