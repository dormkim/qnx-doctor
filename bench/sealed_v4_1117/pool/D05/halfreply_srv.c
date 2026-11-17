/* halfreply_srv <me>: ack errors; good requests are handled below. */
#include "../common/qd.h"
int main(int argc,char**argv){
  const char*me=argv[1]; name_attach_t*a=qd_attach(me); qd_msg_t m;
  for(int n=0;;n++){
    int r=qd_receive(a->chid,&m);
    if(r>0 && m.app.v<0) MsgReply(r,EOK,0,0);   /* only the error path replies */
    /* good path: no reply (bug) */
    qd_tick(me,n);
  }
}
