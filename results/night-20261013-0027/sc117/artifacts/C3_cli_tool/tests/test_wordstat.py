import io
import json
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import wordstat


class ComputeStatsTest(unittest.TestCase):
    def test_basic_counts(self):
        text = "Hello world\nhello World foo\n"
        stats = wordstat.compute_stats(text)
        self.assertEqual(stats["lines"], 2)
        self.assertEqual(stats["words"], 5)
        self.assertEqual(stats["chars"], len(text))
        self.assertEqual(
            stats["top"],
            [["hello", 2], ["world", 2], ["foo", 1]],
        )

    def test_top_max_five_and_tie_break(self):
        # a/b/c が 3 回、d/e/f が 2 回。同回数なら辞書順、最大 5 個。
        text = "a a a b b b c c c d d e e f f g"
        stats = wordstat.compute_stats(text)
        self.assertEqual(len(stats["top"]), 5)
        self.assertEqual(
            stats["top"],
            [["a", 3], ["b", 3], ["c", 3], ["d", 2], ["e", 2]],
        )

    def test_empty_file(self):
        stats = wordstat.compute_stats("")
        self.assertEqual(stats, {"lines": 0, "words": 0, "chars": 0, "top": []})

    def test_case_insensitive_count(self):
        text = "Foo FOO fOo foO"
        stats = wordstat.compute_stats(text)
        self.assertEqual(stats["top"], [["foo", 4]])


class MainCliTest(unittest.TestCase):
    def test_main_prints_json_line(self):
        with tempfile.NamedTemporaryFile(
            "w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            f.write("apple banana\napple\n")
            path = f.name
        try:
            result = subprocess.run(
                [sys.executable, "wordstat.py", path],
                capture_output=True,
                text=True,
                cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            )
            self.assertEqual(result.returncode, 0)
            data = json.loads(result.stdout.strip())
            self.assertEqual(data["lines"], 2)
            self.assertEqual(data["words"], 3)
            self.assertEqual(data["top"], [["apple", 2], ["banana", 1]])
        finally:
            os.unlink(path)

    def test_no_args_returns_1(self):
        result = subprocess.run(
            [sys.executable, "wordstat.py"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("usage", result.stderr.lower())


if __name__ == "__main__":
    unittest.main()
