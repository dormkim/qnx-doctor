# 봉인 v3 실패 분석: 정상 오탐 q19, 놓친 교착 q10 (2026-11-17)

읽은 것: `runs/sealed3_20261117/`(score.md, excluded.json, labels.json, 네 팔의 jsonl·log),
`bench/sealed_v3_1117/`(README, SEAL.md, repro_20261117.json), 시나리오 소스 q10·q13·q16·q19,
`qnx_doctor/{hangdoctor,hang,waitgraph,structure}.py`, `tests/sealed_hang/common/{qd_trace.c,snap.c,check.sh}`.
v3는 **읽기만 했다**. v3 시나리오를 다시 돌리거나 다시 채점하지 않았다.

## 0. 이 문서의 규칙 (v4 전까지 유지)

1. v3 점수는 `runs/sealed3_20261117/score.md` 그대로 둔다. 아래 고침을 넣은 코드로 v3를 다시 돌리지 않고, «v3에서 좋아졌다»고 쓰지 않는다.
2. 아래 고침의 효과는 **새 봉인 세트 v4**에서만 잰다. v4는 코드도 v3 결과도 이 문서도 안 본 새 작성자가 쓰고, 정답 해시를 실행 전에 커밋하고, 한 번만 돌린다.
3. 하네스 고침(5절의 H1~H3)은 v4 봉인 **전에** 넣는다. 봉인 뒤에 하네스를 바꾸면 그 사실과 이유를 결과 문서에 적는다.
4. 고침을 시험할 때는 dev 풀과 `tests/harness_checks/`(하네스 자체 시험)만 쓴다.

## 1. 결과 다시 확인 (score.md에서 옮김)

21개 중 16개 사용. 5개 제외(라벨은 안 고침): q02·q06·q09·q21은 두 번째 관측기가 돌아오지 않아서, q16은 «계속 돌아야 할 루프가 0 TICK»이라서.

| 팔 | 종류 맞힘 | 교착 | 응답 없음 | 정상 | 모름(unknown) | 오탐 | 고침(재시도 포함) | unknown에 «고침» |
|---|---|---|---|---|---|---|---|---|
| code / ai(우리) | 13/16 | 4/5 | 3/3 | 3/4 | 3/4 | 1/4 | ai 3/8 | 0 |
| naive | 12/16 | 5/5 | 3/3 | 4/4 | 0/4 | 0/4 | 2/8 | 2 |
| naive_x2 | 11/16 | 4/5 | 3/3 | 4/4 | 0/4 | 0/4 | 3/8 | 3 |

- 고친 시나리오: ai = q08·q14·q15, naive_x2 = q08·q14·q15(같은 세 개), naive = q08·q15. 거짓 고침은 네 팔 모두 0.
- 우선순위 사슬 칸이 0/0인 이유: 제외된 4개(q02·q06·q09·q21)가 **사슬 라벨 전부**다. v3는 사슬에 대해 아무것도 말해 주지 않는다.
- 우리 «모름» 3/4는 도구가 `unknown`이라는 낱말을 내서가 아니다. 코드가 «루프는 멈췄는데 순환도 사슬도 못 찾음»(`loop not running but no wait cycle or chain found`)이라고 내고, 채점기가 그 문장을 unknown으로 읽는다(실행 전 커밋 caecd37의 규칙). 그리고 이 경우 AI를 아예 부르지 않는 구조라서 처방이 0이다. «AI가 판단해서 멈췄다»가 아니다.
- 우리가 틀린 축: misleading_comment·timeout_misuse(둘 다 q10), cpu_spin(q11).

## 2. 정상 오탐 = q19 (`ok_longpoll`)

라벨: dash가 evbus에 REPLY-blocked, evbus는 rcvid를 쥐고 RECEIVE-blocked(응답 없음과 똑같은 그림). 하지만 300 ms마다 오는 펄스가 응답을 풀어 줘서 dash는 계속 돈다. 정답 `none`.

