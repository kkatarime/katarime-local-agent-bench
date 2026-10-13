"""wordstat.py の unittest テスト。"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file))))

from wordstat import compute_stats, main  # noqa: E402


class TestComputeStats(unittest.TestCase):
    def test_basic_counts(self):
        text = "the quick brown fox\nthe lazy dog\n"
        stats = compute_stats(text)
        self.assertEqual(stats["lines"], 2)
        self.assertEqual(stats["words"], 7)
        self.assertEqual(stats["chars"], len(text))

    def test_top_ordering(self):
        text = "the THE the and and fox"
        stats = compute_stats(text)
        top = stats["top"]
        self.assertEqual(top[0], ["the", 3])
        self.assertEqual(top[1], ["and", 2])

    def test_tie_dictionary_order(self):
        # 回数が同じなら辞書順
        text = "beta alpha gamma delta epsilon zeta"
        stats = compute_stats(text)
        words = [w for w, _ in stats["top"]]
        self.assertEqual(words, sorted(words)[:5])
        self.assertEqual(len(stats["top"]), 5)

    def test_utf8_multibyte_chars(self):
        text = "こんにちは 世界\nこんにちは\n"
        stats = compute_stats(text)
        self.assertEqual(stats["lines"], 2)
        self.assertEqual(stats["words"], 3)
        self.assertEqual(stats["chars"], len(text))
        self.assertEqual(stats["top"][0], ["こんにちは", 2])


class TestMainExitCode(unittest.TestCase):
    def test_no_args_returns_1(self):
        # 引数なしなら終了コード 1
        code = main(["wordstat.py"])
        self.assertEqual(code, 1)

    def test_cli_output_is_valid_json(self):
        with tempfile.NamedTemporaryFile(
            "w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            f.write("foo bar foo\nbaz\n")
            path = f.name
        try:
            out = subprocess.run(
                [sys.executable, "wordstat.py", path],
                capture_output=True, text=True,
                cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            )
            self.assertEqual(out.returncode, 0)
            data = json.loads(out.stdout)
            self.assertEqual(data["top"][0], ["foo", 2])
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
