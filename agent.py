# -*- coding: utf-8 -*-
"""local file-operation agent test harness (stdlib only, fully local).
Talks to an OpenAI-compatible server on 127.0.0.1 (llama-server --jinja),
gives the model 5 file tools sandboxed to ./sandbox, runs 5 tasks, and
grades each result by inspecting the files (not the model's claims)."""
import json, os, sys, time, shutil, re, urllib.request, argparse, csv

HERE = os.path.dirname(os.path.abspath(__file__))
SANDBOX = os.path.join(HERE, "sandbox")

# ---------------- fixture ----------------
FIXTURE = {
    "notes/meeting.txt": "定例会議メモ 2026-10-01\n参加: 佐藤, 田中, 鈴木\n議題: リリース準備\n決定事項:\n- 田中がテスト計画を金曜までに作る\n- 鈴木がCIのタイムアウトを延長する\n- 佐藤が顧客向けリリースノートを書く\n雑談: ランチはカレー\n",
    "notes/idea.md": "# アイデア\n- ローカルLLMでファイル整理\n",
    "config/app.ini": "[server]\nhost = 127.0.0.1\nport = 8080\nworkers = 4\n\n[log]\nlevel = info\n",
    "src/main.py": "def main():\n    print('hello')\n",
    "src/util/helpers.py": "# helper funcs\n# TODO-SECRET-42: replace this stub\ndef add(a, b):\n    return a + b\n",
    "src/util/__init__.py": "",
    "data/a.csv": "name,score\nalice,10\nbob,20\n",
    "data/b.csv": "name,score\ncarol,30\ndave,40\n",
    "logs/run1.log": "ok\n",
    "logs/run2.log": "ok\n",
}

def build_sandbox():
    if os.path.exists(SANDBOX):
        shutil.rmtree(SANDBOX)
    for rel, body in FIXTURE.items():
        p = os.path.join(SANDBOX, *rel.split("/"))
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8", newline="\n") as f:
            f.write(body)

def rd(rel):
    p = os.path.join(SANDBOX, *rel.split("/"))
    if not os.path.isfile(p):
        return None
    with open(p, encoding="utf-8", errors="replace") as f:
        return f.read()

# ---------------- tools (sandboxed) ----------------
def safe(path):
    path = (path or ".").replace("\\", "/").lstrip("/")
    full = os.path.realpath(os.path.join(SANDBOX, path))
    root = os.path.realpath(SANDBOX)
    if full != root and not full.startswith(root + os.sep):
        raise ValueError("path escapes sandbox: " + path)
    return full

def t_list_dir(path=".", recursive=False):
    base = safe(path)
    out = []
    if recursive:
        for d, dirs, files in os.walk(base):
            dirs.sort()
            for fn in sorted(files):
                out.append(os.path.relpath(os.path.join(d, fn), SANDBOX).replace("\\", "/"))
    else:
        for fn in sorted(os.listdir(base)):
            full = os.path.join(base, fn)
            out.append(fn + ("/" if os.path.isdir(full) else ""))
    return "\n".join(out) or "(empty)"

def t_read_file(path):
    with open(safe(path), encoding="utf-8", errors="replace") as f:
        s = f.read()
    return s if len(s) < 20000 else s[:20000] + "\n...(truncated)"

