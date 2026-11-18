/* stopsrv <me>: replies while it has reply credits; a bookkeeping bug stops replies after the first few. */
#include "../common/qd.h"
int main(int argc,char**argv){
  const char*me=argv[1]; name_attach_t*a=qd_attach(me); qd_msg_t m;
  for(int n=0;;n++){
    int r=qd_receive(a->chid,&m);
    if(r>0 && n<3) MsgReply(r,EOK,0,0);   /* QD-CULPRIT: after 3, the message is taken but never replied */
    qd_tick(me,n);
  }
}
