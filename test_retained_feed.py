import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from export_feed import export, retained_settled_fixtures


class RetainedFeedTest(unittest.TestCase):
    def test_only_recent_settled_results_survive_refresh(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "fixtures.json"
            previous = {
                "schema_version": 1,
                "fixtures": [
                    {"id": 1, "kickoff_utc": "2026-11-15T12:00:00Z", "winner_1x2": "HOME"},
                    {"id": 2, "kickoff_utc": "2026-11-15T13:00:00Z", "winner_1x2": None},
                    {"id": 3, "kickoff_utc": "2026-10-01T12:00:00Z", "winner_1x2": "AWAY"},
                ],
            }
            output.write_text(json.dumps(previous), encoding="utf-8")

            self.assertEqual([fixture["id"] for fixture in retained_settled_fixtures(output, date(2026, 11, 26))], [1])
            fresh = {"id": 4, "kickoff_utc": "2026-11-26T12:00:00Z", "winner_1x2": None}
            with patch("export_feed.fetch_day", return_value=[fresh]):
                export(date(2026, 11, 26), date(2026, 11, 26), output, "test-value")

            current = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual([fixture["id"] for fixture in current["fixtures"]], [1, 4])
            self.assertEqual(current["fixture_count"], 2)
            self.assertEqual(current["settled_archive_from"], "2026-11-03")

    def test_invalid_existing_feed_is_not_replaced(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "fixtures.json"
            output.write_text('{"schema_version":1,"fixtures":"broken"}', encoding="utf-8")
            with patch("export_feed.fetch_day") as fetch:
                with self.assertRaises(RuntimeError):
                    export(date(2026, 11, 26), date(2026, 11, 26), output, "test-value")
                fetch.assert_not_called()


if __name__ == "__main__":
    unittest.main()
