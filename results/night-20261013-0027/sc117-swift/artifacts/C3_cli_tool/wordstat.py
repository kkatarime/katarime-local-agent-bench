#!/usr/bin/env python3
"""wordstat.py - 標準ライブラリだけでテキストファイルの統計を出す CLI ツール."""
import json
import sys
from collections import Counter


def compute_stats(text):
    words = text.split()
    counts = Counter(w.lower() for w in words)
    top = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:5]
    return {
        "lines": len(text.splitlines()),
        "words": len(words),
        "chars": len(text),
        "top": [[w, c] for w, c in top],
    }


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print("usage: python wordstat.py <ファイル>")
        sys.exit(1)
    with open(argv[0], encoding="utf-8") as f:
        text = f.read()
    print(json.dumps(compute_stats(text), ensure_ascii=False))


if __name__ == "__main__":
    main()