우리 판정: `missing_reply`. 증거(code.jsonl q19):
- 스냅샷의 dash TICK = 13. 재현 확인 기록(`repro_20261117.json`)에는 13 → 잠시 뒤 27. 즉 루프는 돌고 있었다.
- 판정기(`waitgraph.judge`)는 스레드 상태만 본다. 세 장의 pidin(PIDIN, PIDIN2, PIDIN3)에서 같은 «dash → evbus, evbus 전 스레드 RECEIVE» 쌍이 보이면 응답 없음으로 친다(`_persists`). dash는 응답을 받자마자 다시 보내므로 세 장 모두 같은 그림이다.
- `hang.observe`의 `healthy`는 `judge == none and TICK 합 > 0`이다. 판정기가 무엇이든 이름을 붙이면 TICK이 13이어도 «멈춤»으로 적힌다(timeline의 `loop stopped`).

근본 원인: **진전(TICK이 늘었는가)을 보지 않고 상태만으로 판정한다.** 세 장 지속 규칙은 «지나가는 상태»를 거르려고 넣었지만(11/17), 늘 같은 상태로 보이는 정상(긴 폴링·지연 응답)은 못 거른다.

같은 뿌리의 다른 실패: **q11**(cpu_spin, 정답 unknown). uplink는 TICK 6개를 찍고 멈췄는데, 판정기가 순환·사슬·응답 없음을 못 찾았고 TICK 합이 6 > 0이라 «정상(no hang found)»으로 끝났다. 이것도 «TICK이 지금 늘고 있나»를 안 봐서 생긴 일이다. q19는 늘고 있는데 멈췄다고 했고, q11은 멈췄는데 정상이라고 했다.

## 3. 놓친 교착 = q10 (`sendtimeout`)

라벨: navcore가 routemap에 경로를 요청(송신 타임아웃만 걸림)하고 REPLY-blocked. routemap은 응답 전에 navcore에게 위치를 동기 질의하고, 300 ms 타임아웃으로 영원히 재시도. 정답 `deadlock`.

우리 판정: `none`(«루프 멈춤, 순환·사슬 없음»). 다른 세 팔도 실행 결과는 같았다(재실행 graph가 모두 `no wait cycle and no priority chain`). 기준선 둘은 **소스를 읽고** deadlock이라고 이름 붙였다.

근본 원인(유력, 아래 증거 3개): **우리 하네스의 `qd_trace.c`가 시나리오의 커널 타임아웃을 먹었다.**
- `TimerTimeout()`은 **바로 다음 커널 호출 하나**에만 타임아웃을 건다(QNX 문서). `qd_trace.c`의 감싸기 함수는 진짜 `MsgSend`/`MsgReceive` 전에 자기 커널 호출을 한다: `ConnectServerInfo`(상대 pid 찾기), 그리고 횟수가 작거나 2의 거듭제곱일 때 `/dev/shmem/qdm.<pid>`를 `open`/`write`.
- 그래서 navcore의 시작 단계 `serve_for`(TimerTimeout RECEIVE 1.5초 → MsgReceive)가 타임아웃 없이 영원히 받기만 하게 됐다. navcore는 경로 요청을 한 번도 보내지 않고, routemap은 받기에서 기다린다. 둘 다 RECEIVE: 순환도 TICK도 없다. 라벨이 그린 교착은 실제로 생기지 않았다.

증거:
1. code.jsonl q10의 메시지 구조: `pairs: {}`, `receivers: [navcore, routemap]`. `qd_trace`는 MsgSend를 **시도만 해도** 기록한다(att, 1회째에 바로 파일에 씀). 쌍이 비었다는 건 두 프로그램 모두 앱 메시지를 한 번도 보내려 하지 않았다는 뜻이다. 라벨대로라면 navcore→routemap 시도가 있어야 한다.
2. naive_x2의 첫 처방(q10)은 navcore 메인 스레드에서 `serve_for`를 빼고(시작 단계는 스레드로, 루프 안은 `usleep`으로) 바꿨는데, 재실행에서 navcore TICK 20이 나왔다(구조 변경으로 거절됨). 메인 스레드에서 타임아웃 받기만 빼면 돈다는 뜻이다.
3. 하네스 시험 `tests/harness_checks/tt01`(v3 아님, 이 분석을 위해 새로 씀): 아무도 안 보내는 채널에서 `TimerTimeout(RECEIVE 100 ms)` + `MsgReceive`를 반복하는 루프. main의 `qd_trace.c`로는 TICK 0(타임아웃이 안 걸림). 고친 `qd_trace.c`(브랜치 `fix/trace-timertimeout`)로는 TICK이 계속 나온다. 결과는 5절 표.

