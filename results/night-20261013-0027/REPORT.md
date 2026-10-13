# 夜間ベンチ結果

実行: 2026-10-13 00:40〜

## 総合

| モデル | 文脈 | 長文 (見つけた事実) | 複数ファイル B | 完成度 C | 合計 | 平均 出力 tok/s |
|---|---|---|---|---|---|---|
| orca | 65536 | 30/35 | 38/41 | 34/41 | **102/117** | 37.7 |
| sc117-swift | 65536 | 30/35 | 40/41 | 37/41 | **107/117** | 44.4 |
| sc117 | 65536 | 30/35 | 41/41 | 37/41 | **108/117** | 43.6 |
| strata-standard | 65536 | 30/35 | 41/41 | 36/41 | **107/117** | 43.9 |

## 長文（どこまで読めるか）

各段階で文書の 5%・25%・50%・75%・95% の位置に事実を1つずつ埋め、5つ全部答えられるかを見る。

| モデル | 6K字 | 12K字 | 24K字 | 40K字 | 56K字 | 90K字 | 120K字 |
|---|---|---|---|---|---|---|---|
| orca | 5/5 (4045tok, 初出力4.5s) | 5/5 (8026tok, 初出力5.1s) | 5/5 (15540tok, 初出力9.7s) | 5/5 (25232tok, 初出力17.4s) | 5/5 (35196tok, 初出力23.0s) | 5/5 (57186tok, 初出力33.2s) | 文脈超過 |
| sc117-swift | 5/5 (4045tok, 初出力3.6s) | 5/5 (8026tok, 初出力4.9s) | 5/5 (15540tok, 初出力9.3s) | 5/5 (25232tok, 初出力17.0s) | 5/5 (35196tok, 初出力22.2s) | 5/5 (57186tok, 初出力33.4s) | 文脈超過 |
| sc117 | 5/5 (4045tok, 初出力3.6s) | 5/5 (8026tok, 初出力4.9s) | 5/5 (15540tok, 初出力9.1s) | 5/5 (25232tok, 初出力16.8s) | 5/5 (35196tok, 初出力22.0s) | 5/5 (57186tok, 初出力33.0s) | 文脈超過 |
| strata-standard | 5/5 (4045tok, 初出力3.5s) | 5/5 (8026tok, 初出力4.9s) | 5/5 (15540tok, 初出力9.1s) | 5/5 (25232tok, 初出力16.8s) | 5/5 (35196tok, 初出力22.1s) | 5/5 (57186tok, 初出力32.8s) | 文脈超過 |

## 課題ごと

| 課題 | orca | sc117-swift | sc117 | strata-standard |
|---|---|---|---|---|
| B1_rename | 5/5 (28s) | 5/5 (24s) | 5/5 (22s) | 5/5 (22s) |
| B2_bugfix | 6/6 (46s) | 5/6 (44s) | 6/6 (41s) | 6/6 (37s) |
| B3_organize | 17/17 (28s) | 17/17 (25s) | 17/17 (25s) | 17/17 (24s) |
| B4_aggregate | 1/4 (494s) | 4/4 (82s) | 4/4 (79s) | 4/4 (94s) |
| B5_configs | 3/3 (34s) | 3/3 (16s) | 3/3 (18s) | 3/3 (19s) |
| B6_crossdoc | 6/6 (26s) | 6/6 (20s) | 6/6 (20s) | 6/6 (22s) |
| C1_breakout | 10/14 (71s) | 10/14 (61s) | 10/14 (70s) | 10/14 (57s) |
| C2_todo_app | 13/13 (42s) | 13/13 (56s) | 13/13 (88s) | 13/13 (41s) |
| C3_cli_tool | 4/6 (45s) | 6/6 (94s) | 6/6 (59s) | 5/6 (38s) |
| C4_design_doc | 7/8 (50s) | 8/8 (131s) | 8/8 (140s) | 8/8 (162s) |

## 詳細

### orca（文脈 65536、思考 medium）

- **B1_rename** 5/5: tests 4/4, old name left in: none
- **B2_bugfix** 6/6: tests 6/6
- **B3_organize** 17/17: placed 15/15, index lists 15, left in inbox 0
- **B4_aggregate** 1/4: header True, totals False, order False (want [('日用品', 698517), ('家電', 696923)])
- **B5_configs** 3/3: app.ini ok, deploy.yaml ok, db.json ok
- **B6_crossdoc** 6/6: found 6/6, wrong items 0, mentions fishing False
- **C1_breakout** 10/14: static True, play 9/13 ['right_moves_paddle', 'space_starts', 'ball_moves', 'lives_decrease_or_over'] errors=[]
- **C2_todo_app** 13/13: files 3/3, checks 10/10; run 1 failed: [] []; run 2 failed: [] []
- **C3_cli_tool** 4/6: hidden inputs 3/3, own tests 0/1, usage message True
- **C4_design_doc** 7/8: sections 6/6, japanese chars 1900, table True, code block True, headings 15

