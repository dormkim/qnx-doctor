/* idle_srv <me>: most of the time we sit in receive -- looks dead, it isn't. */
#include "../common/qd.h"
int main(int argc,char**argv){
  const char*me=argv[1]; name_attach_t*a=qd_attach(me); qd_msg_t m;
  for(int n=0;;n++){
    int r=qd_receive(a->chid,&m);   /* QD-CULPRIT: parked here forever? (no -- a client knocks) */
    if(r>0) MsgReply(r,EOK,0,0);
    qd_tick(me,n);
  }
}
