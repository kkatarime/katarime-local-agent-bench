#!/usr/bin/env python3
"""A tiny terminal chat for a running Strata server (start it with run-<model>.bat / run-<model>.sh first).

    python chat.py [--port 8080] [--think none|low|medium|high]

Type a message and press Enter.  /image <path> attaches a picture to your next message (when the server was set up
with images), /think <none|low|medium|high> sets how long the model thinks first, /tools on|off lets the model use
the server's MCP tools (kk-files: the files in one folder, see kk-files/README.md), /reset starts a new conversation,
/quit leaves.  Standard library only.
"""
from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import sys
import time
import urllib.request


def stream(url, messages, think, max_tokens, tools=True):
    body = {"model": "strata", "messages": messages, "stream": True, "max_tokens": max_tokens,
            "reasoning_effort": think}
    if tools:
        body["strata_mcp"] = True          # let the server run its MCP tools (e.g. kk-files) for this chat
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=3600) as r:
        for raw in r:
            line = raw.decode("utf-8", "replace").strip()
            if not line.startswith("data: ") or line == "data: [DONE]":
                continue
            j = json.loads(line[6:])
            d = j["choices"][0]["delta"]
            yield d.get("reasoning_content") or "", d.get("content") or "", j.get("strata_mcp")


def tool_line(ev):
    """One line for an MCP tool event from the server, or None for the ones not worth showing."""
    if ev.get("event") == "call":
        args = ev.get("arguments")
        args = args if isinstance(args, dict) else {}
        shown = ", ".join(f"{k}={str(v)[:60] + ('...' if len(str(v)) > 60 else '')!r}" for k, v in args.items())
        return f"[tool] {ev.get('tool') or ev.get('name')}({shown})"
    if ev.get("event") == "result" and not ev.get("skipped"):
        first = (ev.get("text") or "").strip().splitlines()[:1]
        return f"[tool] {'ok' if ev.get('ok') else 'failed'}, {ev.get('chars', 0):,} chars" + \
            (f": {first[0][:100]}" if first and not ev.get("ok") else "")
    if ev.get("event") == "limit":
        return f"[tool] stopped after {ev.get('max_rounds')} tool calls in a row"
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", type=int, default=8080)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--think", default="medium", choices=["none", "low", "medium", "high"],
                    help="how long the model thinks before answering (none = answer directly)")
    ap.add_argument("--no-think", action="store_true", help="same as --think none")
    ap.add_argument("--max-tokens", type=int, default=4096)
    ap.add_argument("--no-tools", action="store_true",
                    help="do not let the model use the server's MCP tools (files etc.); /tools on|off switches it too")
    a = ap.parse_args()
    url = f"http://{a.host}:{a.port}/v1/chat/completions"
    gray, reset = ("\033[90m", "\033[0m") if sys.stdout.isatty() else ("", "")
    messages, pending = [], []
    think = "none" if a.no_think else a.think
    tools = not a.no_tools
    print(f"Strata chat ({url}).  /image <path> = attach a picture, /think none|low|medium|high (now: {think}), "
          f"/tools on|off (now: {'on' if tools else 'off'}), /reset = new conversation, /quit = leave.")
    try:
        with urllib.request.urlopen(f"http://{a.host}:{a.port}/mcp", timeout=5) as r:
            st = json.loads(r.read())
        names = [f"{s['name']} ({len(s.get('tools') or [])} tools, {s.get('status')})" for s in st.get("servers", [])]
        print("MCP tools: " + (", ".join(names) if names else "none configured (see kk-files/README.md)"))
    except (OSError, ValueError):
        pass
    while True:
        try:
            user = input("\nyou> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if user in ("/quit", "/exit"):
            return 0
        if user == "/reset":
            messages, pending = [], []
            print("(new conversation)")
            continue
        if user.startswith("/think"):
            level = user[6:].strip().lower()
            if level in ("none", "low", "medium", "high"):
                think = level
                print(f"(thinking: {think})")
            else:
                print("(usage: /think none|low|medium|high)")
            continue
        if user.startswith("/tools"):
            arg = user[6:].strip().lower()
            if arg in ("on", "off"):
                tools = arg == "on"
            print(f"(tools: {'on' if tools else 'off'})" if arg in ("on", "off", "") else "(usage: /tools on|off)")
            continue
        if user.startswith("/image"):
            path = user[6:].strip().strip('"').strip("'")
            if not os.path.isfile(path):
                print(f"(no such file: {path or '?'} - usage: /image <path to a picture>)")
                continue
            mime = mimetypes.guess_type(path)[0] or "image/jpeg"
            data = base64.b64encode(open(path, "rb").read()).decode()
            pending.append({"type": "image_url", "image_url": {"url": f"data:{mime};base64,{data}"}})
            print(f"(picture attached: {os.path.basename(path)} - now type your question)")
            continue
        if not user:
            continue
        if pending:
            messages.append({"role": "user", "content": [*pending, {"type": "text", "text": user}]})
            pending = []
        else:
            messages.append({"role": "user", "content": user})
        answer, n, t0 = [], 0, time.time()
        print("model> ", end="", flush=True)
        try:
            in_think = False
            for reasoning, content, tool in stream(url, messages, think, a.max_tokens, tools):
                line = tool_line(tool) if tool else None
                if line:
                    print((reset if in_think else "") + f"\n{gray}{line}{reset}", flush=True)
                    in_think = False
                if reasoning:
                    if not in_think:
                        print(gray, end="")
                        in_think = True
                    print(reasoning, end="", flush=True)
                if content:
                    if in_think:
                        print(reset + "\n", end="")
                        in_think = False
                    print(content, end="", flush=True)
                    answer.append(content)
                n += 1
            if in_think:
                print(reset, end="")
        except OSError as e:
            print(f"\n(could not reach the server at {url}: {e})")
            messages.pop()
            continue
        dt = time.time() - t0
        print(f"\n{gray}[{n} chunks in {dt:.1f} s]{reset}")
        messages.append({"role": "assistant", "content": "".join(answer)})


if __name__ == "__main__":
    sys.exit(main())