起動ログ（RAM・VRAM）:
```
[strata] experts loaded: 49.80 GiB at 5.00 GiB/s (24 s so far)
[strata] filling the GPU's expert cache (4318 experts, 8.75 GiB of VRAM) ...
ready: http://127.0.0.1:8085/v1  (OpenAI: /v1/chat/completions, Anthropic: /v1/messages, context 65536 tokens)
```

成果物: `orca/artifacts/`、作業フォルダ: `orca/work/`

### sc117-swift（文脈 65536、思考 medium）

- **B1_rename** 5/5: tests 4/4, old name left in: none
- **B2_bugfix** 5/6: tests 5/6
- **B3_organize** 17/17: placed 15/15, index lists 15, left in inbox 0
- **B4_aggregate** 4/4: header True, totals True, order True (want [('日用品', 698517), ('家電', 696923)])
- **B5_configs** 3/3: app.ini ok, deploy.yaml ok, db.json ok
- **B6_crossdoc** 6/6: found 6/6, wrong items 0, mentions fishing False
- **C1_breakout** 10/14: static True, play 9/13 ['left_moves_paddle', 'right_moves_paddle', 'ball_moves', 'lives_decrease_or_over'] errors=[]
- **C2_todo_app** 13/13: files 3/3, checks 10/10; run 1 failed: [] []; run 2 failed: [] []
- **C3_cli_tool** 6/6: hidden inputs 3/3, own tests 5/5, usage message True
- **C4_design_doc** 8/8: sections 6/6, japanese chars 3459, table True, code block True, headings 24

起動ログ（RAM・VRAM）:
```
[strata] experts loaded: 39.97 GiB at 4.18 GiB/s (20 s so far)
[strata] filling the GPU's expert cache (5198 experts, 8.43 GiB of VRAM) ...
ready: http://127.0.0.1:8085/v1  (OpenAI: /v1/chat/completions, Anthropic: /v1/messages, context 65536 tokens)
```

成果物: `sc117-swift/artifacts/`、作業フォルダ: `sc117-swift/work/`

### sc117（文脈 65536、思考 medium）

- **B1_rename** 5/5: tests 4/4, old name left in: none
- **B2_bugfix** 6/6: tests 6/6
- **B3_organize** 17/17: placed 15/15, index lists 15, left in inbox 0
- **B4_aggregate** 4/4: header True, totals True, order True (want [('日用品', 698517), ('家電', 696923)])
- **B5_configs** 3/3: app.ini ok, deploy.yaml ok, db.json ok
- **B6_crossdoc** 6/6: found 6/6, wrong items 0, mentions fishing False
- **C1_breakout** 10/14: static True, play 9/13 ['left_moves_paddle', 'right_moves_paddle', 'ball_moves', 'lives_decrease_or_over'] errors=[]
- **C2_todo_app** 13/13: files 3/3, checks 10/10; run 1 failed: [] []; run 2 failed: [] []
- **C3_cli_tool** 6/6: hidden inputs 3/3, own tests 6/6, usage message True
- **C4_design_doc** 8/8: sections 6/6, japanese chars 4929, table True, code block True, headings 34

起動ログ（RAM・VRAM）:
```
[strata] experts loaded: 39.97 GiB at 5.04 GiB/s (18 s so far)
[strata] filling the GPU's expert cache (4940 experts, 8.02 GiB of VRAM) ...
ready: http://127.0.0.1:8085/v1  (OpenAI: /v1/chat/completions, Anthropic: /v1/messages, context 65536 tokens)
```

成果物: `sc117/artifacts/`、作業フォルダ: `sc117/work/`

### strata-standard（文脈 65536、思考 medium）

- **B1_rename** 5/5: tests 4/4, old name left in: none
- **B2_bugfix** 6/6: tests 6/6
- **B3_organize** 17/17: placed 15/15, index lists 15, left in inbox 0
- **B4_aggregate** 4/4: header True, totals True, order True (want [('日用品', 698517), ('家電', 696923)])
- **B5_configs** 3/3: app.ini ok, deploy.yaml ok, db.json ok
- **B6_crossdoc** 6/6: found 6/6, wrong items 0, mentions fishing False
- **C1_breakout** 10/14: static True, play 9/13 ['left_moves_paddle', 'right_moves_paddle', 'ball_moves', 'lives_decrease_or_over'] errors=[]
- **C2_todo_app** 13/13: files 3/3, checks 10/10; run 1 failed: [] []; run 2 failed: [] []
- **C3_cli_tool** 5/6: hidden inputs 3/3, own tests 5/6, usage message True
- **C4_design_doc** 8/8: sections 6/6, japanese chars 3787, table True, code block True, headings 25

起動ログ（RAM・VRAM）:
```
[strata] experts loaded: 39.97 GiB at 5.09 GiB/s (17 s so far)
[strata] filling the GPU's expert cache (5083 experts, 8.25 GiB of VRAM) ...
ready: http://127.0.0.1:8085/v1  (OpenAI: /v1/chat/completions, Anthropic: /v1/messages, context 65536 tokens)
```

成果物: `strata-standard/artifacts/`、作業フォルダ: `strata-standard/work/`

