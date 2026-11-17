/* ring <me> <next> <arm:0|1>: pass a token around a 3-node ring; send first, then serve. */
#include "../common/qd.h"
int main(int argc,char**argv){
  const char*me=argv[1],*next=argv[2]; int arm=atoi(argv[3]);
  name_attach_t*a=qd_attach(me); int coid=qd_open(next);
  qd_tick(me,0);
  if(arm){ uint64_t to=2000000000ULL; TimerTimeout(CLOCK_MONOTONIC,_NTO_TIMEOUT_RECEIVE,NULL,&to,NULL); } /* guards the wrong state */
  for(int n=1;;n++){
    qd_send(coid,n);                 /* all three send before any receive -> circular */
    qd_msg_t m; int r=qd_receive(a->chid,&m); if(r>0) MsgReply(r,EOK,0,0);
    qd_tick(me,n);
  }
}
