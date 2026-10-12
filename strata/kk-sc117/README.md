# kk-sc117: SC117 の無検閲 GSQ-RCO 版を Strata で試す

対象: [SC117/Qwen3.8-Flash-Next-GSQ-RCO-abliterated-GGUF](https://huggingface.co/SC117/Qwen3.8-Flash-Next-GSQ-RCO-abliterated-GGUF)
（Strata 標準の ISTA-DASLab GSQ-RCO 版の重みを残し、拒否に関わる投影だけを無検閲版から差し替えたもの）。

## 手順
1. **準備（1回だけ）**: `kk-sc117\SETUP-SC117.bat` をダブルクリック。
   - IQ3_XXS（約 76GB）を `Strata-data\sc117\IQ3_XXS\` にダウンロードし（止めても続きから再開）、
     パック `Strata-data\packs\sc117-iq3_xxs\` と起動設定 `kk-sc117\sc117-iq3_xxs.json` を作ります。
   - 別のサイズ・文脈: `SETUP-SC117.bat IQ2_XS 65536` のように指定（サイズは Q2_0 / IQ2_XS / IQ3_XXS / IQ3_S）。
   - トークンが要るリポジトリなら、HF のトークン（hf_...）をコピーしてから Enter、と聞かれます。
2. **ショートカット（1回だけ）**: `kk-files\Make-Shortcut-SC117.bat` → デスクトップに **Strata SC117 (files)**。
3. **起動**: ショートカットをダブルクリック（作業フォルダ `%USERPROFILE%\work`）。フォルダをドロップするとそのフォルダで起動。
   - IQ3_XXS 以外を使うときは、コマンドプロンプトで `set SC117=IQ2_XS` してから `kk-files\Strata-SC117.bat`。

## なぜ setup.py を使わないか
`START-HERE.bat --gguf-dir` に SC117 のファイルを渡すと、setup は標準の IQ3_XXS と同じ扱いにし、
既にある標準版のパック `packs/iq3_xxs` を**そのまま再利用**します。パックには SC117 が差し替えた投影の重みが入るので、
それでは無検閲化が効かないまま動いてしまいます。そこでパックは `packs/sc117-<サイズ>` に別に作ります。
エンジンの設定（GPU、VRAM の予約、MTP など）は、この PC で動いている標準版の設定（無ければ Orca）から写します。

## 確認すること
- 起動ログに `MCP server 'files': 7 tools` と、`model : sc117-iq3_xxs.json` が出るか。
- 速さ（Orca IQ3_XXS は約 58 トークン/秒）と、日本語の質、拒否しないか。
- パック作成で `--compat-bf16` に切り替わったと表示されたら、その旨を記録（GSQ-RCO 版なら不要のはず）。
- MTP（先読み）は元のモデルのものを使います。SC117 のリポジトリに専用の MTP が入っていれば、そちらの方が速い可能性があります。
