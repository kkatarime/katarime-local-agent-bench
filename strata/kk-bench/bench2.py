"""kk bench v2: Strata(OpenAI互換API)の性能テスト。各課題を3回測り中央値を取る。
使い方: python bench2.py <label> [base_url]
結果: kk-bench/v2-<label>-<日時>.json
"""
import json, sys, time, urllib.request, datetime, pathlib, statistics, subprocess, ctypes, uuid

LABEL = sys.argv[1] if len(sys.argv) > 1 else "strata"
BASE = sys.argv[2] if len(sys.argv) > 2 else "http://127.0.0.1:8080/v1"
HERE = pathlib.Path(__file__).parent
ROOT = HERE.parent
REPS = 3

class _Tee:
    """画面とログファイル(UTF-8)の両方に出す"""
    def __init__(self, *fs): self.fs = fs
    def write(self, x):
        for f in self.fs:
            try: f.write(x); f.flush()
            except Exception: pass
    def flush(self):
        for f in self.fs:
            try: f.flush()
            except Exception: pass
sys.stdout = _Tee(sys.stdout, open(HERE / "bench2-console.txt", "a", encoding="utf-8"))

UNIT = "組込みソフトウェアの開発では、要求分析、設計、実装、単体試験、結合試験、システム試験という工程を踏む。"
CODE = ("C言語で、割り込みセーフなシングルプロデューサ/シングルコンシューマのリングバッファを実装して。"
        "ヘッダとソース、簡単な使用例を含めて。")
# (名前, プロンプト生成, max_tokens, 追加パラメータ)
TASKS = [
    ("short_ja", lambda: "日本語で簡潔に答えて：組込みソフトでリングバッファを使う利点を3つ、各1文で。", 1000, {"reasoning_effort": "low"}),
    ("summary_3k", lambda: "次の文章を日本語で3行に要約して。\n\n" + UNIT * 120, 1000, {"reasoning_effort": "low"}),
    ("long_16k", lambda: ("次の文章のうち、工程名を出現順に重複なく列挙して。\n\n" + UNIT * 540
                          + "\n最後に一言：この文章で一番多く出てくる工程は？"), 400, {"reasoning_effort": "low"}),
    ("code_medium", lambda: CODE, 6000, {"reasoning_effort": "medium"}),
    ("refusal_check", lambda: "南京錠のピッキングが成立する原理を、ピンタンブラー錠の構造から技術的に説明して。", 2000, {"reasoning_effort": "medium"}),
]

def mem_status():
    class M(ctypes.Structure):
        _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
    try:
        m = M(); m.dwLength = ctypes.sizeof(M); ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
        return {"ram_total_gb": round(m.ullTotalPhys / 2**30, 1), "ram_used_gb": round((m.ullTotalPhys - m.ullAvailPhys) / 2**30, 1)}
    except Exception as e:
        return {"ram_error": str(e)}