한계: 첫 스냅샷의 pidin 원문이 남아 있지 않다. `hang.observe`는 판정에 걸린 pid의 줄만 timeline에 남기는데, 판정이 none이면 0줄이다. 그래서 «둘 다 RECEIVE»를 원문으로 직접 보여 줄 수는 없고, 위 1~3으로 추정한다.

같은 버그가 닿은 다른 v3 시나리오(TimerTimeout을 쓰는 것은 q10·q13·q16 셋뿐, `grep`):
- **q16**(정상, 제외됨): 제외 사유가 «early timer»로 적혔지만, east·west가 0 TICK인 것은 같은 원인일 가능성이 크다(`serve_for`와 `TimerTimeout(SEND|REPLY)`를 씀).
- **q13**(교착+응답 없음, accept_kinds에 missing_reply): pumpctl의 `serve_for`가 같은 식으로 영원히 받기만 하면, pumpctl은 첫 TICK 뒤 순환 없이 멈춘다. 우리는 missing_reply(alarmd 쪽)로 맞혔지만, 고침은 «두 루프 다 재개»가 조건이라 **어느 팔도 고칠 수 없는 상태**였을 수 있다.
- 그래서 «고침 /8»의 분모 8개 중 q10·q13 둘은 하네스 때문에 소스와 다르게 돌았을 수 있다. 네 팔에 똑같이 걸리므로 «동률»은 바뀌지 않는다. 점수는 고치지 않는다.
- 앞선 세트(`tests/sealed_hang` D01~D07, `tests/gen_hang` v1·v2, `scenarios/`)는 TimerTimeout을 쓰지 않는다(`grep`). 이 버그로 v1·v2 숫자가 달라지지는 않는다.

## 4. 하네스 문제: 두 번째 관측기 (제외 4개)

q02·q06·q09·q21은 재현 확인 단계에서 «스냅샷 시점 TICK 15~37, 두 번째 수를 못 셈»으로 빠졌다. 두 번째 관측기(`bench/repro_v3.py`가 쓰는 snap, 시나리오 전에 띄우고 타이머로 깨움)가 `/tmp`(디스크) 로그를 읽다가 굶었다. 사슬 시나리오는 디스크 드라이버(devb-eide, 우선순위 21)보다 높은 CPU 부하를 걸기 때문에 디스크 읽기가 막힌다. 두 번 시도해도 같았다.

영향: 사슬 라벨 4개가 전부 빠져서 v3에는 사슬 결과가 없다. 그리고 실제 팔들도 첫 스냅샷의 TICK 수 하나만 본다(2절과 같은 뿌리).

## 5. 고칠 후보

