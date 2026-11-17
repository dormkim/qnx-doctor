/* lostwake <producer> <consumer>: hand one unit across a condvar. */
#include "../common/qd.h"
static pthread_mutex_t mx; static pthread_cond_t cv; static const char*R[2];
static FILE* lg(const char*r){char p[64];snprintf(p,sizeof p,"/tmp/%s.log",r);return fopen(p,"w");}
static void tk(FILE*f,const char*r,int n){fprintf(f,"TICK %s %d\n",r,n);fflush(f);}
static void*prod(void*_){FILE*f=lg(R[0]);tk(f,R[0],0);
  pthread_mutex_lock(&mx);pthread_cond_signal(&cv);pthread_mutex_unlock(&mx);  /* signals before the wait */
  for(int n=1;;n++){tk(f,R[0],n);usleep(200000);} return 0;}
static void*cons(void*_){FILE*f=lg(R[1]);tk(f,R[1],0);
  usleep(200000);                         /* arrives after the signal is gone */
  pthread_mutex_lock(&mx);
  pthread_cond_wait(&cv,&mx);             /* QD-CULPRIT: no predicate -> missed wakeup = waits forever */
  pthread_mutex_unlock(&mx);tk(f,R[1],1); return 0;}
int main(int argc,char**argv){
  R[0]=argv[1];R[1]=argv[2]; pthread_mutex_init(&mx,0);pthread_cond_init(&cv,0);
  pthread_t p,c; pthread_create(&p,0,prod,0);pthread_create(&c,0,cons,0);
  pthread_join(c,0); return 0;
}
