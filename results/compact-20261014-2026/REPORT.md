# 夜間ベンチ結果

実行: 2026-10-14 20:26〜

## 総合

| モデル | 文脈 | 長文 (見つけた事実) | 複数ファイル B | 完成度 C | 合計 | 平均 出力 tok/s |
|---|---|---|---|---|---|---|
| sc117-compact | 262144 | 0/0 | 0/0 | 0/0 | **17/20** | - |

## 長文（どこまで読めるか）

各段階で文書の 5%・25%・50%・75%・95% の位置に事実を1つずつ埋め、5つ全部答えられるかを見る。「文脈超過」の段階は総合の点数に含めない。

| モデル | 6K字 | 12K字 | 24K字 | 40K字 | 56K字 | 90K字 | 120K字 | 160K字 | 240K字 | 320K字 | 400K字 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| sc117-compact | - | - | - | - | - | - | - | - | - | - | - |

## 課題ごと

| 課題 | sc117-compact |
|---|---|
| K1_summary | 6/6 (22s) |
| K2_after_compact | 4/4 (81s) |
| K3_recall_compact | 0/3 (0s) |
| K2_after_baseline | 4/4 (60s) |
| K3_recall_baseline | 3/3 (0s) |

## 詳細

### sc117-compact（文脈 262144、思考 medium）

- **K1_summary** 6/6: 田中の担当 ok, app.ini の変更 ok, 9090 ok, out/ のルール ok, YYYY-MM-DD のルール ok, 長さ 4000 字以内 ok; 1202 chars; prompt 5030 -> 2151 tokens
- **K2_after_compact** 4/4: out/tanaka.md, items 6/6, YYYY-MM-DD 6/6, sorted True
- **K3_recall_compact** 0/3: app.ini NG, deploy.yaml NG, tanaka.md NG
- **K2_after_baseline** 4/4: out/tanaka.md, items 6/6, YYYY-MM-DD 6/6, sorted True
- **K3_recall_baseline** 3/3: app.ini ok, deploy.yaml ok, tanaka.md ok

起動ログ（RAM・VRAM）:
```
[strata] experts loaded: 39.97 GiB at 5.09 GiB/s (19 s so far)
[strata] filling the GPU's expert cache (4854 experts, 7.88 GiB of VRAM) ...
ready: http://127.0.0.1:8085/v1  (OpenAI: /v1/chat/completions, Anthropic: /v1/messages, context 262144 tokens)
```

成果物: `sc117-compact/artifacts/`、作業フォルダ: `sc117-compact/work/`