def t_write_file(path, content):
    full = safe(path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
    return "wrote %d chars to %s" % (len(content), path)

def t_search_text(pattern, path="."):
    hits = []
    for d, _, files in os.walk(safe(path)):
        for fn in files:
            full = os.path.join(d, fn)
            try:
                with open(full, encoding="utf-8", errors="replace") as f:
                    for i, line in enumerate(f, 1):
                        if pattern in line:
                            hits.append("%s:%d: %s" % (os.path.relpath(full, SANDBOX).replace("\\", "/"), i, line.rstrip()))
            except OSError:
                pass
    return "\n".join(hits) or "(no match)"

def t_move_file(src, dst):
    s, d = safe(src), safe(dst)
    os.makedirs(os.path.dirname(d), exist_ok=True)
    shutil.move(s, d)
    return "moved %s -> %s" % (src, dst)

TOOLS = {"list_dir": t_list_dir, "read_file": t_read_file, "write_file": t_write_file,
         "search_text": t_search_text, "move_file": t_move_file}

def fn_schema(name, desc, props, req):
    return {"type": "function", "function": {"name": name, "description": desc,
            "parameters": {"type": "object", "properties": props, "required": req}}}

S = {"type": "string"}
TOOL_SCHEMAS = [
    fn_schema("list_dir", "List entries of a directory (relative to workspace root). recursive=true lists all files.",
              {"path": S, "recursive": {"type": "boolean"}}, []),
    fn_schema("read_file", "Read a UTF-8 text file.", {"path": S}, ["path"]),
    fn_schema("write_file", "Create or overwrite a text file with the full content.", {"path": S, "content": S}, ["path", "content"]),
    fn_schema("search_text", "Find lines containing a literal string under a directory.", {"pattern": S, "path": S}, ["pattern"]),
    fn_schema("move_file", "Move or rename a file.", {"src": S, "dst": S}, ["src", "dst"]),
]

# ---------------- tasks + graders ----------------
def g1():
    s = rd("report1.md") or ""
    return all(re.search(p, s) for p in [r"10", r"\.py\D*3|3\D*\.py", r"\.csv\D*2|2\D*\.csv", r"\.log\D*2|2\D*\.log"])
def g2():
    s = rd("summary.md") or ""
    return all(k in s for k in ["田中", "鈴木", "佐藤"]) and ("テスト" in s and "CI" in s and "リリースノート" in s) and "カレー" not in s
def g3():
    want = FIXTURE["config/app.ini"].replace("port = 8080", "port = 9090")
    return (rd("config/app.ini") or "").replace("\r\n", "\n").rstrip("\n") == want.rstrip("\n")
def g4():
    return "src/util/helpers.py" in (rd("found.txt") or "").replace("\\", "/")
def g5():
    s = (rd("data/merged.csv") or "").replace("\r\n", "\n").strip().splitlines()
    return (len(s) == 5 and s[0].replace(" ", "") == "name,score"
            and sorted(x.replace(" ", "") for x in s[1:]) == ["alice,10", "bob,20", "carol,30", "dave,40"])

def g6():
    s = rd("game/index.html") or ""
    return len(s) > 1500 and "<canvas" in s.lower() and "gameState" in s and "</html>" in s.lower()

GAME_SPEC = ("ブラウザで動くブロック崩しゲームを game/index.html に1ファイルで作ってください。外部ライブラリ・外部ファイル・ネット接続は使わず、HTML/CSS/JavaScript と <canvas> だけで書くこと。\n"
             "必須仕様:\n1. ←→キーでパドルが左右に動く\n2. ボールが壁・パドル・ブロックで反射する\n3. ブロックは5行×8列、壊すとスコア+10\n"
             "4. ライフは3。ボールが下に落ちるとライフ-1、0でゲームオーバー表示\n5. 全ブロックを壊したらクリア表示\n6. Rキーでいつでも最初からやり直せる\n"
             "7. スペースキーでボール発射\n8. 自動テスト用に window.gameState = {score, lives, state} を常に最新に保つこと（state は 'ready'|'playing'|'gameover'|'clear'）。"
             "さらに window.gameState.ball = {x, y, vx, vy} と window.gameState.paddle = {x, y, w} も公開すること\n"
             "書き終えたら read_file で読み返し、仕様漏れや文法ミスがあれば write_file で全体を書き直してください。")

TASKS = [
    ("T1_inventory", "ワークスペース全体のファイルを調べ、総ファイル数と拡張子ごとのファイル数（.py, .csv, .log など）を report1.md に書いてください。", g1),
    ("T2_summarize", "notes/meeting.txt を読み、決定事項（誰が何をするか）だけを箇条書きで summary.md にまとめてください。雑談は含めないこと。", g2),
    ("T3_edit", "config/app.ini の port を 9090 に変更してください。他の行は一切変えないこと。", g3),
    ("T4_search", "文字列 TODO-SECRET-42 を含むファイルを探し、そのファイルのパスだけを found.txt に書いてください。", g4),
    ("T5_merge", "data フォルダの CSV をすべて結合して data/merged.csv を作ってください。ヘッダー行は先頭に1回だけにすること。", g5),
    ("T6_game", GAME_SPEC, g6),
]
MAX_STEPS = {"T6_game": 30}
DEADLINE = [None]

SYSTEM = ("あなたはローカルPC上のファイル操作エージェントです。必ずツールを使って実際にファイルを読み書きしてください。"
          "パスはワークスペースのルートからの相対パスです。作業が終わったら、何をしたかを1〜2文で答えて終了してください。")

# ---------------- LLM client ----------------
NOPROXY = urllib.request.build_opener(urllib.request.ProxyHandler({}))

def chat(url, model, messages, timeout, think=True, max_tokens=8192, effort=""):
    payload = {"model": model, "messages": messages, "tools": TOOL_SCHEMAS,
               "tool_choice": "auto", "temperature": 0.2, "max_tokens": max_tokens}
    if not think:
        payload["chat_template_kwargs"] = {"enable_thinking": False}
    if effort:
        payload["reasoning_effort"] = effort   # Strata: none/low/medium/high (default high)
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url.rstrip("/") + "/v1/chat/completions", data=body,
                                 headers={"Content-Type": "application/json"})
    with NOPROXY.open(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))

