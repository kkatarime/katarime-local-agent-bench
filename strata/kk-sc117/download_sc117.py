"""SC117 の無検閲 GSQ-RCO 版（SC117/Qwen3.8-Flash-Next-GSQ-RCO-abliterated-GGUF）を Strata-data/sc117/<サイズ> に
再開可能ダウンロードする（kk用）。ファイル名は決め打ちせず、リポジトリのファイル一覧から選ぶ。

    .venv\\Scripts\\python.exe kk-sc117\\download_sc117.py [--quant IQ3_XXS]

ゲート付きのときは HF のアクセストークンが要る。HF_TOKEN 環境変数か、クリップボード（hf_...）から読む。"""
import argparse, os, pathlib, subprocess, sys, time
import requests

REPO = "SC117/Qwen3.8-Flash-Next-GSQ-RCO-abliterated-GGUF"
QUANTS = ("Q2_0", "IQ2_XS", "IQ3_XXS", "IQ3_S")
DATA = pathlib.Path(__file__).resolve().parents[2] / "Strata-data"


def token_from_clipboard():
    input("このリポジトリはトークンが必要です。HF のトークン（hf_...）をコピーしてから Enter を押してください: ")
    tok = subprocess.run(["powershell", "-NoProfile", "-Command", "Get-Clipboard"],
                         capture_output=True, text=True).stdout.strip()
    if not tok.startswith("hf_"):
        sys.exit("クリップボードにトークン（hf_ で始まる文字列）がありません。コピーし直してもう一度実行してください。")
    print(f"トークンを読み取りました（hf_...{tok[-4:]}）")
    return tok


def list_files(hdr):
    r = requests.get(f"https://huggingface.co/api/models/{REPO}/tree/main", params={"recursive": "true"},
                     headers=hdr, timeout=60)
    if r.status_code in (401, 403):
        return None
    r.raise_for_status()
    return [(x["path"], int(x.get("lfs", {}).get("size") or x.get("size") or 0)) for x in r.json() if x.get("type") == "file"]


def fetch(path, size, dst, hdr):
    out = dst / pathlib.PurePosixPath(path).name
    part = out.with_suffix(out.suffix + ".part")
    if out.exists() and out.stat().st_size == size:
        print(f"済: {out.name}")
        return
    u = f"https://huggingface.co/{REPO}/resolve/main/{path}"
    have = part.stat().st_size if part.exists() else 0
    h = dict(hdr, Range=f"bytes={have}-")
    with requests.get(u, headers=h, stream=True, timeout=60) as r:
        if r.status_code in (401, 403):
            sys.exit(f"アクセス拒否({r.status_code})：HF のモデルページで利用条件に同意したか、トークンを確認してください。")
        r.raise_for_status()
        if not (have and r.status_code == 206):
            have = 0
        t0, done, last = time.time(), have, 0
        with open(part, "ab" if have else "wb") as f:
            for chunk in r.iter_content(8 << 20):
                f.write(chunk)
                done += len(chunk)
                if time.time() - last > 2:
                    sp = (done - have) / max(time.time() - t0, 1e-6)
                    print(f"\r{out.name[-40:]}  {done / 1e9:6.1f}/{size / 1e9:.1f} GB  {sp / 1e6:5.0f} MB/s ", end="", flush=True)
                    last = time.time()
    print()
    if size and part.stat().st_size != size:
        sys.exit("サイズが一致しません。もう一度実行すると続きから再開します。")
    part.replace(out)
    print(f"完了: {out.name}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quant", default="IQ3_XXS", type=str.upper, choices=QUANTS)
    a = ap.parse_args()
    tok = os.environ.get("HF_TOKEN", "").strip()
    hdr = {"Authorization": f"Bearer {tok}"} if tok else {}
    files = list_files(hdr)
    if files is None:
        hdr = {"Authorization": f"Bearer {token_from_clipboard()}"}
        files = list_files(hdr)
        if files is None:
            sys.exit("ファイル一覧を取得できません。HF のモデルページで利用条件に同意したか確認してください: https://huggingface.co/" + REPO)
    q = a.quant.lower()
    pick = [(p, s) for p, s in files if p.lower().endswith(".gguf") and not pathlib.PurePosixPath(p).name.lower().startswith("mmproj")
            and (f"/{q}/" in "/" + p.lower() or f"-{q}-" in p.lower() or f"-{q}." in p.lower())]
    if not pick:
        print("このサイズの GGUF が見つかりません。リポジトリにあるファイル:")
        for p, s in files:
            print(f"  {p}  ({s / 1e9:.1f} GB)")
        sys.exit(1)
    others = [p for p, _ in files if not p.lower().endswith(".gguf")]
    if others:
        print("（GGUF 以外のファイル: " + ", ".join(others[:20]) + (" ..." if len(others) > 20 else "") + "）")
    dst = DATA / "sc117" / a.quant
    dst.mkdir(parents=True, exist_ok=True)
    total = sum(s for _, s in pick)
    print(f"{REPO} {a.quant}: {len(pick)} ファイル、合計 {total / 1e9:.1f} GB -> {dst}")
    for p, s in pick:
        fetch(p, s, dst, hdr)
    print("ダウンロード完了:", dst)


if __name__ == "__main__":
    main()
