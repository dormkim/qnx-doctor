/* selfsend <me>: forward the first job to our own worker channel. */
#include "../common/qd.h"
int main(int argc,char**argv){
  const char*me=argv[1]; int chid=ChannelCreate(0);
  int coid=ConnectAttach(0,0,chid,_NTO_SIDE_CHANNEL,0);
  qd_tick(me,0);
  qd_msg_t m; m.app.type=QD_MSG; m.app.v=1; int r=0;
  MsgSend(coid,&m.app,sizeof m.app,&r,sizeof r);  /* QD-CULPRIT: the only thread sends to its own channel */
  qd_tick(me,1); return 0;
}
