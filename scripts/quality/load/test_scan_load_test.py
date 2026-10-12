import unittest

from scan_load_test import percentile, summarize


def sample(seconds, status=200, outcome="created"):
    return {"seconds": seconds, "status": status, "outcome": outcome}


class PercentileTests(unittest.TestCase):
    def test_nearest_rank(self):
        values = [float(n) for n in range(1, 101)]
        self.assertEqual(percentile(values, 50), 50.0)
        self.assertEqual(percentile(values, 95), 95.0)
        self.assertEqual(percentile(values, 99), 99.0)

    def test_single_value(self):
        self.assertEqual(percentile([0.3], 95), 0.3)

    def test_empty_raises(self):
        with self.assertRaises(ValueError):
            percentile([], 95)


class SummarizeTests(unittest.TestCase):
    def test_all_ok_within_limit(self):
        report = summarize([sample(0.1), sample(0.2), sample(0.3)], 1.0, 3)
        self.assertTrue(report["p95_within_limit"])
        self.assertEqual(report["lost_or_failed_events"], 0)
        self.assertEqual(report["throughput_per_second"], 3.0)

    def test_slow_p95_fails_limit(self):
        report = summarize([sample(0.1)] * 18 + [sample(2.5)] * 2, 5.0, 2)
        self.assertFalse(report["p95_within_limit"])

    def test_errors_are_counted_not_hidden(self):
        report = summarize([sample(0.1), sample(0.1, 500, ""), sample(0.0, 0, "URLError")], 1.0, 1)
        self.assertEqual(report["lost_or_failed_events"], 2)
        self.assertEqual(report["failures"], {"500:": 1, "0:URLError": 1})

    def test_duplicate_outcome_is_not_created(self):
        report = summarize([sample(0.1, 200, "duplicate")], 1.0, 1)
        self.assertEqual(report["lost_or_failed_events"], 1)

    def test_no_successes_never_passes(self):
        self.assertFalse(summarize([sample(0.1, 500, "")], 1.0, 1)["p95_within_limit"])


if __name__ == "__main__":
    unittest.main()
