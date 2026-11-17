/* pulse_srv <me>: a timer pulse drives one tick every 400ms. */
#include "../common/qd.h"
#include <time.h>
#include <signal.h>
#define PCODE (_PULSE_CODE_MINAVAIL+1)
int main(int argc,char**argv){
  const char*me=argv[1]; int chid=ChannelCreate(0);
  int coid=ConnectAttach(0,0,chid,_NTO_SIDE_CHANNEL,0);
  struct sigevent ev; SIGEV_PULSE_INIT(&ev,coid,SIGEV_PULSE_PRIO_INHERIT,PCODE,0);
  timer_t t; timer_create(CLOCK_MONOTONIC,&ev,&t);
  struct itimerspec it; it.it_value.tv_sec=0; it.it_value.tv_nsec=400000000;
  it.it_interval=it.it_value; timer_settime(t,0,&it,NULL);
  qd_msg_t m;
  for(int n=0;;n++){ MsgReceive(chid,&m,sizeof m,NULL); qd_tick(me,n); }
}
