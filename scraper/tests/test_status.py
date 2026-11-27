"""Tests for the status.json merge rules.

    .venv/bin/python3 -m unittest discover -s scraper/tests -t .
"""
import unittest

from ..status import merge_status

T1 = "2026-11-27T11:02:00+05:30"
T2 = "2026-11-27T16:03:00+05:30"
T3 = "2026-11-28T11:01:00+05:30"


class MergeStatusTest(unittest.TestCase):
    def test_ok_check_records_rate_date_and_last_ok(self):
        status = merge_status({}, {"SBI": {"result": "ok", "rateDate": "2026-11-27", "checkedAt": T1}})
        self.assertEqual(status["checkedAt"], T1)
        self.assertEqual(status["banks"]["SBI"], {"checkedAt": T1, "result": "ok", "rateDate": "2026-11-27", "lastOkAt": T1})

    def test_error_keeps_last_ok_and_starts_failing_since(self):
        prev = merge_status({}, {"SBI": {"result": "waiting", "rateDate": "2026-11-26", "checkedAt": T1}})
        status = merge_status(prev, {"SBI": {"result": "error", "error": "timeout", "checkedAt": T2}})
        self.assertEqual(status["banks"]["SBI"], {
            "checkedAt": T2, "result": "error", "error": "timeout", "failingSince": T2, "lastOkAt": T1,
        })

    def test_repeated_error_keeps_first_failing_since(self):
        prev = merge_status({}, {"SBI": {"result": "error", "error": "a", "checkedAt": T1}})
        prev = merge_status(prev, {"SBI": {"result": "error", "error": "b", "checkedAt": T2}})
        status = merge_status(prev, {"SBI": {"result": "error", "error": "c", "checkedAt": T3}})
        bank = status["banks"]["SBI"]
        self.assertEqual(bank["failingSince"], T1)
        self.assertEqual(bank["error"], "c")
        self.assertNotIn("lastOkAt", bank)

    def test_recovery_clears_failing_since(self):
        prev = merge_status({}, {"SBI": {"result": "error", "error": "a", "checkedAt": T1}})
        status = merge_status(prev, {"SBI": {"result": "ok", "rateDate": "2026-11-27", "checkedAt": T2}})
        self.assertNotIn("failingSince", status["banks"]["SBI"])
        self.assertEqual(status["banks"]["SBI"]["lastOkAt"], T2)

    def test_unchecked_bank_keeps_previous_entry(self):
        prev = merge_status({}, {"CUB": {"result": "error", "error": "timeout", "checkedAt": T1}})
        status = merge_status(prev, {"SBI": {"result": "ok", "rateDate": "2026-11-27", "checkedAt": T2}})
        self.assertEqual(status["banks"]["CUB"], prev["banks"]["CUB"])
        self.assertEqual(status["checkedAt"], T2)

    def test_long_error_is_truncated(self):
        status = merge_status({}, {"SBI": {"result": "error", "error": "x" * 500, "checkedAt": T1}})
        self.assertEqual(len(status["banks"]["SBI"]["error"]), 200)


if __name__ == "__main__":
    unittest.main()
