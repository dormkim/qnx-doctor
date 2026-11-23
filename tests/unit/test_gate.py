"""qnx_doctor.gate: fixes the rerun cannot vouch for (v7 plan section 2). The v6 cases are development cases."""
import unittest

from qnx_doctor import gate


class UsedSync(unittest.TestCase):
    def test_value_kept_is_used(self):
        self.assertEqual(len(gate.used_sync("val = qd_send(o, k); return qd_send(z, 1); f(1, qd_send(w, 2));")), 3)

    def test_error_check_only_is_not_used(self):
        self.assertEqual(gate.used_sync("if (qd_send(c, 1) < 0) perror(\"x\"); if (n && qd_send(b, -1) < 0) p(); qd_send(a, 2);"), [])

    def test_compare_with_a_value_is_used(self):
        self.assertEqual(len(gate.used_sync("if (qd_send(q, 3) == 7) x();")), 1)

    def test_msgsend_with_reply_buffer_is_used(self):
        self.assertEqual(len(gate.used_sync("if (MsgSend(c, &m, 4, &r, 4) == -1) e();")), 1)
        self.assertEqual(gate.used_sync("if (MsgSend(c, &m, 4, NULL, 0) == -1) e();"), [])

    def test_comments_are_ignored(self):
        self.assertEqual(gate.used_sync("/* val = qd_send(o, k); */ // x = qd_send(a, 1);"), [])


class Review(unittest.TestCase):
    SRV = "for (;;) { int rcvid = qd_receive(chid, &m); if (rcvid == 0) continue; MsgReply(rcvid, EOK, &one, 4); }"

    def test_v6_bkr_invented_answer_goes_to_review(self):
        before = {"p/dbd.c": "else val = qd_send(owner, key);"}
        after = {"p/dbd.c": "else { val = MsgSendPulse(owner, -1, _PULSE_CODE_MINAVAIL, key) == -1 ? -1 : 1; }"}
        self.assertTrue(gate.review(before, after))

    def test_request_as_pulse_to_a_receiver_that_drops_pulses(self):
        before = {"p/ui.c": "if (qd_send(cat, HEADER) < 0) perror(\"h\");", "p/cat.c": self.SRV}
        after = {"p/ui.c": "if (MsgSendPulse(cat, -1, 1, HEADER) == -1) perror(\"h\");", "p/cat.c": self.SRV}
        self.assertTrue(gate.review(before, after))

    def test_pulse_with_the_receiver_taught_to_handle_it_passes(self):
        before = {"p/k.c": "if (qd_send(brk, -1) < 0) perror(\"r\");", "p/b.c": self.SRV}
        after = {"p/k.c": "if (MsgSendPulse(brk, -1, 1, -1) == -1) perror(\"r\");",
                 "p/b.c": self.SRV.replace("if (rcvid == 0) continue;", "if (rcvid == 0) { routes++; continue; }")}
        self.assertEqual(gate.review(before, after), [])

    def test_unused_send_to_pulse_passes(self):
        before = {"p/c.c": "if (qd_send(out, batch) < 0) perror(\"f\");"}
        after = {"p/c.c": "if (MsgSendPulse(out, -1, 1, batch) == -1) perror(\"f\");"}
        self.assertEqual(gate.review(before, after), [])

    def test_reordering_without_dropping_passes(self):
        before = {"p/s.c": "v = qd_send(a, 1); MsgReply(r, EOK, &v, 4);"}
        after = {"p/s.c": "MsgReply(r, EOK, &last, 4); v = qd_send(a, 1); last = v;"}
        self.assertEqual(gate.review(before, after), [])


if __name__ == "__main__":
    unittest.main()
