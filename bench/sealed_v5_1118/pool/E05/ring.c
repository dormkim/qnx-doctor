/* ring <me> <next>: send a token to <next> first, only then serve own channel.
   Every node sends before any node receives -> a circular send/reply wait. */
#include "../common/qd.h"
int main(int argc,char**argv){
  const char*me=argv[1],*next=argv[2];
  name_attach_t*a=qd_attach(me); int coid=qd_open(next);
  qd_tick(me,0);
  for(int n=1;;n++){
    qd_send(coid,n);                 /* QD-CULPRIT: all send before receiving -> deadlock */
    qd_msg_t m; int r=qd_receive(a->chid,&m); if(r>0) MsgReply(r,EOK,0,0);
    qd_tick(me,n);
  }
}
