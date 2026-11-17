/* noreply_srv <me>: accept work, enqueue it, reply when the batch flushes. */
#include "../common/qd.h"
int main(int argc,char**argv){
  const char*me=argv[1]; name_attach_t*a=qd_attach(me); qd_msg_t m;
  for(int n=0;;n++){
    int r=qd_receive(a->chid,&m); (void)r;   /* rcvid kept for a flush that never comes */
    qd_tick(me,n);
  }
}
