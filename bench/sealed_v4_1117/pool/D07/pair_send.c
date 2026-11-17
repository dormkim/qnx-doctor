/* pair_send <me> <peer>: exchange with the peer; send first, then serve. */
#include "../common/qd.h"
int main(int argc,char**argv){
  const char*me=argv[1],*peer=argv[2];
  name_attach_t*a=qd_attach(me); int coid=qd_open(peer);
  for(int n=0;;n++){
    qd_send(coid,n);                 /* both peers send before receiving -> mutual block */
    qd_msg_t m; int r=qd_receive(a->chid,&m); if(r>0) MsgReply(r,EOK,0,0);
    qd_tick(me,n);
  }
}
