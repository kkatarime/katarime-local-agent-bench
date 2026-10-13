#!/usr/bin/env python3
"""wordstat.py - 単語・行・文字数の統計を JSON で出力する CLI ツール。

使い方:
    python wordstat.py <ファイル>

出力例:
    {"lines": 3, "words": 10, "chars": 57, "top": [["the", 3], ["and", 2], ...]}
"""
import json
import sys
from collections import Counter


def compute_stats(text: str) -> dict:
    """テキストから統計情報を計算して dict で返す。"""
    lines = len(text.splitlines())
    words_list = text.split()
    words = len(words_list)
    chars = len(text)

    counter = Counter(w.lower() for w in words_list)
    # 回数の多い順、同回数なら辞書順
    top = sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))[:5]
    top = [[w, c] for w, c in top]

    return {"lines": lines, "words": words, "chars": chars, "top": top}


def main(argv=None) -> int:
    argv = sys.argv if argv is None else argv
    if len(argv) != 2:
        prog = argv[0] if argv else "wordstat.py"
        print(f"usage: {prog} <file>", file=sys.stderr)
        return 1

    path = argv[1]
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except OSError as e:
        print(f"error: cannot read file: {e}", file=sys.stderr)
        return 1

    stats = compute_stats(text)
    print(json.dumps(stats, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
