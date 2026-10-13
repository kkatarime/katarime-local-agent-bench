"""wordstat.py の unittest テスト."""
import json
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import wordstat  # noqa: E402


def run_cli(args):
    return subprocess.run(
        [sys.executable, os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))), "wordstat.py")] + args,
        capture_output=True, text=True,
    )


class TestWordstat(unittest.TestCase):
    def test_basic_stats(self):
        text = "Hello world\nhello WORLD foo\nfoo foo bar\n"
        stats = wordstat.compute_stats(text)
        self.assertEqual(stats["lines"], 3)
        self.assertEqual(stats["words"], 8)
        self.assertEqual(stats["chars"], len(text))
        # hello:2, world:2, foo:3, bar:1 -> sorted by count desc, then dict order
        self.assertEqual(stats["top"], [["foo", 3], ["hello", 2], ["world", 2], ["bar", 1]])

    def test_top_tie_dictionary_order(self):
        text = "b a a b c"
        stats = wordstat.compute_stats(text)
        # a:2, b:2, c:1 -> tie broken by dictionary order
        self.assertEqual(stats["top"], [["a", 2], ["b", 2], ["c", 1]])

    def test_top_max_five(self):
        text = "e d c b a a b c d e e"
        stats = wordstat.compute_stats(text)
        self.assertEqual(len(stats["top"]), 5)
        self.assertEqual(stats["top"][0], ["e", 3])
        self.assertEqual(stats["top"], [["e", 3], ["a", 2], ["b", 2], ["c", 2], ["d", 2]])

    def test_cli_outputs_json_line(self):
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False,
                                         encoding="utf-8", dir=".") as f:
            f.write("apple banana\nbanana cherry\n")
            path = f.name
        try:
            proc = run_cli([path])
            self.assertEqual(proc.returncode, 0)
            result = json.loads(proc.stdout.strip())
            self.assertEqual(result["lines"], 2)
            self.assertEqual(result["words"], 4)
            self.assertEqual(result["top"][0], ["banana", 2])
        finally:
            os.unlink(path)

    def test_cli_no_args_exit_1(self):
        proc = run_cli([])
        self.assertEqual(proc.returncode, 1)
        self.assertIn("usage", proc.stdout.lower())


if __name__ == "__main__":
    unittest.main()
