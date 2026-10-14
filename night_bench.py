# -*- coding: utf-8 -*-
"""night_bench.py - an overnight benchmark for local models behind an OpenAI-compatible server (Strata).

    python night_bench.py run --url http://127.0.0.1:8085 --name orca --ctx 65536 --logdir logs/night/x/orca
    python night_bench.py report --root logs/night/x           # REPORT.md + summary.csv over every model
    python night_bench.py make-config --src a.json --ctx 65536 --out b.json
    python night_bench.py selftest                             # graders against reference solutions (no model)

Three groups of tasks, every one graded from the files the model leaves (never from what it says):
  L  long context: one prompt of 6K ... 120K characters with 5 facts hidden at different depths (no tools);
     how many it finds, how long the prompt really was in tokens, time to the first token, prefill speed.
  B  multi-file work with the file tools: rename across modules, fix bugs until hidden tests pass, sort files into
     folders, aggregate 12 CSVs, edit three config formats, collect facts spread over 8 documents.
  C  how complete a thing it can build: a Breakout game and a 3-file TODO app (both played in a headless browser),
     a Python CLI with its own tests (run on hidden inputs), a long design document (structure checks).
Each task works in its own folder under <logdir>/work/<task>, kept for a look in the morning.
Standard library only.  The browser checks need Edge or Chrome (found automatically, or BENCH_BROWSER=path).
"""
from __future__ import annotations

import argparse, csv, glob, hashlib, json, os, random, re, shutil, subprocess, sys, tempfile, time
import urllib.error, urllib.request

import agent

HERE = os.path.dirname(os.path.abspath(__file__))
NOPROXY = urllib.request.build_opener(urllib.request.ProxyHandler({}))
SYSTEM = agent.SYSTEM


# ================================================================================================ helpers
def wr(root, rel, text):
    p = os.path.join(root, *rel.split("/"))
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def rd(root, rel):
    p = os.path.join(root, *rel.split("/"))
    if not os.path.isfile(p):
        return None
    with open(p, encoding="utf-8", errors="replace") as f:
        return f.read()


def sha(root, rel):
    p = os.path.join(root, *rel.split("/"))
    return hashlib.sha256(open(p, "rb").read()).hexdigest() if os.path.isfile(p) else None


