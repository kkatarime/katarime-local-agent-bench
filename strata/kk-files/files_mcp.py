"""kk-files/files_mcp.py - an MCP server (stdio, standard library only) that lets the Strata model work on the files
in ONE local folder from its chat (the web page and chat.py).

    python kk-files/files_mcp.py --root C:\\Users\\me\\work [--read-only]

Strata starts it from an "mcpServers" entry (kk-files/Strata-Files.bat writes one).  Tools: list_dir, read_file,
search_text, and unless --read-only: write_file, replace_text, move_file, make_dir.  Every path is relative to --root
and may not leave it (.. and links out of the folder are refused).  A file that write_file / replace_text overwrites
is first copied to <name>.bak-YYYYmmdd-HHMMSS; nothing is ever deleted.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time

READ_LIMIT = 20000          # characters per read_file result (Strata cuts tool results at 20,000 by default too)
MAX_HITS = 200
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv"}
ROOT = ""
READ_ONLY = False


class ToolError(Exception):
    pass


def safe(path) -> str:
    rel = str(path or ".").replace("\\", "/").lstrip("/")
    if len(rel) > 1 and rel[1] == ":":
        raise ToolError("absolute paths are not allowed; use a path relative to the folder root")
    full = os.path.realpath(os.path.join(ROOT, rel))
    if full != ROOT and not full.startswith(ROOT + os.sep):
        raise ToolError("path is outside the allowed folder: " + str(path))
    return full


def rel(full) -> str:
    return os.path.relpath(full, ROOT).replace("\\", "/")


def backup(full):
    if os.path.isfile(full):
        bak = full + ".bak-" + time.strftime("%Y%m%d-%H%M%S")
        shutil.copy2(full, bak)
        return rel(bak)
    return None


def read_text(full, with_encoding=False):
    with open(full, "rb") as f:
        data = f.read()
    if b"\0" in data[:8192]:
        raise ToolError("binary file (not text): " + rel(full))
    text, enc = None, "utf-8"
    for enc in ("utf-8-sig", "cp932"):           # Japanese Windows files are often Shift_JIS
        try:
            text = data.decode(enc)
            break
        except UnicodeDecodeError:
            pass
    if text is None:
        text, enc = data.decode("utf-8", "replace"), "utf-8"
    if enc == "utf-8-sig" and not data.startswith(b"\xef\xbb\xbf"):
        enc = "utf-8"
    return (text, enc) if with_encoding else text


# ------------------------------------------------------------------------------------------------ tools
def list_dir(path=".", recursive=False):
    base = safe(path)
    if not os.path.isdir(base):
        raise ToolError("not a directory: " + str(path))
    out = []
    if recursive:
        for d, dirs, files in os.walk(base):
            dirs[:] = sorted(x for x in dirs if x not in SKIP_DIRS)
            out += [rel(os.path.join(d, fn)) for fn in sorted(files)]
            if len(out) > 2000:
                out = out[:2000] + ["...(more than 2000 files; list a subfolder)"]
                break
    else:
        for fn in sorted(os.listdir(base)):
            full = os.path.join(base, fn)
            out.append(fn + "/" if os.path.isdir(full) else "%s  (%d bytes)" % (fn, os.path.getsize(full)))
    return "\n".join(out) or "(empty)"


def read_file(path, start_line=None, end_line=None):
    full = safe(path)
    if not os.path.isfile(full):
        raise ToolError("no such file: " + str(path))
    lines = read_text(full).splitlines(keepends=True)
    total = len(lines)
    if start_line is None and end_line is None and sum(map(len, lines)) < READ_LIMIT:
        return "".join(lines)
    a = max(1, int(start_line or 1))
    b = min(total, int(end_line or total))
    if a > b:
        return "(no lines: start_line=%d, end_line=%d, file has %d lines)" % (a, b, total)
    out, n, last = [], 0, a - 1
    for i in range(a - 1, b):
        if n + len(lines[i]) > READ_LIMIT and out:
            break
        out.append(lines[i])
        n += len(lines[i])
        last = i + 1
    s = "".join(out)
    if last < b:
        s += "\n...(truncated: lines %d-%d of %d; call read_file with start_line=%d to continue)" % (a, last, total, last + 1)
    elif a > 1 or b < total:
        s += "\n...(lines %d-%d of %d)" % (a, b, total)
    return s


def search_text(pattern, path="."):
    if not pattern:
        raise ToolError("pattern is empty")
    hits = []
    for d, dirs, files in os.walk(safe(path)):
        dirs[:] = sorted(x for x in dirs if x not in SKIP_DIRS)
        for fn in sorted(files):
            if ".bak-" in fn:                        # our own backups would only repeat the hits
                continue
            full = os.path.join(d, fn)
            try:
                text = read_text(full)
            except (OSError, ToolError):
                continue
            for i, line in enumerate(text.splitlines(), 1):
                if pattern in line:
                    hits.append("%s:%d: %s" % (rel(full), i, line.strip()[:300]))
                    if len(hits) >= MAX_HITS:
                        return "\n".join(hits) + "\n...(stopped at %d matches)" % MAX_HITS
    return "\n".join(hits) or "(no match)"


def write_file(path, content):
    full = safe(path)
    if os.path.isdir(full):
        raise ToolError("is a directory: " + str(path))
    os.makedirs(os.path.dirname(full), exist_ok=True)
    bak = backup(full)
    with open(full, "w", encoding="utf-8", newline="") as f:
        f.write(content)
    return "wrote %d characters to %s%s" % (len(content), rel(full), " (previous version saved as %s)" % bak if bak else "")


def replace_text(path, old, new, count=1):
    full = safe(path)
    if not os.path.isfile(full):
        raise ToolError("no such file: " + str(path))
    text, enc = read_text(full, with_encoding=True)
    found = text.count(old) if old else 0
    if not found:
        raise ToolError("old text not found in " + rel(full) + " (it must match exactly, including spaces)")
    count = int(count or 1)
    if count > 0 and found != count:
        raise ToolError("old text occurs %d times, expected %d; add surrounding lines to make it unique, "
                        "or pass count=%d (or count=0 for all)" % (found, count, found))
    bak = backup(full)
    with open(full, "w", encoding=enc, newline="") as f:     # keep the file's encoding (Shift_JIS stays Shift_JIS)
        f.write(text.replace(old, new))
    return "replaced %d occurrence(s) in %s (previous version saved as %s)" % (found, rel(full), bak)


def move_file(src, dst):
    s, d = safe(src), safe(dst)
    if not os.path.exists(s):
        raise ToolError("no such file: " + str(src))
    if os.path.exists(d):
        raise ToolError("destination already exists: " + str(dst))
    os.makedirs(os.path.dirname(d), exist_ok=True)
    shutil.move(s, d)
    return "moved %s -> %s" % (rel(s), rel(d))


def make_dir(path):
    full = safe(path)
    os.makedirs(full, exist_ok=True)
    return "created " + rel(full)


S, I, B = {"type": "string"}, {"type": "integer"}, {"type": "boolean"}


def tool(fn, desc, props, req, writes=False):
    return {"fn": fn, "writes": writes, "spec": {"name": fn.__name__, "description": desc, "inputSchema":
            {"type": "object", "properties": props, "required": req}}}


TOOLS = [
    tool(list_dir, "List a folder (path relative to the root; '.' is the root). recursive=true lists every file below.",
         {"path": S, "recursive": B}, []),
    tool(read_file, "Read a text file. start_line/end_line (1-based, inclusive) read part of a large file.",
         {"path": S, "start_line": I, "end_line": I}, ["path"]),
    tool(search_text, "Find lines that contain a literal string, in every text file under a folder.",
         {"pattern": S, "path": S}, ["pattern"]),
    tool(write_file, "Create a file, or replace a whole file with new content. The old file is kept as a .bak copy.",
         {"path": S, "content": S}, ["path", "content"], True),
    tool(replace_text, "Change part of a file: replace the exact text `old` with `new`. `old` must occur `count` "
         "times (default 1; 0 = replace all). Prefer this to write_file for small edits.",
         {"path": S, "old": S, "new": S, "count": I}, ["path", "old", "new"], True),
    tool(move_file, "Move or rename a file or folder (the destination must not exist).", {"src": S, "dst": S},
         ["src", "dst"], True),
    tool(make_dir, "Create a folder (and its parents).", {"path": S}, ["path"], True),
]


def active():
    return [t for t in TOOLS if not (READ_ONLY and t["writes"])]


# ------------------------------------------------------------------------------------------------ MCP (stdio)
def result(text, error=False):
    return {"content": [{"type": "text", "text": text}], "isError": error}


def handle(msg):
    method, rid, params = msg.get("method"), msg.get("id"), msg.get("params") or {}
    if "id" not in msg:                          # notifications (initialized, cancelled): nothing to answer
        return None
    if method == "initialize":
        res = {"protocolVersion": params.get("protocolVersion") or "2025-06-18", "capabilities": {"tools": {}},
               "serverInfo": {"name": "kk-files", "version": "0.1"},
               "instructions": "Files in %s%s. Paths are relative to that folder." % (ROOT, " (read only)" if READ_ONLY else "")}
    elif method == "ping":
        res = {}
    elif method == "tools/list":
        res = {"tools": [t["spec"] for t in active()]}
    elif method == "tools/call":
        t = next((t for t in active() if t["spec"]["name"] == params.get("name")), None)
        if t is None:
            res = result("unknown tool: %s" % params.get("name"), True)
        else:
            try:
                res = result(t["fn"](**(params.get("arguments") or {})))
            except (ToolError, OSError, TypeError, ValueError) as e:
                res = result(str(e), True)
    else:
        return {"jsonrpc": "2.0", "id": rid, "error": {"code": -32601, "message": "method not found: %s" % method}}
    return {"jsonrpc": "2.0", "id": rid, "result": res}


def main():
    global ROOT, READ_ONLY
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", required=True, help="the only folder the model may touch")
    ap.add_argument("--read-only", action="store_true", help="offer only list_dir, read_file and search_text")
    a = ap.parse_args()
    ROOT = os.path.realpath(os.path.expanduser(a.root))
    READ_ONLY = a.read_only
    if not os.path.isdir(ROOT):
        sys.exit("[kk-files] no such folder: " + ROOT)
    stdin = open(sys.stdin.fileno(), "r", encoding="utf-8", closefd=False)
    stdout = open(sys.stdout.fileno(), "w", encoding="utf-8", newline="\n", closefd=False)
    print("[kk-files] ready: %s%s" % (ROOT, " (read only)" if READ_ONLY else ""), file=sys.stderr, flush=True)
    for line in stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except ValueError:
            continue
        out = handle(msg) if isinstance(msg, dict) else None
        if out is not None:
            stdout.write(json.dumps(out, ensure_ascii=False) + "\n")
            stdout.flush()


if __name__ == "__main__":
    main()