def run_task(args, tid, prompt, log):
    msgs = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}]
    steps = toks = 0
    err = ""
    t0 = time.time()
    for steps in range(1, MAX_STEPS.get(tid, args.max_steps) + 1):
        if DEADLINE[0] and time.time() > DEADLINE[0]:
            err = "deadline"
            break
        try:
            to = args.timeout if not DEADLINE[0] else max(30, min(args.timeout, int(DEADLINE[0] - time.time())))
            resp = chat(args.url, args.model, msgs, to, args.think == "on", args.max_tokens, args.effort)
        except Exception as e:
            err = "llm_error: %r" % e
            break
        toks += (resp.get("usage") or {}).get("completion_tokens", 0)
        ch = resp["choices"][0]
        m = ch["message"]
        calls = m.get("tool_calls") or []
        if not calls and ch.get("finish_reason") == "length":
            # thinking ran out the token budget before acting: nudge once per step
            log.write(json.dumps({"task": tid, "step": steps, "event": "length_no_action",
                                  "reasoning_len": len(m.get("reasoning_content") or "")}) + "\n")
            msgs.append({"role": "user", "content": "考えすぎです。推論は短く切り上げて、今すぐ必要なツールを1つ呼んでください。"})
            continue
        msgs.append({"role": "assistant", "content": m.get("content") or "", **({"tool_calls": calls} if calls else {})})
        log.write(json.dumps({"task": tid, "step": steps, "content": m.get("content"),
                              "reasoning_len": len(m.get("reasoning_content") or ""), "tool_calls": calls}, ensure_ascii=False) + "\n")
        if not calls:
            break
        for c in calls:
            name = c["function"]["name"]
            try:
                a = c["function"].get("arguments") or "{}"
                a = json.loads(a) if isinstance(a, str) else a
                out = TOOLS[name](**a)
            except Exception as e:
                out = "ERROR: %r" % e
            log.write(json.dumps({"task": tid, "tool": name, "result": out[:2000]}, ensure_ascii=False) + "\n")
            msgs.append({"role": "tool", "tool_call_id": c.get("id", ""), "content": out})
    else:
        err = "max_steps"
    return steps, toks, round(time.time() - t0, 1), err

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:8085")
    ap.add_argument("--model", default="local")
    ap.add_argument("--max-steps", type=int, default=15)
    ap.add_argument("--timeout", type=int, default=600)
    ap.add_argument("--logdir", default=os.path.join(HERE, "logs"))
    ap.add_argument("--think", choices=["on", "off"], default="on")
    ap.add_argument("--max-tokens", type=int, default=8192)
    ap.add_argument("--effort", default="", help="reasoning_effort sent to the server (Strata)")
    ap.add_argument("--tag", default="")
    ap.add_argument("--tasks", default="")
    ap.add_argument("--deadline", type=int, default=0, help="wall-clock seconds for the whole run")
    args = ap.parse_args()
    os.makedirs(args.logdir, exist_ok=True)
    if args.deadline:
        DEADLINE[0] = time.time() + args.deadline
    build_sandbox()
    rows = []
    want = [t for t in args.tasks.split(",") if t]
    res_path = os.path.join(args.logdir, "results%s.csv" % args.tag)
    def save():
        with open(res_path, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["task", "result", "steps", "completion_tokens", "seconds", "error"])
            w.writerows(rows)
    with open(os.path.join(args.logdir, "transcript%s.jsonl" % args.tag), "w", encoding="utf-8") as log:
        for tid, prompt, grade in TASKS:
            if want and tid not in want:
                continue
            print("[%s] start" % tid, flush=True)
            steps, toks, sec, err = run_task(args, tid, prompt, log)
            ok = False
            try:
                ok = grade()
            except Exception as e:
                err = (err + " grade_error:%r" % e).strip()
            rows.append([tid, "PASS" if ok else "FAIL", steps, toks, sec, err])
            print("[%s] %s steps=%d tokens=%d %ss %s" % (tid, rows[-1][1], steps, toks, sec, err), flush=True)
            log.flush()
            save()
    game = os.path.join(SANDBOX, "game", "index.html")
    if os.path.isfile(game):
        shutil.copy(game, os.path.join(args.logdir, "game%s.html" % args.tag))
    print("[think=%s%s] PASS %d / %d" % (args.think, (" effort=" + args.effort) if args.effort else "", sum(r[1] == "PASS" for r in rows), len(rows)))

if __name__ == "__main__":
    main()
