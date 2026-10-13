#!/usr/bin/env python3
"""wordstat.py - UTF-8 テキストファイルの統計を JSON で出力する CLI ツール。

使い方:
    python wordstat.py <ファイル>

出力 (1行の JSON):
    {"lines": 行数, "words": 単語数, "chars": 文字数, "top": [[単語, 回数], ...]}
"""
import json
import sys
from collections import Counter


def compute_stats(text):
    """テキストから統計辞書を作る。"""
    words = text.split()
    lowered = [w.lower() for w in words]
    counter = Counter(lowered)
    top = sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))[:5]
    return {
        "lines": len(text.splitlines()),
        "words": len(words),
        "chars": len(text),
        "top": [[w, c] for w, c in top],
    }


def main(argv):
    if len(argv) != 2:
        print("usage: python wordstat.py <file>", file=sys.stderr)
        return 1
    path = argv[1]
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except OSError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    stats = compute_stats(text)
    print(json.dumps(stats, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
