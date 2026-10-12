"""OrcaRouter Uncensored IQ3_XXS を Strata-data/orca に再開可能ダウンロードする（kk用）。
HFのゲート承認済みアカウントのアクセストークンが必要。HF_TOKEN 環境変数か、起動時の入力で渡す（画面に表示しない）。"""
import os, sys, time, getpass, pathlib, requests

REPO = "orcarouter/Qwen3.8-Flash-Next-Uncensored-GGUF"
FILES = ["Qwen3.8-Flash-Next-Uncensored-IQ3_XXS-00001-of-00002.gguf",
         "Qwen3.8-Flash-Next-Uncensored-IQ3_XXS-00002-of-00002.gguf"]
DST = pathlib.Path(__file__).resolve().parents[2] / "Strata-data" / "orca"

def url_for(name, hdr):
    for path in (name, f"IQ3_XXS/{name}"):
        u = f"https://huggingface.co/{REPO}/resolve/main/{path}"
        r = requests.head(u, headers=hdr, allow_redirects=True, timeout=30)
        if r.status_code == 200:
            return u, int(r.headers.get("content-length", 0))
        if r.status_code in (401, 403):
            sys.exit(f"アクセス拒否({r.status_code})：HFでモデルページのゲートを承認したか、トークンが正しいか確認してください。")
    sys.exit(f"ファイルが見つかりません: {name}")

def fetch(name, hdr):
    u, size = url_for(name, hdr)
    out = DST / name; part = out.with_suffix(out.suffix + ".part")
    if out.exists() and out.stat().st_size == size:
        print(f"済: {name}"); return
    have = part.stat().st_size if part.exists() else 0
    h = dict(hdr); h["Range"] = f"bytes={have}-" if have else "bytes=0-"
    with requests.get(u, headers=h, stream=True, timeout=60) as r:
        r.raise_for_status()
        mode = "ab" if (have and r.status_code == 206) else "wb"
        if mode == "wb": have = 0
        t0 = time.time(); done = have; last = 0
        with open(part, mode) as f:
            for chunk in r.iter_content(8 << 20):
                f.write(chunk); done += len(chunk)
                if time.time() - last > 2:
                    sp = (done - have) / max(time.time() - t0, 1e-6)
                    print(f"\r{name[-22:]}  {done/1e9:6.1f}/{size/1e9:.1f} GB  {sp/1e6:5.0f} MB/s ", end="", flush=True)
                    last = time.time()
    print()
    if part.stat().st_size != size:
        sys.exit("サイズ不一致。もう一度実行すると続きから再開します。")
    part.rename(out); print(f"完了: {name}")

if __name__ == "__main__":
    DST.mkdir(parents=True, exist_ok=True)
    tok = os.environ.get("HF_TOKEN", "").strip()
    if not tok:
        input("トークン（hf_...）をコピーした状態で Enter を押してください（クリップボードから読み取ります）: ")
        import subprocess
        tok = subprocess.run(["powershell", "-NoProfile", "-Command", "Get-Clipboard"],
                             capture_output=True, text=True).stdout.strip()
    if not tok.startswith("hf_"):
        sys.exit("クリップボードにトークン（hf_ で始まる文字列）がありません。コピーし直してもう一度実行してください。")
    print(f"トークンを読み取りました（hf_...{tok[-4:]}）")
    hdr = {"Authorization": f"Bearer {tok}"}
    for n in FILES:
        fetch(n, hdr)
    print("全ファイルのダウンロード完了:", DST)
