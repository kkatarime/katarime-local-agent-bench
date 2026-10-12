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
| `05_NIGHT_BENCH.bat` | 夜間ベンチ：Strata の全モデル（SC117 Swift・Orca・SC117・標準）を各2時間上限で連続実行し、`logs\night\<日時>\REPORT.md` に比較表を出す |

`02_game_bench.ps1 -Only "name1,name2"` で構成を絞れます。

## ツール
`list_dir` / `read_file` / `write_file` / `search_text` / `move_file`（すべて `sandbox/` 内に限定）。
`read_file` は `start_line` / `end_line`（1始まり・両端含む）で行範囲を読めます。20,000文字を超える部分は切り詰め、続きの開始行を結果に示します。

## Strata の会話でファイルを扱う
`strata\kk-files\Strata-Files.bat` で、Strata のチャット（ブラウザ画面と `strata\chat.py`）から指定フォルダのファイルを読み書きできます。詳しくは `strata/kk-files/README.md`。

## 夜間ベンチ（`night_bench.py`）
課題はすべて、モデルが残したファイルで採点します（モデルの自己申告は見ません）。
- **L 長文**: 6千〜12万字の文書の 5%・25%・50%・75%・95% の位置に事実を埋め、5つ答えられるか。実際のトークン数・最初の出力までの秒数・読み込み速度も記録。文脈を超える長さは「文脈超過」。
- **B 複数ファイル**: 複数モジュールにまたがる改名（隠しテストで確認）、バグ修正（テストが全部通るか）、15ファイルの仕分け、12個のCSVの集計、3形式の設定ファイル編集、8つの議事録からの抽出。
- **C 完成度**: ブロック崩し（ヘッドレスの Edge で実際に操作：パドル・発射・落下・R でやり直し・JS エラー）、3ファイル構成の TODO アプリ（追加・Enter・完了・削除・件数・再読み込み後の復元）、CLI ツール（隠し入力で出力を照合＋自作テスト）、設計書（見出し・表・コード・分量）。
- 各課題の作業フォルダ（`work/`）と成果物（`artifacts/`）は残るので、朝に実物を開いて確かめられます。
- 文脈は 64K で起動を試し、起動できなければそのモデルの設定の長さ（32K）でやり直します（`-Ctx 0` で設定のまま）。
- `python night_bench.py selftest` で、模範解答に満点・空の回答に0点が付くことを、モデル無しで確かめられます（Edge/Chrome が必要）。

## Strata 構成
- `strata-qwen38-flash-next_medium`: `Strata\strata-iq3_xxs.json`
- `strata-orca-uncensored_medium`: `Strata\kk-orca\orca-iq3_xxs.json`
- `agent.py --effort medium` が `reasoning_effort` をリクエストに付けます（none / low / medium / high）。
- 起動時に `kk-close-apps.ps1`（Strata リポジトリ側）で他アプリを閉じます。実行前に作業を保存してください。

## 注意
- パスは `C:\Users\<user>\ai-models\...` 前提です。
- T6 の判定は `gameState` という文字列の有無だけを見る甘いものです。動作確認は別途、実際に動かして行ってください。
