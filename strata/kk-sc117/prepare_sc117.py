"""ダウンロードした SC117 版から、Strata 用のパックと起動設定 kk-sc117/sc117-<サイズ>.json を作る（kk用）。

    .venv\\Scripts\\python.exe kk-sc117\\prepare_sc117.py [--quant IQ3_XXS] [--context 32768]

標準の setup.py には通さない。通すと標準版と同じ名前（packs/iq3_xxs）のパックが再利用され、
無検閲化した部分（SC117 が差し替えた投影の重み）が標準版のもので上書きされたまま動いてしまうため。
パックは packs/sc117-<サイズ> に別に作り、エンジンの設定は既存の動いている設定（標準版、無ければ Orca）から写す。"""
import argparse, glob, json, os, pathlib, re, subprocess, sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
DATA = ROOT.parent / "Strata-data"
SHARD = re.compile(r"-(\d{5})-of-(\d{5})\.gguf$")


def say(m):
    print("  " + m, flush=True)


def base_config(quant):
    """Settings that already run on this PC: the standard config of the same size, else any standard one, else Orca's."""
    cands = [ROOT / f"strata-{quant.lower()}.json"]
    cands += sorted((pathlib.Path(p) for p in glob.glob(str(ROOT / "strata-*.json")) if not p.endswith(".shared-settings.json")),
                    key=os.path.getmtime, reverse=True)
    cands.append(ROOT / "kk-orca" / "orca-iq3_xxs.json")
    for c in cands:
        if c.is_file():
            return c, json.loads(c.read_text(encoding="utf-8-sig"))
    sys.exit("動いている Strata の設定（strata-*.json か kk-orca\\orca-iq3_xxs.json）が見つかりません。先に Strata を一度起動してください。")


def set_arg(args, flag, value=None, drop=False):
    if flag in args:
        i = args.index(flag)
        has_value = i + 1 < len(args) and not args[i + 1].startswith("--")
        del args[i:i + (2 if has_value else 1)]
    if not drop:
        args += [flag] if value is None else [flag, str(value)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quant", default="IQ3_XXS", type=str.upper)
    ap.add_argument("--context", type=int, default=32768, help="32768 / 65536 / 131072 ...")
    ap.add_argument("--kv", default="int8", choices=["int8", "q4_0"])
    a = ap.parse_args()
    src = DATA / "sc117" / a.quant
    firsts = sorted(p for p in src.glob("*-00001-of-*.gguf"))
    if len(firsts) != 1:
        sys.exit(f"{src} に 1 番目の分割ファイル（*-00001-of-*.gguf）が {len(firsts)} 個あります。先に download_sc117.py を実行してください。")
    first = firsts[0]
    total = int(SHARD.search(first.name).group(2))
    shards = [first.with_name(SHARD.sub("-%05d-of-%05d.gguf" % (i, total), first.name)) for i in range(1, total + 1)]
    missing = [s.name for s in shards if not s.is_file()]
    if missing:
        sys.exit("足りない分割ファイル: " + ", ".join(missing))
    print(f"[1/3] モデル: {first.name}（{total} 分割）")

    env = dict(os.environ, STRATA_GGUF_PY=str(ROOT / "third_party" / "llama.cpp" / "gguf-py"))
    sys.path.insert(0, str(ROOT / "tools"))
    from gguf_reader import GGUFFile
    ple = next((s for s in shards if any(t.name == "per_layer_token_embd.weight" for t in GGUFFile(s).tensors)), None)
    if ple is None:
        sys.exit("per_layer_token_embd が見つかりません（Qwen3.8-Flash-Next の GGUF ではない？）")

    pack = DATA / "packs" / f"sc117-{a.quant.lower()}"
    print(f"[2/3] パック: {pack}")
    if (pack / "native_experts.txt").exists() and (pack / "tokenizer" / "vocab.json").exists():
        say("作成済み（作り直すならこのフォルダを消してから再実行）")
    else:
        cmd = [sys.executable, str(ROOT / "tools" / "iq_pack.py"), "--gguf", str(first), "--out", str(pack)]
        if subprocess.call(cmd, env=env, cwd=str(ROOT)) != 0:
            say("そのままでは作れなかったので --compat-bf16（Orca と同じ変換）で作り直します")
            if subprocess.call(cmd + ["--compat-bf16"], env=env, cwd=str(ROOT)) != 0:
                sys.exit("パックを作れませんでした（上のエラーを見てください）")

    base_path, cfg = base_config(a.quant)
    print(f"[3/3] 起動設定（エンジンの設定は {base_path.name} から）")
    args = list(cfg["args"])
    set_arg(args, "--pack", pack)
    set_arg(args, "--native", first)
    set_arg(args, "--ple-gguf", ple)
    set_arg(args, "--max-context", a.context)
    set_arg(args, "--kv", a.kv)
    set_arg(args, "--compat-bf16", drop=True)
    for flag in ("--resident-experts", "--mmap-experts"):     # the low-RAM modes need an experts.bin this pack lacks
        set_arg(args, flag, drop=True)
    # from 64K the KV cache can live in RAM and only 32K positions stay in VRAM (what setup.py does when RAM allows)
    set_arg(args, "--kv-resident", 32768, drop=a.context < 65536)
    for flag in ("--rope-scaling", "--rope-scale"):
        set_arg(args, flag, drop=True)
    if a.context > 262144:
        sys.exit("262144 を超える文脈はここでは作りません（setup.py の rope scaling が必要）")
    cfg.update({"args": args, "tokenizer": str(pack / "tokenizer"),
                "model_name": f"sc117-qwen3.8-flash-next-abliterated-{a.quant.lower()}",
                "log": str(ROOT / f"sc117-{a.quant.lower()}.log")})
    out = HERE / f"sc117-{a.quant.lower()}.json"
    out.write_text(json.dumps(cfg, ensure_ascii=False, indent=1), encoding="utf-8")
    say(f"書きました: {out}")
    say(f"文脈 {a.context:,} トークン、KV {a.kv}" + ("、KV は RAM に置く（--kv-resident 32768）" if a.context >= 65536 else ""))
    print("準備完了。kk-files\\Strata-SC117.bat（またはデスクトップのショートカット）で起動できます。")


if __name__ == "__main__":
    main()
