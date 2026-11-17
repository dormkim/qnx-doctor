/* twomsg_srv <me>: each transaction is a header then a body; reply after both. */
#include "../common/qd.h"
int main(int argc,char**argv){
  const char*me=argv[1]; name_attach_t*a=qd_attach(me); qd_msg_t m;
  for(int n=0;;n++){
    int r1=qd_receive(a->chid,&m);   /* header */
    int r2=qd_receive(a->chid,&m);   /* body (QD-CULPRIT: the client only ever sends one) */
    if(r1>0) MsgReply(r1,EOK,0,0);
    if(r2>0) MsgReply(r2,EOK,0,0);
    qd_tick(me,n);
  }
}