def run_py(root, args, timeout=60, stdin=None):
    """Run Python in the task folder (the model's code: only inside its own folder, with a time limit)."""
    try:
        r = subprocess.run([sys.executable, *args], cwd=root, capture_output=True, text=True, timeout=timeout,
                           input=stdin, encoding="utf-8", errors="replace",
                           env=dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1"))
        return r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "timeout"


def unittest_counts(root, start="tests"):
    """(passed, total, tail of the output) of `python -m unittest discover -s tests -t .` in the task folder."""
    code, out, err = run_py(root, ["-m", "unittest", "discover", "-s", start, "-t", "."], timeout=120)
    text = out + err
    m = re.search(r"Ran (\d+) tests?", text)
    total = int(m.group(1)) if m else 0
    m2 = re.search(r"FAILED \(([^)]*)\)", text)
    bad = sum(int(x) for x in re.findall(r"(?:failures|errors)=(\d+)", m2.group(1))) if m2 else 0
    return max(0, total - bad), total, text[-1500:]


# ------------------------------------------------------------------------------------------------ browser
def find_browser():
    env = os.environ.get("BENCH_BROWSER")
    if env and os.path.isfile(env):
        return env
    cands = [r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
             r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
             r"C:\Program Files\Google\Chrome\Application\chrome.exe",
             os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
             "/usr/bin/chromium", "/usr/bin/google-chrome"]
    cands += glob.glob("/opt/pw-browsers/chromium-*/chrome-linux/chrome")
    return next((c for c in cands if os.path.isfile(c)), None)


def browser_run(page, profile, budget_ms=60000):
    """Open `page` headless, let its timers run (virtual time), return the JSON the harness left in #__bench."""
    exe = find_browser()
    if not exe:
        return None, "no Edge/Chrome found (set BENCH_BROWSER)"
    args = [exe, "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
            "--allow-file-access-from-files", "--user-data-dir=" + profile,
            "--virtual-time-budget=%d" % budget_ms, "--dump-dom", "file:///" + page.replace("\\", "/").lstrip("/")]
    if sys.platform != "win32":
        args.insert(1, "--no-sandbox")
    try:
        r = subprocess.run(args, capture_output=True, timeout=180, encoding="utf-8", errors="replace")
    except subprocess.TimeoutExpired:
        return None, "browser timeout"
    m = re.search(r'<pre id="__bench">(.*?)</pre>', r.stdout or "", re.S)
    if not m:
        return None, "harness did not finish (page crashed or blocked): " + (r.stderr or "")[-300:]
    import html
    try:
        return json.loads(html.unescape(m.group(1))), ""
    except ValueError as e:
        return None, "bad harness output: %r" % e


# Headless with --virtual-time-budget never fires requestAnimationFrame, so a game driven by it would look frozen:
# replace it with a ~60 fps timer, which virtual time does run.
EARLY = ("<script>window.__benchErrors=[];window.addEventListener('error',function(e){"
         "window.__benchErrors.push(String(e.message||e));});"
         "window.requestAnimationFrame=function(cb){return setTimeout(function(){cb(performance.now());},16);};"
         "window.cancelAnimationFrame=function(id){clearTimeout(id);};</script>\n")


def inject(html_text, script):
    """The harness at the end of the body, and an error catcher before the page's own scripts (a syntax error in
    them happens before the harness exists)."""
    tag = "<script>\n" + script + "\n</script>\n"
    i = html_text.lower().rfind("</body>")
    html_text = html_text[:i] + tag + html_text[i:] if i >= 0 else html_text + tag
    m = re.search(r"<head[^>]*>", html_text, re.I) or re.search(r"<html[^>]*>", html_text, re.I)
    j = m.end() if m else 0
    return html_text[:j] + EARLY + html_text[j:]


# ================================================================================================ L: long context
CITIES = ["札幌", "仙台", "東京", "横浜", "名古屋", "大阪", "神戸", "広島", "福岡", "那覇"]
ITEMS = ["ねじ", "ケーブル", "電池", "工具箱", "梱包材", "センサー", "モーター", "基板", "ラベル", "手袋"]
PEOPLE = ["佐藤", "鈴木", "高橋", "田中", "伊藤", "渡辺", "山本", "中村", "小林", "加藤"]
FILLER = ["棚卸しは毎週金曜日に行う。", "入荷予定は来週に変更された。", "破損品は返品処理済み。",
          "The count was double-checked by the night shift.", "在庫の偏りについて本部へ報告済み。",
          "Next audit is planned for the end of the quarter.", "配送業者との契約は自動更新される。"]
PROJECTS = ["青葉", "白鷺", "疾風", "琥珀", "雷鳥", "若竹", "朧月", "紅葉"]
WORDS = ["ひまわり三号", "星屑の鍵", "北斗七番", "銀河鉄道", "月見団子", "珊瑚礁", "桜吹雪", "雪解け水"]


def long_doc(chars, seed):
    rnd = random.Random(seed)
    lines = []
    while sum(len(x) + 1 for x in lines) < chars:
        i = len(lines)
        lines.append("記録%05d: %s支店の%sの在庫は%d個、担当は%s。%s" % (
            i, rnd.choice(CITIES), rnd.choice(ITEMS), rnd.randint(1, 999), rnd.choice(PEOPLE), rnd.choice(FILLER)))
    picks = rnd.sample(range(len(PROJECTS)), 5)
    facts = {}
    for k, depth in zip(picks, (0.05, 0.25, 0.5, 0.75, 0.95)):
        pos = max(1, int(len(lines) * depth))
        old = WORDS[(k + 3) % len(WORDS)]
        lines.insert(pos, "【重要】%s計画の合言葉は「%s」です（旧合言葉の「%s」は廃止）。" % (PROJECTS[k], WORDS[k], old))
        facts[PROJECTS[k]] = (WORDS[k], old)
    return "\n".join(lines), facts


# characters; Japanese here is ~0.64 tokens per character (measured 2026-10-13), so 400K characters is ~254K tokens.
# A level the context cannot hold is skipped as over_context (from the first answer's real token count).
LONG_LEVELS = [6000, 12000, 24000, 40000, 56000, 90000, 120000, 160000, 240000, 320000, 400000]


def stream_chat(a, messages, max_tokens, effort, timeout):
    payload = {"model": a.model, "messages": messages, "stream": True, "max_tokens": max_tokens, "temperature": 0.2,
               "stream_options": {"include_usage": True}}
    if effort:
        payload["reasoning_effort"] = effort
    req = urllib.request.Request(a.url.rstrip("/") + "/v1/chat/completions", data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    first = None
    content, reasoning, usage = [], [], {}
    with NOPROXY.open(req, timeout=timeout) as r:
        for raw in r:
            line = raw.decode("utf-8", "replace").strip()
            if not line.startswith("data: ") or line == "data: [DONE]":
                continue
            j = json.loads(line[6:])
            if j.get("usage"):
                usage = j["usage"]
            for ch in j.get("choices") or []:
                d = ch.get("delta") or {}
                if (d.get("content") or d.get("reasoning_content")) and first is None:
                    first = time.time() - t0
                content.append(d.get("content") or "")
                reasoning.append(d.get("reasoning_content") or "")
    return "".join(content), "".join(reasoning), usage, first, time.time() - t0


def run_long(a, log, deadline):
    rows = []
    ratio = None                                   # tokens per character, from the first answer's usage
    for chars in LONG_LEVELS:
        tid = "L_%dk" % (chars // 1000)
        if time.time() > deadline:
            rows.append({"task": tid, "chars": chars, "error": "deadline"})
            continue
        if ratio and chars * ratio > a.ctx - 2048:
            rows.append({"task": tid, "chars": chars, "est_tokens": int(chars * ratio), "error": "over_context",
                         "score": 0, "max": 5})
            continue
        doc, facts = long_doc(chars, seed=chars)
        q = ("上の文書には【重要】と書かれた行が5つあります。それぞれの計画名と、現在の合言葉（廃止された旧合言葉ではない方）を、"
             "1行に1つ「計画名: 合言葉」の形で答えてください。")
        msgs = [{"role": "system", "content": "あなたは文書を正確に読むアシスタントです。文書に書かれていることだけで答えてください。"},
                {"role": "user", "content": doc + "\n\n---\n" + q}]
        print("[%s] start (%d chars)" % (tid, len(doc)), flush=True)
        row = {"task": tid, "chars": len(doc), "max": 5}
        try:
            content, reasoning, usage, ttft, total = stream_chat(a, msgs, 4096, a.long_effort,   # 250K tokens take minutes
                                                                 max(60, min(3600, deadline - time.time())))
            pt = usage.get("prompt_tokens")
            if pt:
                ratio = pt / len(doc)
            good = sum(1 for p, (w, old) in facts.items() if re.search(re.escape(p) + r"[^\n]{0,40}" + re.escape(w), content))
            wrong = sum(1 for p, (w, old) in facts.items() if old in content)
            row.update({"score": good, "decoys": wrong, "prompt_tokens": pt, "completion_tokens": usage.get("completion_tokens"),
                        "ttft_s": round(ttft or 0, 1), "seconds": round(total, 1),
                        "prefill_tok_s": round(pt / ttft, 1) if pt and ttft else None, "answer": content[-600:]})
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")[:300]
            row.update({"score": 0, "error": ("over_context: " if "context" in body else "http %d: " % e.code) + body})
        except Exception as e:
            row.update({"score": 0, "error": "llm_error: %r" % e})
        log.write(json.dumps({"long": row}, ensure_ascii=False) + "\n")
        log.flush()
        print("[%s] %s/5 %s" % (tid, row.get("score"), row.get("error", "")), flush=True)
        rows.append(row)
    return rows


# ================================================================================================ B: multi-file
def setup_b1(w):
    wr(w, "shop/__init__.py", "")
    wr(w, "shop/pricing.py", "TAX = 0.1\n\n\ndef calc_total(prices, tax=TAX):\n    \"\"\"Sum of prices with tax, rounded to yen.\"\"\"\n    return round(sum(prices) * (1 + tax))\n")
    wr(w, "shop/cart.py", "from shop.pricing import calc_total\n\n\nclass Cart:\n    def __init__(self):\n        self.items = []\n\n    def add(self, name, price):\n        self.items.append((name, price))\n\n    def total(self):\n        return calc_total([p for _, p in self.items])\n")
    wr(w, "shop/report.py", "from shop import pricing\n\n\ndef line(prices):\n    # uses calc_total for the summary line\n    return 'total: %d' % pricing.calc_total(prices, tax=0)\n")
    wr(w, "shop/api.py", "from shop.pricing import calc_total as _total\n\n\ndef handle(req):\n    return {'total': _total(req['prices'])}\n")
    wr(w, "tests/__init__.py", "")
    wr(w, "tests/test_shop.py", "import unittest\nfrom shop.pricing import compute_total\nfrom shop.cart import Cart\nfrom shop import report, api\n\n\nclass T(unittest.TestCase):\n    def test_total(self):\n        self.assertEqual(compute_total([100, 200]), 330)\n\n    def test_cart(self):\n        c = Cart(); c.add('a', 1000)\n        self.assertEqual(c.total(), 1100)\n\n    def test_report(self):\n        self.assertEqual(report.line([10, 20]), 'total: 30')\n\n    def test_api(self):\n        self.assertEqual(api.handle({'prices': [50]}), {'total': 55})\n")


def grade_b1(w):
    ok, total, out = unittest_counts(w)
    left = [f for f in glob.glob(os.path.join(w, "shop", "*.py")) if "calc_total" in open(f, encoding="utf-8", errors="replace").read()]
    score = ok + (1 if not left else 0)
    return score, 5, "tests %d/%d, old name left in: %s" % (ok, total, [os.path.basename(x) for x in left] or "none")


PROMPT_B1 = ("shop パッケージの関数 calc_total を compute_total に改名してください。定義だけでなく、すべての呼び出し・import・"
             "コメント中の名前も直すこと。tests/ フォルダのファイルは変更しないこと（テストは新しい名前で書かれています）。")


def setup_b2(w):
    wr(w, "lib/__init__.py", "")
    wr(w, "lib/paging.py", "def page(items, n, size=10):\n    \"\"\"Page n (1-based) of items.\"\"\"\n    start = n * size\n    return items[start:start + size]\n\n\ndef pages(count, size=10):\n    return count // size\n")
    wr(w, "lib/money.py", "def discount(price, percent):\n    \"\"\"Price after a percent discount, rounded half up to whole yen.\"\"\"\n    return int(price * (100 - percent) / 100)\n\n\ndef split(total, people):\n    \"\"\"Split a bill: the first ones pay the extra yen.\"\"\"\n    base = total // people\n    return [base] * people\n")
    wr(w, "lib/text.py", "def slug(title):\n    \"\"\"'Hello World!' -> 'hello-world'.\"\"\"\n    return title.lower().replace(' ', '-')\n")
    wr(w, "tests/__init__.py", "")
    wr(w, "tests/test_lib.py", "import unittest\nfrom lib import paging, money, text\n\n\nclass Paging(unittest.TestCase):\n    def test_first_page(self):\n        self.assertEqual(paging.page(list(range(25)), 1), list(range(10)))\n\n    def test_last_page(self):\n        self.assertEqual(paging.page(list(range(25)), 3), [20, 21, 22, 23, 24])\n\n    def test_pages(self):\n        self.assertEqual(paging.pages(25), 3)\n        self.assertEqual(paging.pages(20), 2)\n        self.assertEqual(paging.pages(0), 0)\n\n\nclass Money(unittest.TestCase):\n    def test_discount_round(self):\n        self.assertEqual(money.discount(999, 15), 849)\n        self.assertEqual(money.discount(105, 10), 95)\n\n    def test_split(self):\n        self.assertEqual(money.split(100, 3), [34, 33, 33])\n        self.assertEqual(sum(money.split(1001, 4)), 1001)\n\n\nclass Text(unittest.TestCase):\n    def test_slug(self):\n        self.assertEqual(text.slug('Hello World!'), 'hello-world')\n        self.assertEqual(text.slug('  A  B  '), 'a-b')\n")


def grade_b2(w):
    ok, total, out = unittest_counts(w)
    tampered = sha(w, "tests/test_lib.py") != B2_TEST_HASH[0]
    return (0 if tampered else ok), 6, "tests %d/%d%s" % (ok, total, " (tests were changed: 0)" if tampered else "")


B2_TEST_HASH = [None]
PROMPT_B2 = ("lib/ のコードにバグがあり、tests/test_lib.py のテストが失敗します。lib/ 側を直して、すべてのテストが通るようにしてください。"
             "テストファイルは変更しないこと。各関数の docstring とテストが仕様です。")

B3_FILES = {"inbox/report_q1.pdf": "docs", "inbox/minutes.docx": "docs", "inbox/readme.txt": "docs", "inbox/notes.md": "docs",
            "inbox/logo.png": "images", "inbox/photo_01.jpg": "images", "inbox/banner.gif": "images", "inbox/icon.svg": "images",
            "inbox/sales.csv": "data", "inbox/users.json": "data", "inbox/metrics.xlsx": "data",
            "inbox/main.py": "code", "inbox/app.js": "code", "inbox/style.css": "code", "inbox/build.sh": "code"}


def setup_b3(w):
    for rel in B3_FILES:
        wr(w, rel, "dummy content of %s\n" % rel)


def grade_b3(w):
    good = sum(1 for rel, d in B3_FILES.items() if rd(w, "%s/%s" % (d, rel.split("/")[1])) is not None)
    idx = rd(w, "index.md") or ""
    listed = sum(1 for rel in B3_FILES if rel.split("/")[1] in idx)
    left = len(glob.glob(os.path.join(w, "inbox", "*")))
    score = good + (2 if listed == len(B3_FILES) else 1 if listed >= 10 else 0)
    return score, len(B3_FILES) + 2, "placed %d/%d, index lists %d, left in inbox %d" % (good, len(B3_FILES), listed, left)


PROMPT_B3 = ("inbox/ にある全ファイルを種類別に移動してください: 文書(.pdf .docx .txt .md)は docs/、画像(.png .jpg .gif .svg)は images/、"
             "データ(.csv .json .xlsx)は data/、コード(.py .js .css .sh)は code/。ファイル名は変えないこと。"
             "最後に、移動先フォルダごとにファイル名を列挙した index.md をルートに作ってください。")

B4_CATS = ["食品", "日用品", "家電", "衣料", "書籍"]


def b4_data():
    rnd = random.Random(44)
    months = {}
    for m in range(1, 13):
        rows = []
        for d in range(1, rnd.randint(8, 14)):
            rows.append(("2026-%02d-%02d" % (m, d), rnd.choice(B4_CATS), rnd.randint(100, 50000)))
        months["sales/2026-%02d.csv" % m] = rows
    return months


def setup_b4(w):
    for rel, rows in b4_data().items():
        wr(w, rel, "date,category,amount\n" + "".join("%s,%s,%d\n" % r for r in rows))


def grade_b4(w):
    tot = {}
    for rows in b4_data().values():
        for _, c, v in rows:
            tot[c] = tot.get(c, 0) + v
    want = sorted(tot.items(), key=lambda x: -x[1])
    s = (rd(w, "summary.csv") or "").replace("\r\n", "\n").strip().splitlines()
    if not s:
        return 0, 4, "no summary.csv"
    head = s[0].replace(" ", "") == "category,total"
    got = []
    for line in s[1:]:
        p = [x.strip() for x in line.split(",")]
        if len(p) >= 2 and p[0] in tot:
            try:
                got.append((p[0], int(float(p[1]))))
            except ValueError:
                pass
    vals = sum(1 for c, v in got if tot.get(c) == v) == len(tot) and len(got) == len(tot)
    order = got == want
    grand = any(("合計" in line or "total" in line.split(",")[0].lower()) and str(sum(tot.values())) in line for line in s[1:])
    score = head + vals * 2 + order + 0 * grand
    return score, 4, "header %s, totals %s, order %s (want %s)" % (head, vals, order, want[:2])


PROMPT_B4 = ("sales/ フォルダに月別の売上 CSV が12個あります（列: date,category,amount）。全期間のカテゴリ別合計を計算し、"
             "summary.csv に書いてください。1行目はヘッダー category,total、2行目以降は合計の大きい順。数値は整数で、カンマ区切り。")


def setup_b5(w):
    wr(w, "config/app.ini", "[server]\nhost = 127.0.0.1\nport = 8080\ntimeout = 30\n\n[cache]\nport = 6379\n")
    wr(w, "config/db.json", '{\n  "db": {"host": "db.local", "port": 5432},\n  "api": {"url": "http://127.0.0.1:8080/v1", "retries": 3}\n}\n')
    wr(w, "config/deploy.yaml", "service:\n  name: web\n  port: 8080\n  replicas: 2\nhealth:\n  path: /health\n  port: 8080\n")


def grade_b5(w):
    want = {"config/app.ini": "[server]\nhost = 0.0.0.0\nport = 9090\ntimeout = 30\n\n[cache]\nport = 6379\n",
            "config/db.json": None,
            "config/deploy.yaml": "service:\n  name: web\n  port: 9090\n  replicas: 2\nhealth:\n  path: /health\n  port: 9090\n"}
    score, notes = 0, []
    for rel in ("config/app.ini", "config/deploy.yaml"):
        got = (rd(w, rel) or "").replace("\r\n", "\n").rstrip("\n")
        ok = got == want[rel].rstrip("\n")
        score += ok
        notes.append("%s %s" % (rel.split("/")[1], "ok" if ok else "differs"))
    try:
        j = json.loads(rd(w, "config/db.json") or "")
        ok = j == {"db": {"host": "db.local", "port": 5432}, "api": {"url": "http://127.0.0.1:9090/v1", "retries": 3}}
    except ValueError:
        ok = False
    score += ok
    notes.append("db.json %s" % ("ok" if ok else "differs"))
    return score, 3, ", ".join(notes)


PROMPT_B5 = ("config/ の3ファイル（app.ini, db.json, deploy.yaml）で、Webサーバーのポート 8080 をすべて 9090 に変えてください"
             "（URL の中のポートも含む）。さらに app.ini の [server] の host を 0.0.0.0 にしてください。"
             "それ以外（キャッシュやDBのポート、他の行、書式）は一切変えないこと。")

B6_DOCS = 8
B6_TANAKA = [("API仕様書のレビュー", "10/14"), ("ログ収集基盤の見積もり", "10/18"), ("顧客Aへの返信", "10/21"),
             ("負荷試験の計画", "10/25"), ("新人向け手順書の更新", "10/30"), ("年末停止の告知文", "11/02")]


def setup_b6(w):
    rnd = random.Random(66)
    slots = rnd.sample(range(B6_DOCS * 4), len(B6_TANAKA))
    k = 0
    for i in range(B6_DOCS):
        body = ["# 定例会議 第%d回 議事録" % (i + 1), "", "## 議論"]
        for _ in range(12):
            body.append("- %sが%sについて説明した。%s" % (rnd.choice(PEOPLE), rnd.choice(ITEMS), rnd.choice(FILLER)))
        body += ["", "## アクションアイテム"]
        for j in range(4):
            slot = i * 4 + j
            if slot in slots:
                t, d = B6_TANAKA[slots.index(slot)]
                body.append("- [ ] 田中: %s（期限 %s）" % (t, d))
            else:
                who = rnd.choice([p for p in PEOPLE if p != "田中"])
                body.append("- [ ] %s: %sの%s（期限 %d/%02d）" % (who, rnd.choice(CITIES), rnd.choice(["調査", "発注", "報告", "点検"]),
                                                             rnd.randint(10, 12), rnd.randint(1, 28)))
        body += ["", "## 雑談", "- 田中さんは週末に釣りへ行った（アクションではない）。"]
        wr(w, "minutes/meeting_%02d.md" % (i + 1), "\n".join(body) + "\n")
        k += 1


def grade_b6(w):
    s = rd(w, "tanaka.md") or ""
    found = sum(1 for t, d in B6_TANAKA if t in s and d in s)
    extra = len(re.findall(r"(調査|発注|報告|点検)（期限", s))
    score = max(0, found - min(extra, found))
    return score, len(B6_TANAKA), "found %d/%d, wrong items %d, mentions fishing %s" % (found, len(B6_TANAKA), extra, "釣り" in s)


PROMPT_B6 = ("minutes/ フォルダの議事録（8ファイル）をすべて読み、田中さんが担当するアクションアイテムだけを集めて、"
             "tanaka.md に「- 内容（期限 M/DD）」の形で期限の早い順に箇条書きしてください。他の人の担当や雑談は含めないこと。")


# ================================================================================================ C: build things
GAME_HARNESS = r"""
(function(){
  var R = {errors: window.__benchErrors || [], checks: {}, notes: []};
  function key(type, k, code, kc){
    var ev = new KeyboardEvent(type, {key: k, code: code, bubbles: true, cancelable: true});
    try { Object.defineProperty(ev, 'keyCode', {get: function(){ return kc; }});
          Object.defineProperty(ev, 'which', {get: function(){ return kc; }}); } catch (e) {}
    document.dispatchEvent(ev);
  }
  function gs(){ try { return JSON.parse(JSON.stringify(window.gameState)); } catch (e) { return null; } }
  function at(ms, f){ setTimeout(function(){ try { f(); } catch (e) { R.notes.push('harness: ' + e); } }, ms); }
  var s0, p0, b1;
  at(500, function(){
    s0 = gs();
    R.checks.canvas = !!document.querySelector('canvas');
    R.checks.gameState = !!(s0 && 'score' in s0 && 'lives' in s0 && 'state' in s0);
    R.checks.ready_at_start = !!(s0 && s0.state === 'ready');
    R.checks.three_lives = !!(s0 && s0.lives === 3);
    R.checks.exposes_ball_paddle = !!(s0 && s0.ball && s0.paddle && 'x' in s0.ball && 'x' in s0.paddle);
    p0 = s0 && s0.paddle ? s0.paddle.x : null;
    key('keydown', 'ArrowLeft', 'ArrowLeft', 37);
  });
  at(900, function(){ key('keyup', 'ArrowLeft', 'ArrowLeft', 37); var s = gs();
    R.checks.left_moves_paddle = !!(s && s.paddle && p0 !== null && s.paddle.x < p0);
    p0 = s && s.paddle ? s.paddle.x : null; key('keydown', 'ArrowRight', 'ArrowRight', 39); });
  at(1300, function(){ key('keyup', 'ArrowRight', 'ArrowRight', 39); var s = gs();
    R.checks.right_moves_paddle = !!(s && s.paddle && p0 !== null && s.paddle.x > p0);
    key('keydown', ' ', 'Space', 32); });
  at(1350, function(){ key('keyup', ' ', 'Space', 32); });
  at(1600, function(){ var s = gs(); R.checks.space_starts = !!(s && s.state === 'playing'); b1 = s && s.ball ? [s.ball.x, s.ball.y] : null; });
  at(2100, function(){ var s = gs();
    R.checks.ball_moves = !!(s && s.ball && b1 && (s.ball.x !== b1[0] || s.ball.y !== b1[1])); });
  at(30000, function(){ var s = gs();   // the paddle never moves: the ball must fall at least once in 28 s
    R.checks.lives_decrease_or_over = !!(s && (s.lives < 3 || s.state === 'gameover'));
    R.checks.score_is_number = !!(s && typeof s.score === 'number');
    R.after30s = s ? {score: s.score, lives: s.lives, state: s.state} : null;
    key('keydown', 'r', 'KeyR', 82); });
  at(30050, function(){ key('keyup', 'r', 'KeyR', 82); });
  at(30400, function(){ var s = gs();
    R.checks.r_restarts = !!(s && s.state === 'ready' && s.lives === 3 && s.score === 0);
    R.checks.no_js_errors = R.errors.length === 0;
    var p = document.createElement('pre'); p.id = '__bench'; p.textContent = JSON.stringify(R); document.body.appendChild(p); });
})();
"""


def grade_c1(w, keep):
    s = rd(w, "game/index.html") or ""
    static = len(s) > 1500 and "<canvas" in s.lower() and "</html>" in s.lower()
    if not s:
        return 0, 14, "no game/index.html"
    test = os.path.join(w, "game", "__bench_test.html")
    with open(test, "w", encoding="utf-8") as f:
        f.write(inject(s, GAME_HARNESS))
    prof = tempfile.mkdtemp(prefix="nb_prof_")
    res, err = browser_run(test, prof, 45000)
    shutil.rmtree(prof, ignore_errors=True)
    if keep:
        shutil.copy(os.path.join(w, "game", "index.html"), keep)
    if res is None:
        return int(static), 14, "static %s; browser: %s" % (static, err)
    checks = res.get("checks", {})
    passed = sum(1 for v in checks.values() if v)
    return int(static) + passed, 14, "static %s, play %d/%d %s errors=%s" % (
        static, passed, len(checks), [k for k, v in checks.items() if not v], res.get("errors", [])[:2])


PROMPT_C1 = agent.GAME_SPEC


TODO_HARNESS_1 = r"""
(function(){
  var R = {errors: window.__benchErrors || [], checks: {}, notes: []};
  function $(s){ return document.querySelector(s); }
  function add(t, enter){ var i = $('#new-todo'); if (!i) return; i.value = t; i.dispatchEvent(new Event('input', {bubbles: true}));
    if (enter) { var ev = new KeyboardEvent('keydown', {key: 'Enter', code: 'Enter', bubbles: true});
      try { Object.defineProperty(ev, 'keyCode', {get: function(){ return 13; }}); } catch (e) {}
      i.dispatchEvent(ev); }
    else { var b = $('#add-btn'); if (b) b.click(); } }
  function lis(){ return document.querySelectorAll('#todo-list li'); }
  setTimeout(function(){ try {
    R.checks.has_elements = !!($('#new-todo') && $('#add-btn') && $('#todo-list') && $('#count'));
    try { localStorage.clear(); } catch (e) {}
    add('牛乳'); add('卵'); add('パン', true);
    R.checks.add_three = lis().length === 3;
    R.checks.enter_adds = lis().length === 3 && /パン/.test(lis()[2].textContent);
    add('   ');
    R.checks.ignores_blank = lis().length === 3;
    var cb = lis()[1] && lis()[1].querySelector('input[type=checkbox]'); if (cb) cb.click();
    R.checks.toggle_done = !!(lis()[1] && lis()[1].classList.contains('done'));
    R.checks.count_left = /2/.test(($('#count') || {}).textContent || '');
    var del = lis()[0] && lis()[0].querySelector('.delete'); if (del) del.click();
    R.checks.delete_works = lis().length === 2 && !/牛乳/.test(($('#todo-list') || {}).textContent || '');
    var dump = ''; for (var k = 0; k < localStorage.length; k++) dump += localStorage.getItem(localStorage.key(k));
    R.checks.saved_to_localstorage = /パン/.test(dump) && !/牛乳/.test(dump);
  } catch (e) { R.notes.push('harness: ' + e); }
  R.checks.no_js_errors = R.errors.length === 0;
  var p = document.createElement('pre'); p.id = '__bench'; p.textContent = JSON.stringify(R); document.body.appendChild(p);
  }, 800);
})();
"""
TODO_HARNESS_2 = r"""
(function(){
  setTimeout(function(){
    var R = {checks: {}}; var l = document.querySelectorAll('#todo-list li');
    R.checks.survives_reload = l.length === 2 && /パン/.test(document.querySelector('#todo-list').textContent)
                                && !!(l[0] && l[0].classList.contains('done'));
    var p = document.createElement('pre'); p.id = '__bench'; p.textContent = JSON.stringify(R); document.body.appendChild(p);
  }, 800);
})();
"""


def grade_c2(w, keep):
    files = [rd(w, "todo/" + f) for f in ("index.html", "style.css", "app.js")]
    static = sum(1 for x in files if x and len(x) > 100)
    if not files[0]:
        return static, 13, "no todo/index.html"
    prof = tempfile.mkdtemp(prefix="nb_prof_")
    notes, passed, n = [], 0, 0
    for i, h in enumerate((TODO_HARNESS_1, TODO_HARNESS_2)):
        page = os.path.join(w, "todo", "__bench_test.html")       # same file name both runs: same localStorage
        with open(page, "w", encoding="utf-8") as f:
            f.write(inject(files[0], h))
        res, err = browser_run(page, prof, 5000)
        if res is None:
            notes.append("run %d: %s" % (i + 1, err))
            n += 9 if i == 0 else 1
            continue
        c = res.get("checks", {})
        n += len(c)
        passed += sum(1 for v in c.values() if v)
        notes.append("run %d failed: %s %s" % (i + 1, [k for k, v in c.items() if not v], res.get("errors", [])[:2]))
    shutil.rmtree(prof, ignore_errors=True)
    if keep:
        shutil.copytree(os.path.join(w, "todo"), keep, dirs_exist_ok=True)
    return static + passed, 13, "files %d/3, checks %d/%d; %s" % (static, passed, n, "; ".join(notes))


PROMPT_C2 = ("ブラウザで動く TODO アプリを todo/ フォルダに index.html, style.css, app.js の3ファイルに分けて作ってください。外部ライブラリは使わないこと。\n"
             "必須仕様（自動テストがこの ID とクラス名で操作します）:\n"
             "1. 入力欄 id=\"new-todo\"、追加ボタン id=\"add-btn\"、一覧 ul id=\"todo-list\"、残り件数表示 id=\"count\"\n"
             "2. ボタンのクリックでも、入力欄で Enter キーでも追加できる。空白だけの入力は追加しない\n"
             "3. 各項目は li で、中に完了切り替えの input[type=checkbox] と削除ボタン（class=\"delete\"）を持つ\n"
             "4. 完了した li には class=\"done\" を付け、取り消し線で表示する\n"
             "5. #count には未完了の件数を数字で表示する（例: 残り 2 件）\n"
             "6. 一覧と完了状態を localStorage に保存し、ページを開き直しても復元する\n"
             "書き終えたら3ファイルを読み返し、仕様漏れがあれば直してください。")


C3_INPUTS = ["the cat and the dog\nThe Cat sat\n\nend",
             "a a a b b c\nd e f g\nA B",
             "Hello, world! hello WORLD\nfoo bar foo\nbaz"]


def c3_expected(text):
    words = [x.lower() for x in text.split()]
    cnt = {}
    for x in words:
        cnt[x] = cnt.get(x, 0) + 1
    top = sorted(cnt.items(), key=lambda x: (-x[1], x[0]))[:5]
    return {"lines": len(text.splitlines()), "words": len(words), "chars": len(text), "top": [[k, v] for k, v in top]}


def grade_c3(w, keep):
    if rd(w, "wordstat.py") is None:
        return 0, 6, "no wordstat.py"
    good = 0
    for i, t in enumerate(C3_INPUTS):
        p = os.path.join(w, "__hidden_%d.txt" % i)
        with open(p, "w", encoding="utf-8", newline="") as f:
            f.write(t)
        code, out, err = run_py(w, ["wordstat.py", p], timeout=30)
        try:
            good += json.loads(out) == c3_expected(t)
        except ValueError:
            pass
    tests = glob.glob(os.path.join(w, "tests", "test_*.py"))
    ok, total, _ = unittest_counts(w) if tests else (0, 0, "")
    own = 2 if tests and total >= 3 and ok == total else 1 if tests and ok else 0
    code, out, err = run_py(w, ["wordstat.py"], timeout=30)
    usage = code != 0 and ("usage" in (out + err).lower() or "使い方" in (out + err))
    if keep:
        for f in ["wordstat.py"] + [os.path.relpath(t, w) for t in tests]:
            os.makedirs(os.path.dirname(os.path.join(keep, f)) or keep, exist_ok=True)
            shutil.copy(os.path.join(w, f), os.path.join(keep, f))
    return good + own + usage, 6, "hidden inputs %d/3, own tests %d/%d, usage message %s" % (good, ok, total, usage)


PROMPT_C3 = ("Python の標準ライブラリだけで、テキストファイルの統計を出す CLI ツール wordstat.py を作ってください。\n"
             "仕様: `python wordstat.py <ファイル>` で、UTF-8 のファイルを読み、次の JSON を1行で標準出力に出す。\n"
             "  {\"lines\": 行数(splitlines の数), \"words\": 単語数(空白で区切る), \"chars\": 文字数(ファイル全体の len),\n"
             "   \"top\": [[単語, 回数], ...] 小文字にそろえた単語の出現回数の多い順に最大5個。回数が同じなら単語の辞書順]\n"
             "引数がないときは使い方(usage)を表示して終了コード 1 で終わる。\n"
             "さらに tests/test_wordstat.py に unittest のテストを3つ以上書くこと（tests/__init__.py も作る）。")


def grade_c4(w, keep):
    s = rd(w, "docs/design.md") or ""
    if not s:
        return 0, 8, "no docs/design.md"
    heads = re.findall(r"^#{1,3}\s*(.+)$", s, re.M)
    need = ["目的", "構成", "手順", "評価", "リスク", "まとめ"]
    have = sum(1 for k in need if any(k in h for h in heads))
    jp = len(re.findall(r"[\u3040-\u30ff\u4e00-\u9fff]", s))
    table = bool(re.search(r"^\|.+\|\s*$\n^\|[\s:|-]+\|\s*$", s, re.M))
    code = s.count("```") >= 2
    score = min(have, 4) + (jp >= 2500) + table + code + (len(heads) >= 8)
    if keep:
        shutil.copy(os.path.join(w, "docs", "design.md"), keep)
    return score, 8, "sections %d/6, japanese chars %d, table %s, code block %s, headings %d" % (have, jp, table, code, len(heads))


PROMPT_C4 = ("「ローカルLLMの夜間ベンチマーク」の設計書を docs/design.md に Markdown で書いてください。\n"
             "必須: 見出しとして「目的」「構成」「手順」「評価方法」「リスクと対策」「まとめ」を含める（小見出しも使う）。"
             "評価項目を Markdown の表で1つ以上示す。実行コマンドの例をコードブックで1つ以上示す。日本語で2500文字以上。")


TASKS = [  # id, group, prompt, setup, grade(w) or grade(w, keep), max steps, minutes
    ("B1_rename", "B", PROMPT_B1, setup_b1, grade_b1, 25, 20),
    ("B2_bugfix", "B", PROMPT_B2, setup_b2, grade_b2, 30, 25),
    ("B3_organize", "B", PROMPT_B3, setup_b3, grade_b3, 40, 20),
    ("B4_aggregate", "B", PROMPT_B4, setup_b4, grade_b4, 30, 20),
    ("B5_configs", "B", PROMPT_B5, setup_b5, grade_b5, 20, 15),
    ("B6_crossdoc", "B", PROMPT_B6, setup_b6, grade_b6, 25, 20),
    ("C1_breakout", "C", PROMPT_C1, None, grade_c1, 30, 45),
    ("C2_todo_app", "C", PROMPT_C2, None, grade_c2, 30, 45),
    ("C3_cli_tool", "C", PROMPT_C3, None, grade_c3, 25, 30),
    ("C4_design_doc", "C", PROMPT_C4, None, grade_c4, 15, 25),
]


def grade(task, w, keepdir):
    tid, g = task[0], task[4]
    if task[1] == "C":
        keep = os.path.join(keepdir, tid)
        if tid in ("C1_breakout", "C4_design_doc"):
            os.makedirs(keepdir, exist_ok=True)
            keep = os.path.join(keepdir, tid + (".html" if tid == "C1_breakout" else ".md"))
        return g(w, keep)
    return g(w)


# ================================================================================================ the agent loop
def chat_tools(a, msgs, timeout):
    payload = {"model": a.model, "messages": msgs, "tools": agent.TOOL_SCHEMAS, "tool_choice": "auto",
               "temperature": 0.2, "max_tokens": a.max_tokens}
    if a.effort:
        payload["reasoning_effort"] = a.effort
    req = urllib.request.Request(a.url.rstrip("/") + "/v1/chat/completions", data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    with NOPROXY.open(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def run_agent(a, task, w, log, deadline):
    tid, _, prompt, _, _, max_steps, minutes = task
    agent.SANDBOX = w
    end = min(deadline, time.time() + minutes * 60)
    msgs = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}]
    st = {"steps": 0, "tool_calls": 0, "completion_tokens": 0, "prompt_tokens_max": 0, "llm_seconds": 0.0, "error": ""}
    t0 = time.time()
    for step in range(1, max_steps + 1):
        st["steps"] = step
        if time.time() > end:
            st["error"] = "time_limit" if end < deadline else "deadline"
            break
        t1 = time.time()
        try:
            resp = chat_tools(a, msgs, max(30, min(1800, int(end - time.time()))))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")[:300]
            st["error"] = ("context_overflow: " if "context" in body else "http %d: " % e.code) + body
            break
        except Exception as e:
            st["error"] = "llm_error: %r" % e
            break
        st["llm_seconds"] += time.time() - t1
        u = resp.get("usage") or {}
        st["completion_tokens"] += u.get("completion_tokens", 0)
        st["prompt_tokens_max"] = max(st["prompt_tokens_max"], u.get("prompt_tokens", 0))
        ch = resp["choices"][0]
        m = ch["message"]
        calls = m.get("tool_calls") or []
        if not calls and ch.get("finish_reason") == "length":
            log.write(json.dumps({"task": tid, "step": step, "event": "length_no_action"}) + "\n")
            msgs.append({"role": "user", "content": "考えすぎです。推論は短く切り上げて、今すぐ必要なツールを1つ呼んでください。"})
            continue
        msgs.append({"role": "assistant", "content": m.get("content") or "", **({"tool_calls": calls} if calls else {})})
        log.write(json.dumps({"task": tid, "step": step, "content": (m.get("content") or "")[:2000], "tool_calls": calls,
                              "reasoning_len": len(m.get("reasoning_content") or "")}, ensure_ascii=False) + "\n")
        if not calls:
            break
        for c in calls:
            st["tool_calls"] += 1
            name = c["function"]["name"]
            try:
                args = c["function"].get("arguments") or "{}"
                args = json.loads(args) if isinstance(args, str) else args
                out = agent.TOOLS[name](**args)
            except Exception as e:
                out = "ERROR: %r" % e
            log.write(json.dumps({"task": tid, "tool": name, "result": out[:1000]}, ensure_ascii=False) + "\n")
            msgs.append({"role": "tool", "tool_call_id": c.get("id", ""), "content": out})
    else:
        st["error"] = "max_steps"
    log.flush()
    st["seconds"] = round(time.time() - t0, 1)
    st["tok_s"] = round(st["completion_tokens"] / st["llm_seconds"], 1) if st["llm_seconds"] else None
    st["llm_seconds"] = round(st["llm_seconds"], 1)
    return st


def cmd_run(a):
    os.makedirs(a.logdir, exist_ok=True)
    deadline = time.time() + (a.deadline or 10 ** 9)
    want = [x for x in a.tasks.split(",") if x]
    out_path = os.path.join(a.logdir, "results.json")
    res = {"name": a.name, "ctx": a.ctx, "effort": a.effort, "long_effort": a.long_effort, "started": time.strftime("%Y-%m-%d %H:%M"),
           "long": [], "tasks": []}

    def save():
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False, indent=1)
    with open(os.path.join(a.logdir, "transcript.jsonl"), "a", encoding="utf-8") as log:
        if not want or any(x.startswith("L") for x in want):
            res["long"] = run_long(a, log, deadline)
            save()
        for task in TASKS:
            if want and task[0] not in want and task[1] not in want:   # ids, or the groups B / C
                continue
            w = os.path.join(a.logdir, "work", task[0])
            shutil.rmtree(w, ignore_errors=True)
            os.makedirs(w)
            if task[3]:
                task[3](w)
            if task[0] == "B2_bugfix":
                B2_TEST_HASH[0] = sha(w, "tests/test_lib.py")
            row = {"task": task[0], "group": task[1]}
            if time.time() > deadline:
                row.update({"score": 0, "max": 0, "error": "deadline", "detail": "not run"})
            else:
                print("[%s] start" % task[0], flush=True)
                st = run_agent(a, task, w, log, deadline)
                try:
                    sc, mx, detail = grade(task, w, os.path.join(a.logdir, "artifacts"))
                except Exception as e:
                    sc, mx, detail = 0, 0, "grade_error: %r" % e
                row.update(st, score=sc, max=mx, detail=detail)
                print("[%s] %s/%s %s | %s" % (task[0], sc, mx, detail, st["error"]), flush=True)
            res["tasks"].append(row)
            save()
    res["finished"] = time.strftime("%Y-%m-%d %H:%M")
    save()


# ================================================================================================ report
def cmd_report(a):
    runs = []
    for p in sorted(glob.glob(os.path.join(a.root, "*", "results.json"))):
        with open(p, encoding="utf-8") as f:
            r = json.load(f)
        r["_dir"] = os.path.basename(os.path.dirname(p))
        runs.append(r)
    if not runs:
        sys.exit("no results under " + a.root)
    L = ["# 夜間ベンチ結果", "", "実行: %s〜" % runs[0].get("started", "?"), ""]
    L += ["## 総合", "", "| モデル | 文脈 | 長文 (見つけた事実) | 複数ファイル B | 完成度 C | 合計 | 平均 出力 tok/s |", "|---|---|---|---|---|---|---|"]
    rows_csv = []
    for r in runs:
        ran = [x for x in r["long"] if not str(x.get("error", "")).startswith(("over_context", "deadline"))]   # not in the total
        lg = sum(x.get("score", 0) or 0 for x in ran), sum(x.get("max", 5) for x in ran)
        b = [t for t in r["tasks"] if t["group"] == "B"]
        c = [t for t in r["tasks"] if t["group"] == "C"]
        bs, bm = sum(t["score"] for t in b), sum(t["max"] for t in b)
        cs, cm = sum(t["score"] for t in c), sum(t["max"] for t in c)
        speeds = [t["tok_s"] for t in r["tasks"] if t.get("tok_s")]
        sp = round(sum(speeds) / len(speeds), 1) if speeds else "-"
        other = [t for t in r["tasks"] if t["group"] not in ("B", "C")]       # e.g. the compaction test (K)
        tot = lg[0] + bs + cs + sum(t["score"] for t in other), lg[1] + bm + cm + sum(t["max"] for t in other)
        L.append("| %s | %s | %d/%d | %d/%d | %d/%d | **%d/%d** | %s |" % (r["name"], r["ctx"], lg[0], lg[1], bs, bm, cs, cm, tot[0], tot[1], sp))
        for x in r["long"]:
            rows_csv.append([r["name"], r["ctx"], x["task"], x.get("score", 0), x.get("max", 5), x.get("prompt_tokens", ""),
                             x.get("seconds", ""), "", x.get("error", "")])
        for t in r["tasks"]:
            rows_csv.append([r["name"], r["ctx"], t["task"], t["score"], t["max"], t.get("prompt_tokens_max", ""), t.get("seconds", ""),
                             t.get("tok_s", ""), t.get("error", "")])
    L += ["", "## 長文（どこまで読めるか）", "", "各段階で文書の 5%・25%・50%・75%・95% の位置に事実を1つずつ埋め、5つ全部答えられるかを見る。"
          "「文脈超過」の段階は総合の点数に含めない。", ""]
    L += ["| モデル | " + " | ".join("%dK字" % (c // 1000) for c in LONG_LEVELS) + " |", "|---|" + "---|" * len(LONG_LEVELS)]
    for r in runs:
        cells = []
        by = {x["task"]: x for x in r["long"]}
        for c in LONG_LEVELS:
            x = by.get("L_%dk" % (c // 1000), {})
            if x.get("error", "").startswith("over_context"):
                cells.append("文脈超過")
            elif x.get("error"):
                cells.append(x["error"][:12])
            elif x:
                cells.append("%s/5 (%stok, 初出力%ss)" % (x.get("score"), x.get("prompt_tokens") or "?", x.get("ttft_s")))
            else:
                cells.append("-")
        L.append("| %s | %s |" % (r["name"], " | ".join(cells)))
    L += ["", "## 課題ごと", ""]
    ids = [t[0] for t in TASKS]
    ids += [x["task"] for r in runs for x in r["tasks"] if x["task"] not in ids and not ids.count(x["task"])]
    ids = [x for x in dict.fromkeys(ids) if any(t["task"] == x for r in runs for t in r["tasks"])]   # only what ran
    L += ["| 課題 | " + " | ".join(r["name"] for r in runs) + " |", "|---|" + "---|" * len(runs)]
    for tid in ids:
        cells = []
        for r in runs:
            t = next((x for x in r["tasks"] if x["task"] == tid), None)
            cells.append("-" if not t else "%d/%d%s (%ss)" % (t["score"], t["max"], " ⚠" + t["error"][:16] if t.get("error") else "",
                                                             int(t.get("seconds") or 0)))
        L.append("| %s | %s |" % (tid, " | ".join(cells)))
    L += ["", "## 詳細", ""]
    for r in runs:
        L += ["### %s（文脈 %s、思考 %s）" % (r["name"], r["ctx"], r.get("effort")), ""]
        for t in r["tasks"]:
            L.append("- **%s** %d/%d: %s%s" % (t["task"], t["score"], t["max"], t.get("detail", ""),
                                               "（停止理由: %s）" % t["error"] if t.get("error") else ""))
        info = os.path.join(a.root, r["_dir"], "server-info.txt")
        if os.path.isfile(info):
            lines = [x.strip() for x in open(info, encoding="utf-8-sig", errors="replace") if x.strip()]
            L += ["", "起動ログ（RAM・VRAM）:", "```"] + lines[:8] + ["```"]
        L += ["", "成果物: `%s/artifacts/`、作業フォルダ: `%s/work/`" % (r["_dir"], r["_dir"]), ""]
    with open(os.path.join(a.root, "REPORT.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    with open(os.path.join(a.root, "summary.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["model", "ctx", "task", "score", "max", "prompt_tokens", "seconds", "tok_s", "error"])
        w.writerows(rows_csv)
    print("wrote", os.path.join(a.root, "REPORT.md"))


# ================================================================================================ config helper
def cmd_make_config(a):
    with open(a.src, encoding="utf-8-sig") as f:
        cfg = json.load(f)
    args = list(cfg["args"])

    def set_arg(flag, value=None, drop=False):
        if flag in args:
            i = args.index(flag)
            del args[i:i + (2 if i + 1 < len(args) and not args[i + 1].startswith("--") else 1)]
        if not drop:
            args.extend([flag] if value is None else [flag, str(value)])
    set_arg("--max-context", a.ctx)
    set_arg("--kv-resident", 32768, drop=a.ctx < 65536)   # from 64K: KV in RAM, 32K positions in VRAM (as setup.py)
    cfg["args"] = args
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=1)
    print("wrote %s (context %d)" % (a.out, a.ctx))


# ================================================================================================ selftest
REF_GAME = r"""<!doctype html><html><head><meta charset="utf-8"><title>Breakout</title></head><body>
<canvas id="c" width="480" height="320"></canvas>
<script>
const cv = document.getElementById('c'), g = cv.getContext('2d');
let keys = {}, bricks, score, lives, state, ball, paddle;
function reset() { score = 0; lives = 3; state = 'ready'; paddle = {x: 200, y: 300, w: 80};
  ball = {x: 240, y: 290, vx: 3, vy: -3}; bricks = [];
  for (let r = 0; r < 5; r++) for (let c = 0; c < 8; c++) bricks.push({x: 10 + c * 58, y: 20 + r * 18, alive: true}); }
function pub() { window.gameState = {score, lives, state, ball: {...ball}, paddle: {...paddle}}; }
document.addEventListener('keydown', e => { keys[e.key] = true;
  if (e.key === ' ' && state === 'ready') state = 'playing'; if (e.key === 'r' || e.key === 'R') reset(); pub(); });
document.addEventListener('keyup', e => { keys[e.key] = false; });
function step() {
  if (keys.ArrowLeft) paddle.x = Math.max(0, paddle.x - 6); if (keys.ArrowRight) paddle.x = Math.min(400, paddle.x + 6);
  if (state === 'ready') { ball.x = paddle.x + 40; ball.y = 290; }
  if (state === 'playing') { ball.x += ball.vx; ball.y += ball.vy;
    if (ball.x < 0 || ball.x > 480) ball.vx *= -1; if (ball.y < 0) ball.vy *= -1;
    if (ball.y > 295 && ball.x > paddle.x && ball.x < paddle.x + paddle.w && ball.vy > 0) ball.vy *= -1;
    for (const b of bricks) if (b.alive && ball.x > b.x && ball.x < b.x + 54 && ball.y > b.y && ball.y < b.y + 14) { b.alive = false; ball.vy *= -1; score += 10; }
    if (ball.y > 320) { lives--; state = lives > 0 ? 'ready' : 'gameover'; }
    if (bricks.every(b => !b.alive)) state = 'clear'; }
  g.clearRect(0, 0, 480, 320); g.fillRect(paddle.x, paddle.y, paddle.w, 8);
  for (const b of bricks) if (b.alive) g.fillRect(b.x, b.y, 54, 14);
  g.beginPath(); g.arc(ball.x, ball.y, 5, 0, 7); g.fill(); pub(); }
reset(); pub(); setInterval(step, 16);
/* padding so the static check sees a real file ............................................................ */
/* ......................................................................................................... */
/* ......................................................................................................... */
/* ......................................................................................................... */
/* ......................................................................................................... */
</script></body></html>
"""
REF_TODO_HTML = """<!doctype html><html><head><meta charset="utf-8"><title>TODO</title><link rel="stylesheet" href="style.css"></head>
<body><h1>TODO</h1><input id="new-todo" placeholder="やること"><button id="add-btn">追加</button>
<ul id="todo-list"></ul><p id="count"></p><script src="app.js"></script>
<!-- reference solution for the self-test: the graders must give it full marks ................................ -->
</body></html>
"""
REF_TODO_CSS = "body{font-family:sans-serif;margin:2em}li.done span{text-decoration:line-through;color:#888}\n" \
               "li{list-style:none;margin:.3em 0}.delete{margin-left:1em}#count{color:#555}\n/* reference */\n"
REF_TODO_JS = r"""const KEY = 'todos'; let todos = [];
try { todos = JSON.parse(localStorage.getItem(KEY)) || []; } catch (e) { todos = []; }
const $ = s => document.querySelector(s);
function save() { localStorage.setItem(KEY, JSON.stringify(todos)); }
function render() { const ul = $('#todo-list'); ul.innerHTML = '';
  todos.forEach((t, i) => { const li = document.createElement('li'); if (t.done) li.className = 'done';
    const cb = document.createElement('input'); cb.type = 'checkbox'; cb.checked = t.done;
    cb.onclick = () => { t.done = !t.done; save(); render(); };
    const sp = document.createElement('span'); sp.textContent = t.text;
    const del = document.createElement('button'); del.className = 'delete'; del.textContent = '削除';
    del.onclick = () => { todos.splice(i, 1); save(); render(); };
    li.append(cb, sp, del); ul.append(li); });
  $('#count').textContent = '残り ' + todos.filter(t => !t.done).length + ' 件'; }
function add() { const v = $('#new-todo').value.trim(); if (!v) return; todos.push({text: v, done: false}); $('#new-todo').value = ''; save(); render(); }
$('#add-btn').onclick = add; $('#new-todo').addEventListener('keydown', e => { if (e.key === 'Enter') add(); });
render();
"""
REF_WORDSTAT = r'''import json, sys
def stats(text):
    words = [w.lower() for w in text.split()]
    c = {}
    for w in words: c[w] = c.get(w, 0) + 1
    top = sorted(c.items(), key=lambda x: (-x[1], x[0]))[:5]
    return {"lines": len(text.splitlines()), "words": len(words), "chars": len(text), "top": [[k, v] for k, v in top]}
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python wordstat.py <file>"); sys.exit(1)
    with open(sys.argv[1], encoding="utf-8", newline="") as f:
        print(json.dumps(stats(f.read()), ensure_ascii=False))
'''
REF_WORDSTAT_TEST = '''import unittest
from wordstat import stats
class T(unittest.TestCase):
    def test_words(self): self.assertEqual(stats("a b a")["words"], 3)
    def test_top(self): self.assertEqual(stats("b a a")["top"][0], ["a", 2])
    def test_lines(self): self.assertEqual(stats("x\\ny")["lines"], 2)
'''


def solve(tid, w):
    """Reference solutions: what a perfect model would leave (for the self-test of the graders)."""
    if tid == "B1_rename":
        for f in glob.glob(os.path.join(w, "shop", "*.py")):
            s = open(f, encoding="utf-8").read().replace("calc_total", "compute_total")
            open(f, "w", encoding="utf-8").write(s)
    elif tid == "B2_bugfix":
        wr(w, "lib/paging.py", "def page(items, n, size=10):\n    start = (n - 1) * size\n    return items[start:start + size]\n\n\ndef pages(count, size=10):\n    return -(-count // size)\n")
        wr(w, "lib/money.py", "def discount(price, percent):\n    return int(price * (100 - percent) / 100 + 0.5)\n\n\ndef split(total, people):\n    base, extra = divmod(total, people)\n    return [base + (1 if i < extra else 0) for i in range(people)]\n")
        wr(w, "lib/text.py", "import re\n\n\ndef slug(title):\n    return '-'.join(re.findall(r'[a-z0-9]+', title.lower()))\n")
    elif tid == "B3_organize":
        idx = []
        for rel, d in B3_FILES.items():
            os.makedirs(os.path.join(w, d), exist_ok=True)
            shutil.move(os.path.join(w, *rel.split("/")), os.path.join(w, d, rel.split("/")[1]))
            idx.append("- %s/%s" % (d, rel.split("/")[1]))
        wr(w, "index.md", "\n".join(idx) + "\n")
    elif tid == "B4_aggregate":
        tot = {}
        for rows in b4_data().values():
            for _, c, v in rows:
                tot[c] = tot.get(c, 0) + v
        wr(w, "summary.csv", "category,total\n" + "".join("%s,%d\n" % kv for kv in sorted(tot.items(), key=lambda x: -x[1])))
    elif tid == "B5_configs":
        for rel in ("config/app.ini", "config/db.json", "config/deploy.yaml"):
            s = rd(w, rel).replace("8080", "9090").replace("host = 127.0.0.1", "host = 0.0.0.0")
            wr(w, rel, s)
    elif tid == "B6_crossdoc":
        wr(w, "tanaka.md", "".join("- %s（期限 %s）\n" % td for td in sorted(B6_TANAKA, key=lambda x: x[1])))
    elif tid == "C1_breakout":
        wr(w, "game/index.html", REF_GAME)
    elif tid == "C2_todo_app":
        wr(w, "todo/index.html", REF_TODO_HTML)
        wr(w, "todo/style.css", REF_TODO_CSS)
        wr(w, "todo/app.js", REF_TODO_JS)
    elif tid == "C3_cli_tool":
        wr(w, "wordstat.py", REF_WORDSTAT)
        wr(w, "tests/__init__.py", "")
        wr(w, "tests/test_wordstat.py", REF_WORDSTAT_TEST)
    elif tid == "C4_design_doc":
        body = "".join("日本語の説明文がここに続きます。" for _ in range(200))
        wr(w, "docs/design.md", "# 設計書\n## 目的\n%s\n## 構成\n### 部品\n## 手順\n### 準備\n## 評価方法\n| 項目 | 内容 |\n|---|---|\n| 長文 | 事実 |\n"
           "## リスクと対策\n```\npython night_bench.py run\n```\n## まとめ\n### 次\n" % body)


def cmd_selftest(a):
    root = tempfile.mkdtemp(prefix="nb_self_")
    print("browser:", find_browser() or "NOT FOUND (C1/C2 cannot be played; set BENCH_BROWSER)")
    bad = 0
    for task in TASKS:
        for mode in ("empty", "solved"):
            w = os.path.join(root, mode, task[0])
            os.makedirs(w)
            if task[3]:
                task[3](w)
            if task[0] == "B2_bugfix":
                B2_TEST_HASH[0] = sha(w, "tests/test_lib.py")
            if mode == "solved":
                solve(task[0], w)
            sc, mx, detail = grade(task, w, os.path.join(root, mode, "artifacts"))
            ok = (sc == mx) if mode == "solved" else (sc < mx)
            bad += not ok
            print("%-4s %-14s %-6s %2d/%-2d %s" % ("ok" if ok else "BAD", task[0], mode, sc, mx, detail))
    doc, facts = long_doc(6000, 6000)
    found = sum(1 for p, (wd, old) in facts.items() if wd in doc and old in doc)
    print("%-4s long_doc: %d chars, %d facts placed" % ("ok" if found == 5 else "BAD", len(doc), found))
    bad += found != 5
    shutil.rmtree(root, ignore_errors=True)
    print("SELFTEST", "PASSED" if not bad else "FAILED (%d)" % bad)
    sys.exit(1 if bad else 0)


# ================================================================================================ other agents
# The same B/C tasks and graders for agents that are not this loop: Aider (run here, task by task) and agents driven
# by hand such as Roo Code's Orchestrator (prepare the folders, work in them, then grade).
AIDER_FILES = {   # files Aider is given to edit or create (it edits what it is given; it does not move files)
    "C1_breakout": ["game/index.html"],
    "C2_todo_app": ["todo/index.html", "todo/style.css", "todo/app.js"],
    "C3_cli_tool": ["wordstat.py", "tests/__init__.py", "tests/test_wordstat.py"],
    "C4_design_doc": ["docs/design.md"],
}
AIDER_SKIP = {"B3_organize": "Aider edits file contents; it cannot move files (shell commands are off)"}


def task_by_id(tid):
    return next(t for t in TASKS if t[0] == tid)


def fresh_task(task, w):
    shutil.rmtree(w, ignore_errors=True)
    os.makedirs(w)
    if task[3]:
        task[3](w)


def b2_reference_hash():
    tmp = tempfile.mkdtemp(prefix="nb_b2_")
    setup_b2(tmp)
    h = sha(tmp, "tests/test_lib.py")
    shutil.rmtree(tmp, ignore_errors=True)
    return h


def want_tasks(spec):
    want = [x for x in (spec or "").split(",") if x]
    groups = {x for x in want if x in ("B", "C")}
    return [t for t in TASKS if not want or t[0] in want or t[1] in groups]


def text_files(w):
    out = []
    for d, dirs, files in os.walk(w):
        dirs[:] = [x for x in dirs if not x.startswith(".")]
        for fn in files:
            rel = os.path.relpath(os.path.join(d, fn), w).replace("\\", "/")
            if not fn.startswith(".") and not rel.startswith("TASK"):
                out.append(rel)
    return sorted(out)


def save_results(path, res):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)


def cmd_aider(a):
    """Every chosen task through `aider --architect` (planner and editor on the same server), then the same graders."""
    os.makedirs(a.logdir, exist_ok=True)
    deadline = time.time() + (a.deadline or 10 ** 9)
    res = {"name": a.name, "ctx": a.ctx, "effort": "aider architect", "started": time.strftime("%Y-%m-%d %H:%M"), "long": [], "tasks": []}
    out_path = os.path.join(a.logdir, "results.json")
    env = dict(os.environ, OPENAI_API_BASE=a.url.rstrip("/") + "/v1", OPENAI_API_KEY=os.environ.get("OPENAI_API_KEY", "local"),
               PYTHONIOENCODING="utf-8", AIDER_ANALYTICS="false")
    for task in want_tasks(a.tasks):
        tid = task[0]
        w = os.path.join(a.logdir, "work", tid)
        fresh_task(task, w)
        B2_TEST_HASH[0] = b2_reference_hash()
        row = {"task": tid, "group": task[1]}
        if tid in AIDER_SKIP:
            row.update(score=0, max=0, error="not_applicable", detail=AIDER_SKIP[tid])
        elif time.time() > deadline:
            row.update(score=0, max=0, error="deadline", detail="not run")
        else:
            with open(os.path.join(w, "TASK.md"), "w", encoding="utf-8") as f:
                f.write(task[2] + "\n")
            files = AIDER_FILES.get(tid) or text_files(w)
            # Aider resolves file names from the git working dir; the work folder lies inside the bench's own repo,
            # and even with --no-git Aider used that repo's root (2026-10-13: tanaka.md, docs/design.md landed there).
            # A repo of its own makes the task folder the root.
            subprocess.run(["git", "init", "-q", "."], cwd=w, capture_output=True)
            cmd = [a.aider_cmd, "--model", "openai/" + a.model, "--editor-model", "openai/" + a.model, "--architect", "--editor-edit-format", "editor-diff",
                   "--yes-always", "--no-auto-commits", "--no-dirty-commits", "--no-gitignore", "--no-suggest-shell-commands", "--no-show-model-warnings",
                   "--no-check-update", "--no-analytics", "--no-pretty", "--no-stream", "--map-tokens", "0", "--timeout", "1800",
                   "--message-file", "TASK.md"] + files
            print("[%s] start (aider, %d files)" % (tid, len(files)), flush=True)
            t0 = time.time()
            limit = max(60, min(task[6] * 60, deadline - time.time()))
            try:
                with open(os.path.join(a.logdir, "aider-%s.log" % tid), "w", encoding="utf-8", errors="replace") as log:
                    r = subprocess.run(cmd, cwd=w, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=limit, stdin=subprocess.DEVNULL)
                err = "" if r.returncode == 0 else "aider exit %d" % r.returncode
            except FileNotFoundError:
                sys.exit("aider not found (%s): install it, or pass --aider-cmd" % a.aider_cmd)
            except subprocess.TimeoutExpired:
                err = "time_limit"
            os.remove(os.path.join(w, "TASK.md"))
            try:
                sc, mx, detail = grade(task, w, os.path.join(a.logdir, "artifacts"))
            except Exception as e:
                sc, mx, detail = 0, 0, "grade_error: %r" % e
            row.update(score=sc, max=mx, detail=detail, error=err, seconds=round(time.time() - t0, 1))
            print("[%s] %s/%s %s | %s" % (tid, sc, mx, detail, err), flush=True)
        res["tasks"].append(row)
        save_results(out_path, res)
    res["finished"] = time.strftime("%Y-%m-%d %H:%M")
    save_results(out_path, res)


def cmd_prepare(a):
    """Task folders for an agent driven by hand: <out>/<task>/ with the fixture and TASK.md (the request to paste)."""
    if os.path.isdir(a.out) and os.listdir(a.out) and not a.force:
        sys.exit("%s already has task folders (work done in them would be lost): pass --force to start over" % a.out)
    for task in want_tasks(a.tasks):
        w = os.path.join(a.out, task[0])
        fresh_task(task, w)
        with open(os.path.join(w, "TASK.md"), "w", encoding="utf-8") as f:
            f.write(task[2] + "\n\n（作業はこのフォルダの中だけで行うこと。この TASK.md は変更・削除しないこと）\n")
    print("prepared %d task folders in %s" % (len(want_tasks(a.tasks)), a.out))


def cmd_grade(a):
    """Grade task folders made by `prepare` and worked on by another agent; results.json + REPORT under --root."""
    B2_TEST_HASH[0] = b2_reference_hash()
    res = {"name": a.name, "ctx": a.ctx, "effort": a.note, "started": time.strftime("%Y-%m-%d %H:%M"), "long": [], "tasks": []}
    logdir = os.path.join(a.root, a.name)
    os.makedirs(logdir, exist_ok=True)
    for task in want_tasks(a.tasks):
        w = os.path.join(a.dir, task[0])
        if not os.path.isdir(w):
            continue
        try:
            sc, mx, detail = grade(task, w, os.path.join(logdir, "artifacts"))
        except Exception as e:
            sc, mx, detail = 0, 0, "grade_error: %r" % e
        res["tasks"].append({"task": task[0], "group": task[1], "score": sc, "max": mx, "detail": detail})
        print("[%s] %s/%s %s" % (task[0], sc, mx, detail))
    save_results(os.path.join(logdir, "results.json"), res)
    cmd_report(argparse.Namespace(root=a.root))


# ================================================================================================ compaction test
# The Strata chat page (serve/web/app.js, kk) compacts a long chat into one hand-over note. This runs the same idea
# through the API on a real model: a multi-turn file job, the page's own summary prompt, then turns that need what was
# compacted away. With --baseline the same turns run once more without compaction, for comparison.
APP_JS = os.path.join(HERE, "strata", "serve", "web", "app.js")
COMPACT_TOOL_CHARS = 1500
COMPACT_TURNS_BEFORE = [
    "minutes/ フォルダの議事録（8ファイル）をすべて読み、田中さんが担当するアクションアイテム（内容と期限）を把握してください。"
    "まだファイルには書かず、把握した件数だけ答えてください。",
    "config/app.ini の [server] の port を 8080 から 9090 に変えてください。他の行は変えないこと。",
    "今後のルール: この作業で新しく作るファイルは必ず out/ フォルダに置くこと。日付は必ず YYYY-MM-DD 形式（年は 2026）で書くこと。"
    "了解したら「了解」とだけ答えてください。",
    "config/deploy.yaml の port: 8080 を、2 か所とも 9090 に変えてください。他は変えないこと。",
]
COMPACT_TURNS_AFTER = [
    "最初に把握した田中さんのアクションアイテムを、決めたルールに従って tanaka.md というファイルに"
    "「- 内容（期限 YYYY-MM-DD）」の形で、期限の早い順に書いてください。",
    "この会話で、これまでに変更・作成したファイルをすべてパス付きで挙げてください。",
]


def compact_prompt():
    """The summary request the chat page sends (read from app.js, so the test follows the page)."""
    try:
        js = open(APP_JS, encoding="utf-8").read()
        m = re.search(r'const COMPACT_PROMPT = (.*?);\n', js, re.S)
        parts = re.findall(r'"((?:[^"\\]|\\.)*)"', m.group(1))
        return "".join(json.loads('"%s"' % x) for x in parts)
    except Exception:
        return ("ここまでの会話を、別のアシスタントがそのまま作業を引き継げる「引き継ぎメモ」に要約してください。"
                "目的、決まったこと、触ったファイル、分かった事実、未完了の作業、注意点を見出し付きの箇条書きで。")


def chat_plain(a, msgs, max_tokens, effort, timeout):
    payload = {"model": a.model, "messages": msgs, "temperature": 0.2, "max_tokens": max_tokens, "reasoning_effort": effort}
    req = urllib.request.Request(a.url.rstrip("/") + "/v1/chat/completions", data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    with NOPROXY.open(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def agent_turn(a, msgs, w, log, label, max_steps=30, minutes=20):
    """One user turn of a continuing conversation (msgs already ends with the user message); returns stats."""
    agent.SANDBOX = w
    end = time.time() + minutes * 60
    st = {"turn": label, "steps": 0, "prompt_tokens_max": 0, "completion_tokens": 0, "error": "", "answer": ""}
    t0 = time.time()
    for step in range(1, max_steps + 1):
        st["steps"] = step
        if time.time() > end:
            st["error"] = "time_limit"
            break
        try:
            resp = chat_tools(a, msgs, max(30, min(1800, int(end - time.time()))))
        except urllib.error.HTTPError as e:
            st["error"] = "http %d: %s" % (e.code, e.read().decode("utf-8", "replace")[:200])
            break
        except Exception as e:
            st["error"] = "llm_error: %r" % e
            break
        u = resp.get("usage") or {}
        st["completion_tokens"] += u.get("completion_tokens", 0)
        st["prompt_tokens_max"] = max(st["prompt_tokens_max"], u.get("prompt_tokens", 0))
        m = resp["choices"][0]["message"]
        calls = m.get("tool_calls") or []
        log.write(json.dumps({"turn": label, "step": step, "content": (m.get("content") or "")[:1500], "tool_calls": calls,
                              "reasoning": (m.get("reasoning_content") or "")[:1500],
                              "finish": resp["choices"][0].get("finish_reason")}, ensure_ascii=False) + "\n")
        if not calls and not (m.get("content") or "").strip():
            st["empty_answers"] = st.get("empty_answers", 0) + 1   # an empty final answer: ask again (at most twice)
            if st["empty_answers"] <= 2:
                continue
            st["error"] = "empty_answer"
        msgs.append({"role": "assistant", "content": m.get("content") or "", **({"tool_calls": calls} if calls else {})})
        if not calls:
            st["answer"] = m.get("content") or ""
            break
        for c in calls:
            try:
                args = c["function"].get("arguments") or "{}"
                args = json.loads(args) if isinstance(args, str) else args
                out = agent.TOOLS[c["function"]["name"]](**args)
            except Exception as e:
                out = "ERROR: %r" % e
            msgs.append({"role": "tool", "tool_call_id": c.get("id", ""), "content": out})
    else:
        st["error"] = "max_steps"
    log.flush()
    st["seconds"] = round(time.time() - t0, 1)
    return st


def compact_msgs(a, msgs, log):
    """What the page does: everything before the last user turn -> one note; that turn stays as it is."""
    last_user = max(i for i, m in enumerate(msgs) if m["role"] == "user")
    old, kept = msgs[1:last_user], msgs[last_user:]
    payload = [msgs[0]] + [dict(m, content=m["content"][:COMPACT_TOOL_CHARS] + "\n…(省略)")
                           if m["role"] == "tool" and len(m.get("content") or "") > COMPACT_TOOL_CHARS else m for m in old]
    payload.append({"role": "user", "content": compact_prompt()})
    t0 = time.time()
    resp = chat_plain(a, payload, 4096, "low", 1800)
    summary = ((resp["choices"][0]["message"].get("content")) or "").strip()
    log.write(json.dumps({"compaction_summary": summary}, ensure_ascii=False) + "\n")
    note = "【これまでの会話の要約（自動圧縮・%d件）】\n\n%s" % (len(old), summary)
    new = [msgs[0], {"role": "user", "content": note},
           {"role": "assistant", "content": "引き継ぎメモを確認しました。この内容を前提に続けます。"}] + kept
    return new, summary, round(time.time() - t0, 1), (resp.get("usage") or {})


def grade_compact_summary(summary):
    checks = {"田中の担当": "田中" in summary, "app.ini の変更": "app.ini" in summary,
              "9090": "9090" in summary, "out/ のルール": bool(re.search(r"out\s*/|out\s*フォルダ", summary)),
              "YYYY-MM-DD のルール": "YYYY-MM-DD" in summary or "YYYY‐MM‐DD" in summary,
              "長さ 4000 字以内": 0 < len(summary) <= 4000}
    return sum(checks.values()), len(checks), ", ".join("%s %s" % (k, "ok" if v else "NG") for k, v in checks.items())


def grade_compact_file(w):
    s = rd(w, "out/tanaka.md")
    where = "out/tanaka.md"
    if s is None:
        s, where = rd(w, "tanaka.md"), "tanaka.md (rule broken: not in out/)"
    if s is None:
        return 0, 4, "no tanaka.md"
    found = [t for t, d in B6_TANAKA if t in s]
    iso = [t for t, d in B6_TANAKA if ("2026-" + d.replace("/", "-")) in s]
    order_ok = [s.find(t) for t, d in sorted(B6_TANAKA, key=lambda x: x[1]) if t in s]
    score = (where == "out/tanaka.md") + (2 if len(found) == 6 else 1 if len(found) >= 4 else 0) + (len(iso) == 6)
    return score, 4, "%s, items %d/6, YYYY-MM-DD %d/6, sorted %s" % (where, len(found), len(iso), order_ok == sorted(order_ok))


def grade_compact_recall(answer):
    checks = {"app.ini": "app.ini" in answer, "deploy.yaml": "deploy.yaml" in answer, "tanaka.md": "tanaka.md" in answer}
    return sum(checks.values()), 3, ", ".join("%s %s" % (k, "ok" if v else "NG") for k, v in checks.items())


def run_compact_scenario(a, w, log, compact):
    tag = "compact" if compact else "baseline"
    shutil.rmtree(w, ignore_errors=True)
    os.makedirs(w)
    setup_b6(w)
    setup_b5(w)
    msgs = [{"role": "system", "content": SYSTEM}]
    turns, info = [], {}
    for i, text in enumerate(COMPACT_TURNS_BEFORE, 1):
        msgs.append({"role": "user", "content": text})
        print("[%s] turn %d" % (tag, i), flush=True)
        turns.append(agent_turn(a, msgs, w, log, "%s-%d" % (tag, i)))
    info["prompt_tokens_before"] = turns[-1]["prompt_tokens_max"]
    if compact:
        print("[%s] compacting %d messages" % (tag, len(msgs)), flush=True)
        try:
            msgs, summary, secs, usage = compact_msgs(a, msgs, log)
        except Exception as e:
            summary, secs, usage = "", 0, {}
            info["compact_error"] = repr(e)
        info.update(summary=summary, compact_seconds=secs, summary_chars=len(summary))
    for j, text in enumerate(COMPACT_TURNS_AFTER, len(COMPACT_TURNS_BEFORE) + 1):
        msgs.append({"role": "user", "content": text})
        print("[%s] turn %d" % (tag, j), flush=True)
        turns.append(agent_turn(a, msgs, w, log, "%s-%d" % (tag, j)))
    info["prompt_tokens_after"] = turns[len(COMPACT_TURNS_BEFORE)]["prompt_tokens_max"]
    info["turns"] = turns
    return info


def cmd_compact_test(a):
    os.makedirs(a.logdir, exist_ok=True)
    res = {"name": a.name, "ctx": a.ctx, "effort": a.effort, "started": time.strftime("%Y-%m-%d %H:%M"), "long": [], "tasks": []}
    out_path = os.path.join(a.logdir, "results.json")
    with open(os.path.join(a.logdir, "transcript.jsonl"), "a", encoding="utf-8") as log:
        for compact in ([True, False] if a.baseline else [True]):
            tag = "compact" if compact else "baseline"
            w = os.path.join(a.logdir, "work", tag)
            info = run_compact_scenario(a, w, log, compact)
            with open(os.path.join(a.logdir, "compact-%s.json" % tag), "w", encoding="utf-8") as f:
                json.dump(info, f, ensure_ascii=False, indent=1)
            secs = sum(t["seconds"] for t in info["turns"]) + info.get("compact_seconds", 0)
            errs = "; ".join("%s: %s" % (t["turn"], t["error"]) for t in info["turns"] if t["error"])
            if compact:
                sc, mx, d = grade_compact_summary(info.get("summary", ""))
                res["tasks"].append({"task": "K1_summary", "group": "K", "score": sc, "max": mx, "seconds": info.get("compact_seconds"),
                                     "detail": "%s; %d chars; prompt %s -> %s tokens%s" % (
                                         d, info.get("summary_chars", 0), info["prompt_tokens_before"], info["prompt_tokens_after"],
                                         "; " + info["compact_error"] if info.get("compact_error") else "")})
            sc, mx, d = grade_compact_file(w)
            res["tasks"].append({"task": "K2_after_%s" % tag, "group": "K", "score": sc, "max": mx, "seconds": round(secs, 1),
                                 "detail": d, "error": errs})
            sc, mx, d = grade_compact_recall(info["turns"][-1]["answer"])
            if not info["turns"][-1]["answer"].strip():
                d += " (empty answer%s)" % (", " + info["turns"][-1]["error"] if info["turns"][-1]["error"] else "")
            res["tasks"].append({"task": "K3_recall_%s" % tag, "group": "K", "score": sc, "max": mx, "detail": d})
            save_results(out_path, res)
            for t in res["tasks"]:
                if t["task"].endswith(tag) or (compact and t["task"] == "K1_summary"):
                    print("[%s] %s/%s %s" % (t["task"], t["score"], t["max"], t["detail"]), flush=True)
    res["finished"] = time.strftime("%Y-%m-%d %H:%M")
    save_results(out_path, res)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--url", default="http://127.0.0.1:8085")
    r.add_argument("--model", default="local")
    r.add_argument("--name", required=True)
    r.add_argument("--ctx", type=int, default=32768, help="the context the server was started with")
    r.add_argument("--effort", default="medium")
    r.add_argument("--long-effort", default="low", help="reasoning effort for the long-context prompts")
    r.add_argument("--max-tokens", type=int, default=16384)
    r.add_argument("--deadline", type=int, default=0, help="seconds for this whole model")
    r.add_argument("--tasks", default="", help="comma list (L = the long-context set), default all")
    r.add_argument("--logdir", required=True)
    p = sub.add_parser("report")
    p.add_argument("--root", required=True)
    m = sub.add_parser("make-config")
    m.add_argument("--src", required=True)
    m.add_argument("--ctx", type=int, required=True)
    m.add_argument("--out", required=True)
    sub.add_parser("selftest")
    x = sub.add_parser("aider", help="the B/C tasks through aider --architect")
    x.add_argument("--url", default="http://127.0.0.1:8085")
    x.add_argument("--model", default="local")
    x.add_argument("--name", default="aider")
    x.add_argument("--ctx", type=int, default=0)
    x.add_argument("--aider-cmd", default="aider")
    x.add_argument("--deadline", type=int, default=0)
    x.add_argument("--tasks", default="B,C", help="task ids, or the groups B and C")
    x.add_argument("--logdir", required=True)
    q = sub.add_parser("prepare", help="task folders + TASK.md for an agent driven by hand (Roo Code ...)")
    q.add_argument("--out", required=True)
    q.add_argument("--tasks", default="B,C")
    q.add_argument("--force", action="store_true", help="recreate folders that already exist")
    g = sub.add_parser("grade", help="grade the folders from prepare")
    g.add_argument("--dir", required=True)
    g.add_argument("--name", required=True)
    g.add_argument("--root", required=True, help="the report folder (other runs there are compared too)")
    g.add_argument("--ctx", type=int, default=0)
    g.add_argument("--note", default="")
    g.add_argument("--tasks", default="B,C")
    k = sub.add_parser("compact-test", help="a multi-turn file job, compacted as the chat page does, then continued")
    k.add_argument("--url", default="http://127.0.0.1:8085")
    k.add_argument("--model", default="local")
    k.add_argument("--name", default="compact")
    k.add_argument("--ctx", type=int, default=0)
    k.add_argument("--effort", default="medium")
    k.add_argument("--max-tokens", type=int, default=16384)
    k.add_argument("--baseline", action="store_true", help="also run the same turns without compaction")
    k.add_argument("--logdir", required=True)
    a = ap.parse_args()
    {"compact-test": cmd_compact_test, "run": cmd_run, "report": cmd_report, "make-config": cmd_make_config, "selftest": cmd_selftest,
     "aider": cmd_aider, "prepare": cmd_prepare, "grade": cmd_grade}[a.cmd](a)


if __name__ == "__main__":
    main()
