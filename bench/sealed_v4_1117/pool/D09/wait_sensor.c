/* wait_sensor <me>: consume readings the field sensor publishes every 100ms. */
#include "../common/qd.h"
int main(int argc,char**argv){
  const char*me=argv[1]; name_attach_t*a=qd_attach(me); qd_tick(me,0); qd_msg_t m;
  for(int n=1;;n++){
    int r=qd_receive(a->chid,&m);   /* waits for the sensor (not in this capture) */
    if(r>0) MsgReply(r,EOK,0,0); qd_tick(me,n);
  }
}