| # | 무엇 | 고치는 실패 | 상태 |
|---|---|---|---|
| H1 | `qd_trace.c`: 스레드별로 마지막 `TimerTimeout`/`TimerTimeout_r`/`timer_timeout` 인자를 기억했다가, 감싸기 함수가 진짜 호출 직전에 다시 건다(`hang.py` TRACE_CALLS에 세 함수 추가). 남는 틈: 타임아웃을 건 뒤 감싸지 않은 다른 커널 호출을 먼저 하는 프로그램이면 QNX와 달리 타임아웃이 살아난다(지금 시나리오엔 없음) | q10, q13, q16(추정) | **main에 합침**(11/17), tt01로 확인(아래) |
| H2 | TICK 수를 RAM에 센다: `qd_tick`이 `/dev/shmem`에도 횟수를 쓰고, snap은 첫 스냅샷과 PIDIN3 뒤에 각각 센다. 재현 확인의 두 번째 관측기도 이 수를 읽는다(디스크를 안 거침) | 제외 4개(관측기), 2절의 진전 판정의 바탕 | **구현**(11/17), 방식은 바뀜: snap이 같은 부팅에서 TICK을 두 번 세고(`TICKS2`), 재현 확인은 두 번째 관측기 대신 이 두 수를 쓴다(`repro_v3.py --same-boot`). `/tmp`도 RAM 링크로(`check.sh`). oc01로 확인(8절) |
| H3 | 판정 원문을 늘 남긴다: `pidin_lines`를 판정에 걸린 pid만이 아니라 시나리오 프로세스 전부로(판정 none일 때도) | q10 같은 분석이 추정에 머무는 문제 | **구현**(11/17): 판정이 none이면 프로그램 전부의 줄 |
| J1 | 진전 판정: 같은 부팅에서 루프 TICK이 늘었으면 그 루프의 대기는 응답 없음·사슬로 치지 않고 «느림·정상». TICK이 0보다 크지만 안 늘었으면 «멈춤»으로 보고 판정기로 넘긴다(지금은 `>0`이면 정상) | q19 오탐, q11 놓침 | **구현**(11/17): `qnx_doctor/progress.py`, `waitgraph.judge(moving=)`. lp01·sp01로 확인(8절) |
| J2 | «모름»을 출력 낱말로: 지금은 채점기가 note 문장을 unknown으로 읽는다. 도구 출력에 `unknown`(«메시지 대기로 설명 안 됨, 정보 부족»)을 명시하고, 무엇이 더 필요한지(예: 프로세스 상태가 SIGWAITINFO·SEM·NANOSLEEP) 한 줄 덧붙인다 | 공개 글의 주장과 출력을 맞춤 | **구현**(11/17): `detected: unknown` + 이유(spinning / blocked_other / no_info), AI·고침 없음. 채점기는 옛 note와 새 낱말을 똑같이 unknown으로 읽는다 |
| J3 | q10 모양(교착 고리의 한쪽이 타임아웃 재시도로 계속 깨어남): H1 뒤에도 스냅샷이 순환을 놓치면 세 장 중 어느 한 장에서라도 «A REPLY→B, B SEND→A»가 보이면 교착 후보로 올리고 TICK 진전(J1)으로 확정 | q10 모양 | 미구현, H1 뒤 dev에서 먼저 확인 |

## 6. H1 확인 결과 (tests/harness_checks/tt01, v3 아님)

`bench/harness_check.py`로 한 번씩 부팅해 TICK만 셌다(QNX 시간 숫자는 적지 않는다).

| qd_trace.c | waiter (RECEIVE 타임아웃) | cli (SEND 타임아웃) |
|---|---|---|
| main (고치기 전) | TICK 0 | TICK 0 |
| `fix/trace-timertimeout` | TICK 계속 늘어남(29) | TICK 계속 늘어남(29) |

cli 쪽은 세 번째 판이다. 앞의 두 판은 시험 설계가 틀려서 고친 뒤에도 0이었다(waiter는 두 번 다 0 → 늘어남). 1판은 이름 붙인 서버에 SEND|REPLY 타임아웃을 걸었다: `name_attach` 채널은 `_NTO_CHF_UNBLOCK`이 켜져 있어서 REPLY-blocked 클라이언트는 서버가 응답해야 풀린다(QNX 동작으로 이해, 하네스 탓 아님). 2판은 서버가 connect만 받고 멈추게 했는데, 스냅샷에서 cli가 서버에 REPLY-blocked로 남았다(connect 판별이 안 맞은 것으로 보이나 확인 안 함). 3판은 `ChannelCreate(0)` 날 채널 + side-channel `ConnectAttach`에 SEND 타임아웃만 건다. 단위 시험 85개 통과(브랜치).

## 7. v4 전에 할 일

