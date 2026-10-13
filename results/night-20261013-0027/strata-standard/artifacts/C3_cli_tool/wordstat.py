#!/usr/bin/env python3
"""wordstat.py - Display simple statistics for a UTF-8 text file.

Usage:
    python wordstat.py <file>

Output (single-line JSON):
    {"lines": int, "words": int, "chars": int, "top": [[word, count], ...]}

- lines: number of lines (splitlines count)
- words: number of whitespace-separated words
- chars: total length of the file content
- top: up to 5 most frequent lowercased words, sorted by count descending,
       then by word ascending (dictionary order) for ties.
"""

import json
import sys
from collections import Counter


def compute_stats(text):
    """Compute statistics for the given text and return a dict."""
    lines = len(text.splitlines())
    words_list = text.split()
    words = len(words_list)
    chars = len(text)

    counts = Counter(w.lower() for w in words_list)
    # Sort by count descending, then by word ascending for ties.
    top = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:5]
    top = [[w, c] for w, c in top]

    return {"lines": lines, "words": words, "chars": chars, "top": top}


def main(argv):
    if len(argv) != 2:
        print("usage: python wordstat.py <file>", file=sys.stderr)
        return 1

    path = argv[1]
    try:
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
    except OSError as e:
        print(f"error: cannot read file: {e}", file=sys.stderr)
        return 1

    stats = compute_stats(text)
    print(json.dumps(stats, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
