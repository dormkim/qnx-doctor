/* reentr_s2 <me> <s1>: validate against s1 before answering. */
#include "../common/qd.h"
int main(int argc,char**argv){
  const char*me=argv[1],*s1=argv[2]; name_attach_t*a=qd_attach(me); int co=qd_open(s1); qd_msg_t m;
  for(int n=0;;n++){
    int r=qd_receive(a->chid,&m);
    if(r>0){ qd_send(co,n);        /* calls back into s1, which is waiting on us */
             MsgReply(r,EOK,0,0); }
    qd_tick(me,n);
  }
}
