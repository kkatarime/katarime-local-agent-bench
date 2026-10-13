"""Tests for wordstat.py."""

import json
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import wordstat

WORDSTAT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "wordstat.py")


def run_cli(*args):
    return subprocess.run(
        [sys.executable, WORDSTAT, *args],
        capture_output=True,
        text=True,
    )


class TestComputeStats(unittest.TestCase):
    def test_basic(self):
        text = "Hello world\nhello WORLD\nfoo"
        stats = wordstat.compute_stats(text)
        self.assertEqual(stats["lines"], 3)
        self.assertEqual(stats["words"], 5)
        self.assertEqual(stats["chars"], len(text))
        # hello:2, world:2, foo:1 -> ties broken by dictionary order
        self.assertEqual(stats["top"], [["hello", 2], ["world", 2], ["foo", 1]])

    def test_empty(self):
        stats = wordstat.compute_stats("")
        self.assertEqual(stats, {"lines": 0, "words": 0, "chars": 0, "top": []})

    def test_top_max_five_and_tie_order(self):
        text = "a a a b b b c c c d d d e e e f f f g g g"
        stats = wordstat.compute_stats(text)
        self.assertEqual(stats["top"], [["a", 3], ["b", 3], ["c", 3], ["d", 3], ["e", 3]])
        self.assertEqual(len(stats["top"]), 5)


class TestCLI(unittest.TestCase):
    def test_output_json(self):
        with tempfile.NamedTemporaryFile(
            "w", suffix=".txt", encoding="utf-8", delete=False
        ) as f:
            f.write("apple apple banana\nApple\n")
            path = f.name
        try:
            result = run_cli(path)
            self.assertEqual(result.returncode, 0)
            data = json.loads(result.stdout.strip())
            self.assertEqual(data["lines"], 2)
            self.assertEqual(data["words"], 4)
            self.assertEqual(data["chars"], len("apple apple banana\nApple\n"))
            self.assertEqual(data["top"], [["apple", 3], ["banana", 1]])
            # Output must be a single line
            self.assertEqual(result.stdout.count("\n"), 1)
        finally:
            os.unlink(path)

    def test_utf8_file(self):
        with tempfile.NamedTemporaryFile(
            "w", suffix=".txt", encoding="utf-8", delete=False
        ) as f:
            f.write("こんにちは 世界 こんにちは\n")
            path = f.name
        try:
            result = run_cli(path)
            self.assertEqual(result.returncode, 0)
            data = json.loads(result.stdout)
            self.assertEqual(data["words"], 3)
            self.assertEqual(data["top"], [["こんにちは", 2], ["世界", 1]])
        finally:
            os.unlink(path)

    def test_no_args_usage_and_exit_code(self):
        result = run_cli()
        self.assertEqual(result.returncode, 1)
        self.assertIn("usage", result.stderr.lower())


if __name__ == "__main__":
    unittest.main()