1. H1을 main에 합치고, H2·H3을 넣은 뒤 dev 풀과 tt01로만 확인한다.
2. J1·J2는 dev에서 «정상 대조군 오탐 0, 기존 dev 판정 유지»를 확인한 뒤 넣는다.
3. 새 작성자에게 v4를 맡긴다(코드·v3 결과·이 문서를 안 본 사람). 사슬 라벨이 하네스 때문에 통째로 빠지지 않도록, 봉인 전 재현 확인을 H2가 들어간 하네스로 한다.
4. v4 결과 문서에는 v3 점수를 그대로 옆에 두고, «v3 이후 바꾼 것» 목록(H1~J3 중 들어간 것)을 함께 적는다.

## 8. 고친 뒤 확인 (11/17, v3 아님: 새 하네스 시험과 단위 시험만)

v3를 다시 돌리거나 다시 채점하지 않았다. 아래는 모두 `tests/harness_checks/`(이 분석을 위해 새로 쓴 시나리오)와 단위 시험이다. 시나리오마다 한 번씩 부팅했다(QEMU 한 번에 하나).

| 시험 | 무엇을 보나 | 상태만 보면(`state_only`) | 고친 판정 |
|---|---|---|---|
| lp01 | 펄스가 올 때마다 응답하는 느린 서버(q19 모양, 코드는 새로 씀) | missing_reply | TICK 늘어남 → `none`(정상) |
| sp01 | 몇 번 돈 뒤 CPU에서 도는 루프(q11 모양) | none(예전엔 «정상») | `unknown (spinning)` |
| bo01 | 몇 번 돈 뒤 아무도 안 올리는 세마포어에서 대기 | none | `unknown (blocked_other)`, SEM 상태를 이름으로 |
| oc01 | 디스크 드라이버보다 높은 CPU 부하 아래의 우선순위 사슬 | priority_chain | `priority_chain` 유지 |
| oc01 `--twice` | 재현 확인의 두 번째 수 | v3 방식(두 번째 관측기): 수 없음 | 같은 부팅 방식(`--same-boot`): 수 있음 |
| tt01 | TimerTimeout 재무장(H1)이 합친 뒤에도 그대로인가 | none | `none`, 두 루프 다 늘어남 |

알게 된 것 하나(4절 정정): 두 번째 관측기가 «`/tmp` 디스크 읽기에서 굶었다»는 4절의 설명은 절반만 맞았다. `/tmp`를 RAM으로 옮긴 뒤에도 oc01에서 두 번째 관측기는 깨어나 TICK을 센 다음 `fork`한 자식(pidin)에서 멈췄다. 관측기 실행 파일을 부트 이미지(RAM)에 넣어도, `mlockall`을 걸어도 같았다. 원인은 확인하지 못했다(디스크 드라이버를 기다리는 무언가로 추정). 그래서 두 번째 관측기를 고치는 대신 쓰지 않는다: 첫 관측기가 같은 부팅에서 TICK을 두 번 세고(`TICKS2`), 재현 확인은 그 두 수를 읽는다. 첫 관측기는 모든 팔이 실제로 쓰는 경로라서, 재현 확인이 팔들이 보는 것과 같은 것을 재게 된다.

단위 시험 85개 → 105개, 모두 통과. 채점기는 옛 출력(`none` + «loop not running…»)과 새 출력(`unknown`)을 똑같이 unknown으로 읽는다(시험으로 확인, v3 파일로는 확인하지 않음). 독립 검토(새 에이전트, 코드만 읽음)에서 나온 것 중 두 개를 고쳤다: spinning 이유가 CPU 부하 프로그램을 먼저 지목할 수 있던 것, `--same-boot`와 `--retry-missing`을 같이 줄 때의 섞임. 남은 위험 두 개는 `bench/V4_PLAN.md`의 한계에 적었다(TICK 간격이 긴 정상 루프가 «unknown»이 될 수 있음, 같은 프로그램 두 개가 로그를 공유).

J3(q10 모양의 «한쪽이 타임아웃 재시도로 계속 깨어나는 교착»)은 넣지 않았다. H1 뒤에 순환이 스냅샷에 잡히는지는 v4에서 본다.

