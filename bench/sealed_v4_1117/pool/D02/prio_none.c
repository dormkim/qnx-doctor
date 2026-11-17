/* prio_none <low> <med> <high>: three workers share one lock. */
#include "../common/qd.h"
#include <sched.h>
static pthread_mutex_t mx; static const char*R[3];
static FILE* lg(const char*r){char p[64];snprintf(p,sizeof p,"/tmp/%s.log",r);return fopen(p,"w");}
static void tk(FILE*f,const char*r,int n){fprintf(f,"TICK %s %d\n",r,n);fflush(f);}
static void*low(void*_){FILE*f=lg(R[0]);tk(f,R[0],0);
  pthread_mutex_lock(&mx);tk(f,R[0],1);
  volatile long x=0; for(long i=0;i<8000000000L;i++) x+=i;   /* long CPU while holding the lock */
  pthread_mutex_unlock(&mx); for(;;) usleep(100000); return 0;}
static void*med(void*_){FILE*f=lg(R[1]);tk(f,R[1],0); volatile long x=0; for(;;) x++; return 0;}
static void*hi(void*_){FILE*f=lg(R[2]);tk(f,R[2],0);
  pthread_mutex_lock(&mx);tk(f,R[2],1);pthread_mutex_unlock(&mx);
  for(int n=2;;n++){tk(f,R[2],n);usleep(100000);} return 0;}
static pthread_t sp(void*(*fn)(void*),int prio){
  pthread_attr_t at;pthread_attr_init(&at);
  pthread_attr_setinheritsched(&at,PTHREAD_EXPLICIT_SCHED);
  pthread_attr_setschedpolicy(&at,SCHED_FIFO);
  struct sched_param s;s.sched_priority=prio;pthread_attr_setschedparam(&at,&s);
  pthread_t t;pthread_create(&t,&at,fn,0);pthread_attr_destroy(&at);return t;}
int main(int argc,char**argv){
  R[0]=argv[1];R[1]=argv[2];R[2]=argv[3];
  pthread_setschedprio(pthread_self(),40);
  pthread_mutexattr_t ma;pthread_mutexattr_init(&ma);
  pthread_mutexattr_setprotocol(&ma,PTHREAD_PRIO_NONE);   /* no inheritance */
  pthread_mutex_init(&mx,&ma);
  sp(low,10); usleep(200000); sp(med,20); usleep(50000);
  pthread_t h=sp(hi,30); pthread_join(h,0); return 0;
}