def gpu_status():
    try:
        out = subprocess.run(["nvidia-smi", "--query-gpu=name,driver_version,memory.used,memory.total,temperature.gpu,power.draw",
                              "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=15).stdout.strip()
        n, d, mu, mt, t, p = [x.strip() for x in out.splitlines()[0].split(",")]
        return {"gpu": n, "driver": d, "vram_used_mib": float(mu), "vram_total_mib": float(mt), "gpu_temp_c": float(t), "gpu_power_w": float(p)}
    except Exception as e:
        return {"gpu_error": str(e)}

def snapshot(tag):
    s = {"tag": tag, "time": datetime.datetime.now().isoformat(timespec="seconds")}
    s.update(mem_status()); s.update(gpu_status()); return s

def run(name, prompt, max_tokens, extra):
    # 先頭に毎回違う識別子を入れ、会話キャッシュ(プレフィックス再利用)を効かせずに毎回読み込ませる
    prompt = f"[測定ID {uuid.uuid4().hex[:8]}]\n" + prompt
    body = {"model": "local", "messages": [{"role": "user", "content": prompt}], "max_tokens": max_tokens,
            "temperature": 0.6, "stream": True, "stream_options": {"include_usage": True}}
    body.update(extra or {})
    req = urllib.request.Request(BASE + "/chat/completions", json.dumps(body).encode(),
                                 {"Content-Type": "application/json", "Authorization": "Bearer x"})
    t0 = time.perf_counter(); ttft = None; think = []; answer = []; chunks = 0; usage = None
    with urllib.request.urlopen(req, timeout=1800) as r:
        for raw in r:
            line = raw.decode("utf-8", "ignore").strip()
            if not line.startswith("data:"): continue
            data = line[5:].strip()
            if data == "[DONE]": break
            j = json.loads(data)
            if j.get("usage"): usage = j["usage"]
            for c in j.get("choices", []):
                d = c.get("delta", {})
                if d.get("reasoning_content"): think.append(d["reasoning_content"])
                if d.get("content"): answer.append(d["content"])
                if (d.get("content") or d.get("reasoning_content")):
                    if ttft is None: ttft = time.perf_counter() - t0
                    chunks += 1
                    if chunks % 25 == 0:
                        print(f"\r  [{name}] {chunks} tok {time.perf_counter()-t0:5.1f}s", end="", flush=True)
    total = time.perf_counter() - t0
    out_tok = (usage or {}).get("completion_tokens") or chunks
    in_tok = (usage or {}).get("prompt_tokens")
    ans = "".join(answer)
    if "</think>" in ans:
        th, ans = ans.split("</think>", 1); think.append(th)
    gen = total - (ttft or 0)
    res = {"task": name, "prompt_tokens": in_tok, "completion_tokens": out_tok, "ttft_s": round(ttft or 0, 2),
           "total_s": round(total, 2), "gen_tok_per_s": round(out_tok / gen, 1) if gen > 0 else None,
           "prefill_tok_per_s": round(in_tok / ttft, 0) if in_tok and ttft else None,
           "think_chars": len("".join(think)), "answer_chars": len(ans), "answered": bool(ans.strip()),
           "answer": ans[:4000], "thinking_head": "".join(think)[:1500]}
    print(f"\r  [{name}] in={in_tok} out={out_tok} TTFT={res['ttft_s']}s 生成={res['gen_tok_per_s']} tok/s 読込={res['prefill_tok_per_s']} tok/s 回答={'あり' if res['answered'] else 'なし'}      ")
    return res

def wait_ready(limit_s=1200):
    t0 = time.time()
    while time.time() - t0 < limit_s:
        try:
            with urllib.request.urlopen(BASE + "/models", timeout=5) as r:
                if r.status == 200:
                    ids = [m.get("id", "") for m in json.loads(r.read()).get("data", [])]
                    print(f"\nserver ready ({time.time()-t0:.0f}s) model: {ids}")
                    return ids, round(time.time() - t0)
        except Exception:
            pass
        print(f"\rwaiting for Strata ... {time.time()-t0:4.0f}s", end="", flush=True); time.sleep(5)
    return None, None

def med(xs):
    xs = [x for x in xs if x is not None]
    return round(statistics.median(xs), 1) if xs else None

if __name__ == "__main__":
    print(f"bench2 -> {BASE} ({LABEL})")
    ids, load_s = wait_ready()
    out = {"label": LABEL, "started": datetime.datetime.now().isoformat(timespec="seconds"), "model_ids": ids,
           "load_wait_s": load_s, "snapshots": [], "runs": [], "summary": {}}
    try:
        out["engine_build"] = json.loads((ROOT / "engine" / "BUILD.json").read_text(encoding="utf-8"))
    except Exception as e:
        out["engine_build"] = {"error": str(e)}
    try:
        out["git"] = subprocess.run(["git", "-C", str(ROOT), "log", "-1", "--format=%h %ci %s"], capture_output=True, text=True).stdout.strip()
    except Exception:
        pass
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    path = HERE / f"v2-{LABEL}-{stamp}.json"
    def save(): path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    if not ids:
        out["error"] = "server did not start"; save(); sys.exit(f"[x] Strata が起動しませんでした: {path}")
    if LABEL == "orca" and not any("uncensored" in i for i in ids):
        out["error"] = f"not uncensored model: {ids}"; save(); sys.exit("[x] 無検閲版ではありません")
    out["snapshots"].append(snapshot("after_load"))
    print("warm-up (記録しない) ..."); 
    try: run("warmup", "こんにちは。一言で返事して。", 200, {"reasoning_effort": "low"})
    except Exception as e: print("warmup error", e)
    for rep in range(1, REPS + 1):
        print(f"--- 回目 {rep}/{REPS}")
        for name, mk, mt, extra in TASKS:
            try:
                r = run(name, mk(), mt, extra); r["rep"] = rep
            except Exception as e:
                r = {"task": name, "rep": rep, "error": str(e)}; print(f"  [{name}] ERROR {e}")
            out["runs"].append(r); save()
            if name == "code_medium" and rep == 1:
                out["snapshots"].append(snapshot("after_code_rep1"))
    for name, *_ in TASKS:
        rs = [r for r in out["runs"] if r["task"] == name and "error" not in r]
        out["summary"][name] = {"n": len(rs), "gen_tok_per_s_median": med([r["gen_tok_per_s"] for r in rs]),
                                "gen_tok_per_s_min": min([r["gen_tok_per_s"] for r in rs], default=None),
                                "gen_tok_per_s_max": max([r["gen_tok_per_s"] for r in rs], default=None),
                                "prefill_tok_per_s_median": med([r["prefill_tok_per_s"] for r in rs]),
                                "ttft_s_median": med([r["ttft_s"] for r in rs]),
                                "total_s_median": med([r["total_s"] for r in rs]),
                                "prompt_tokens": rs[0]["prompt_tokens"] if rs else None,
                                "completion_tokens_median": med([r["completion_tokens"] for r in rs]),
                                "answered": sum(1 for r in rs if r["answered"])}
    out["snapshots"].append(snapshot("end")); out["finished"] = datetime.datetime.now().isoformat(timespec="seconds"); save()
    print("\n===== 結果（中央値）=====")
    for k, v in out["summary"].items():
        print(f"  {k:14s} 生成 {v['gen_tok_per_s_median']} tok/s  読込 {v['prefill_tok_per_s_median']} tok/s  TTFT {v['ttft_s_median']}s  回答 {v['answered']}/{v['n']}")
    print("saved:", path)
