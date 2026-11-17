/* pool_disp <me> <w1> <w2>: hand a job to each worker every 300ms. */
#include "../common/qd.h"
int main(int argc,char**argv){
  const char*me=argv[1],*w1=argv[2],*w2=argv[3];
  int c1=qd_open(w1), c2=qd_open(w2);
  for(int n=0;;n++){ qd_send(c1,n); qd_send(c2,n); qd_tick(me,n); usleep(300000); }
}
