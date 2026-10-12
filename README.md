# local-agent-bench

ローカルLLM（llama.cpp / Strata）に、ファイル操作5課題（T1〜T5）とブロック崩しの生成（T6）をさせるベンチ。
標準ライブラリのみの `agent.py` が OpenAI 互換 API（127.0.0.1）へツール呼び出しで接続します。

## 実行（Windows）
| ファイル | 内容 |
|---|---|
| `00_DIAG.bat` | 環境診断 |
| `01_RUN.bat` | T1〜T5 の実行 |
| `02_GAME_BENCH.bat` | 全構成（llama.cpp 4構成＋Strata 2構成）を各1時間上限で連続実行 |
| `03_GAME_BENCH_STRATA.bat` | Strata 2構成だけを実行（標準版・無検閲版 Orca、思考 `medium`） |

`02_game_bench.ps1 -Only "name1,name2"` で構成を絞れます。

## ツール
`list_dir` / `read_file` / `write_file` / `search_text` / `move_file`（すべて `sandbox/` 内に限定）。
`read_file` は `start_line` / `end_line`（1始まり・両端含む）で行範囲を読めます。20,000文字を超える部分は切り詰め、続きの開始行を結果に示します。

## Strata 構成
- `strata-qwen38-flash-next_medium`: `Strata\strata-iq3_xxs.json`
- `strata-orca-uncensored_medium`: `Strata\kk-orca\orca-iq3_xxs.json`
- `agent.py --effort medium` が `reasoning_effort` をリクエストに付けます（none / low / medium / high）。
- 起動時に `kk-close-apps.ps1`（Strata リポジトリ側）で他アプリを閉じます。実行前に作業を保存してください。

## 注意
- パスは `C:\Users\<user>\ai-models\...` 前提です。
- T6 の判定は `gameState` という文字列の有無だけを見る甘いものです。動作確認は別途、実際に動かして行ってください。
