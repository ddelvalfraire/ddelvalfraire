import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import check


class Checks(unittest.TestCase):
    def test_real_success_and_failure(self):
        for code in (0, 7):
            result = check.run([sys.executable, "-c", f"print('evidence'); exit({code})"], ".")
            self.assertEqual(result["exit"], code)
            self.assertIn("evidence", result["output"])
            self.assertIn("+00:00", result["time"])

    def test_missing_tool_and_timeout(self):
        self.assertEqual(check.run(["/no-such-profile-tool"], ".")["exit"], 127)
        self.assertEqual(check.run([sys.executable, "-c", "import time; time.sleep(5)"],
                                   ".", timeout=.05)["exit"], 124)

    def test_failure_replaces_green_and_escapes_output(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(check, "ROOT", Path(directory)):
            (check.ROOT / "README.template.md").write_text("<!-- RESULTS -->")
            result = {"psi": dict(revision="a" * 40, steps=[dict(
                command="test", time="now", seconds=1, exit=0, output="ok")])}
            check.publish(result)
            self.assertIn("PASS", (check.ROOT / "README.md").read_text())
            result["psi"]["steps"][0].update(exit=1, output="</pre><script>&```\n")
            check.publish(result)
            readme = (check.ROOT / "README.md").read_text()
            self.assertIn("FAIL", readme)
            self.assertNotIn("PASS", readme)
            self.assertIn("&lt;script&gt;", readme)
            self.assertEqual(json.loads((check.ROOT / "results/latest.json").read_text()), result)

    def test_setup_failure_stops_project(self):
        with patch.object(check, "run", return_value=dict(
                command="git fetch", time="now", seconds=0, exit=1, output="offline")) as run:
            result = check.check("Quanta", Path("."))
            self.assertEqual(run.call_count, 1)
            self.assertIn("FAIL", check.render({"Quanta": result}))


if __name__ == "__main__":
    unittest.main()
