# Why this matters on QNX

On QNX, almost everything is a server. Drivers, file systems, the network stack and your own services talk through
synchronous messages: a client calls `MsgSend()` and stays SEND- or REPLY-blocked until the server replies. That is
what makes the system modular and easy to restart piece by piece. It also means one bad wait (two processes sending
to each other, a server that never replies, a high-priority client stuck behind a low-priority server) can stop a
whole chain of processes. Nothing crashes. The system just stops making progress, and `pidin` shows a list of
blocked threads that someone has to read by hand.

QNX's own documentation warns about exactly this, and real systems have hit it. Every source below was opened and
the quoted words were checked against the page on 2026-11-16. Dates are the dates on the page.

## Real cases

| # | What happened | Platform | Source |
|---|---|---|---|
| 1 | **Mars Pathfinder, 1997.** The lander kept resetting itself on Mars. The flight software cognizant engineer wrote: "The failure turned out to be a case of priority inversion" and "The higher priority bc_dist task was blocked by the much lower priority ASI/MET task that was holding a shared resource." The fix was to turn on priority inheritance: "We did end up modifying the global variable to include the priority inheritance option. This corrected the problem." | VxWorks | Glenn E. Reeves (JPL), "What really happened on Mars? -- Authoritative Account", email of Dec 15, 1997. University mirror: <https://www.cs.unc.edu/~anderson/teach/comp790/papers/mars_pathfinder_long_version.html> |
| 2 | **The same incident, as first reported**: "the spacecraft began experiencing total system resets, each resulting in losses of data" … "This scenario is a classic case of priority inversion." | VxWorks | Mike Jones, "What really happened on Mars Rover Pathfinder", Dec 7, 1997. Course copy: <https://www.cs.cornell.edu/courses/cs614/1999sp/papers/pathfinder.html> |
| 3 | **Clients stuck on a QNX server for good.** A QNX 6.2.1 developer: "pidin -p shows that both threads are blocked by io-net process, and we can't kill or do anything to the process." Another user: "There was definitely a problem with tasks beeing NET-REPLY blocked, that couldn't be unblocked by anything", later "it was fixed in 6.3". (The fix is a forum claim; we did not check the release note.) | QNX 6.2.1 | OpenQNX forum, "Process blocked by io-net and not killable", July 2005: <https://forums.openqnx.com/t/topic/39295> |
| 4 | **Threads REPLY-blocked forever, cause in the application.** "all the threads that are REPLY-blocked on devc-pty remain blocked forever." A QNX engineer traced it to a race in the program's own terminal settings (not a QNX bug); the fix was a mutex in the application. This is the kind qnx-doctor targets: `pidin` shows who waits on whom, the cause is in your source. | QNX Neutrino | OpenQNX forum, "Help with deadlock problem", May 2003: <https://forums.openqnx.com/t/topic/20878> |
| 5 | **A deadlock fixed inside a QNX component.** Release notes, fs-qnx4.so: "A deadlock no longer occurs during one of our benchmark tests." (Ref# 49288, 49636). Even the vendor's own servers meet this class of bug. | QNX Momentics 6.4.0 | <https://www.qnx.com/developers/docs/6.4.0/momentics/release_notes/rel_6.4.0.html> |

## What QNX's documentation says to do

- "Never have two threads send to each other." "Always arrange your threads in a hierarchy, with sends going up the
  tree." System Architecture guide, "Robust implementations with Send/Receive/Reply":
  <https://www.qnx.com/developers/docs/7.1/com.qnx.doc.neutrino.sys_arch/topic/ipc_Robust.html>
- "The problem with having two threads send messages to each other is that eventually you'll run into the problem of
  deadlock." Getting Started with QNX (8.0), "The send-hierarchy":
  <https://qnx.com/developers/docs/8.0/com.qnx.doc.neutrino.getting_started/topic/s1_msg_sendhierarchy.html>
- Priority inversion: "a lower-priority thread has prevented a higher-priority thread from getting access to a
  resource." Getting Started with QNX (8.0):
  <https://qnx.com/developers/docs/8.0/com.qnx.doc.neutrino.getting_started/topic/s1_msg_prio_interitance.html>

The rules are clear. What is missing is a tool that checks a real, running system against them and proves a fix.
qnx-doctor does three things a rule in a manual cannot: it builds the wait graph from `pidin` in code, names the
cycle, chain or missing reply, and (in the test loop) accepts a fix only after a rerun shows the system moving again
with the same message structure.

## Who has this problem

- **Automotive teams.** QNX says its software "is now embedded in more than 275 million vehicles worldwide"
  (QNX press release, Dec 16, 2025:
  <https://www.newswire.com/news/qnx-embedded-technology-now-powering-more-than-275-million-vehicles-on-the-road>).
  A stuck chain of services in a vehicle is found late, on a test bench or in the field.
- **Medical device teams.** QNX describes its medical use as ranging "from small-footprint, real-time applications
  such as ventilators and infusion pumps to full-featured applications such as robotic surgery, imaging and
  monitoring systems" (QNX Medical Devices solution guide, PDF:
  <https://qnx.software/content/dam/qnx-xwalk/pdf/solution-guides/qnx-medical-devices-solution-guide.pdf>).
- **Robotics and industrial control teams moving a control loop onto QNX**: the same sensor → controller → actuator
  shape as our demo (`scenarios/hang_demo/control_loop`). If the controller and the actuator send to each other,
  the actuator stops getting commands and the sensor's readings queue up behind them.

qnx-doctor is a development and test tool. It runs on the host and reads `pidin`. It is not part of a shipped
system and makes no safety claim.

## Why a real-time OS makes this sharper

On a general-purpose OS, a stuck service is often hidden by timeouts and retries. On QNX, the design is that a
client waits for its server and a high-priority client really does go first. That is what you want for a control
loop, and it is also why a wrong wait does not fade away: the system keeps exactly the priorities and the waits you
gave it. Priority inheritance (the QNX default for message passing) removes one cause, and `_NTO_CHF_FIXED_PRIORITY`
turns it off. qnx-doctor's fixes are the QNX idioms for each cause: a pulse instead of a synchronous send back,
reply before notifying (`MsgDeliverEvent`), or letting the server inherit the client's priority.

## What we did not find

We looked for, but did not find, a public recall notice (FDA, NHTSA) or a NASA lessons-learned entry that names
priority inversion or a message-passing deadlock as the cause. We do not claim one.
