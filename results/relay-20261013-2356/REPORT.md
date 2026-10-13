# 夜間ベンチ結果

実行: 2026-10-14 00:06〜

## 総合

| モデル | 文脈 | 長文 (見つけた事実) | 複数ファイル B | 完成度 C | 合計 | 平均 出力 tok/s |
|---|---|---|---|---|---|---|
| sc117-aider | 262144 | 0/0 | 14/24 | 6/41 | **20/65** | - |
| sc117 | 262144 | 0/0 | 41/41 | 41/41 | **82/82** | 42.7 |

## 長文（どこまで読めるか）

各段階で文書の 5%・25%・50%・75%・95% の位置に事実を1つずつ埋め、5つ全部答えられるかを見る。「文脈超過」の段階は総合の点数に含めない。

| モデル | 6K字 | 12K字 | 24K字 | 40K字 | 56K字 | 90K字 | 120K字 | 160K字 | 240K字 | 320K字 | 400K字 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| sc117-aider | - | - | - | - | - | - | - | - | - | - | - |
| sc117 | - | - | - | - | - | - | - | - | - | - | - |

## 課題ごと

| 課題 | sc117-aider | sc117 |
|---|---|---|
| B1_rename | 5/5 (51s) | 5/5 (22s) |
| B2_bugfix | 6/6 (96s) | 6/6 (37s) |
| B3_organize | 0/0 ⚠not_applicable (0s) | 17/17 (26s) |
| B4_aggregate | 0/4 (283s) | 4/4 (79s) |
| B5_configs | 3/3 (36s) | 3/3 (20s) |
| B6_crossdoc | 0/6 (75s) | 6/6 (21s) |
| C1_breakout | 0/14 (1993s) | 14/14 (88s) |
| C2_todo_app | 0/13 (1594s) | 13/13 (37s) |
| C3_cli_tool | 6/6 (286s) | 6/6 (36s) |
| C4_design_doc | 0/8 ⚠time_limit (1500s) | 8/8 (81s) |

## 詳細

### sc117-aider（文脈 262144、思考 aider architect）

- **B1_rename** 5/5: tests 4/4, old name left in: none
- **B2_bugfix** 6/6: tests 6/6
- **B3_organize** 0/0: Aider edits file contents; it cannot move files (shell commands are off)（停止理由: not_applicable）
- **B4_aggregate** 0/4: no summary.csv
- **B5_configs** 3/3: app.ini ok, deploy.yaml ok, db.json ok
- **B6_crossdoc** 0/6: found 0/6, wrong items 0, mentions fishing False
- **C1_breakout** 0/14: no game/index.html
- **C2_todo_app** 0/13: no todo/index.html
- **C3_cli_tool** 6/6: hidden inputs 3/3, own tests 4/4, usage message True
- **C4_design_doc** 0/8: no docs/design.md（停止理由: time_limit）

起動ログ（RAM・VRAM）:
```
[strata] experts loaded: 39.97 GiB at 5.07 GiB/s (18 s so far)
[strata] filling the GPU's expert cache (4693 experts, 7.62 GiB of VRAM) ...
ready: http://127.0.0.1:8085/v1  (OpenAI: /v1/chat/completions, Anthropic: /v1/messages, context 262144 tokens)
```

成果物: `sc117-aider/artifacts/`、作業フォルダ: `sc117-aider/work/`

### sc117（文脈 262144、思考 medium）

- **B1_rename** 5/5: tests 4/4, old name left in: none
- **B2_bugfix** 6/6: tests 6/6
- **B3_organize** 17/17: placed 15/15, index lists 15, left in inbox 0
- **B4_aggregate** 4/4: header True, totals True, order True (want [('日用品', 698517), ('家電', 696923)])
- **B5_configs** 3/3: app.ini ok, deploy.yaml ok, db.json ok
- **B6_crossdoc** 6/6: found 6/6, wrong items 0, mentions fishing False
- **C1_breakout** 14/14: static True, play 13/13 [] errors=[]
- **C2_todo_app** 13/13: files 3/3, checks 10/10; run 1 failed: [] []; run 2 failed: [] []
- **C3_cli_tool** 6/6: hidden inputs 3/3, own tests 6/6, usage message True
- **C4_design_doc** 8/8: sections 6/6, japanese chars 3353, table True, code block True, headings 26

起動ログ（RAM・VRAM）:
```
[strata] experts loaded: 39.97 GiB at 5.05 GiB/s (19 s so far)
[strata] filling the GPU's expert cache (4693 experts, 7.62 GiB of VRAM) ...
ready: http://127.0.0.1:8085/v1  (OpenAI: /v1/chat/completions, Anthropic: /v1/messages, context 262144 tokens)
```

成果物: `sc117/artifacts/`、作業フォルダ: `sc117/work/`

