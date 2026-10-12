# kk-files: Strata の会話でローカルのファイルを扱う

Strata の会話（ブラウザのチャット画面と `chat.py`）から、**指定した1つのフォルダ**の中のファイルを読む・探す・書き換えるための MCP サーバーです。標準ライブラリだけで動き、Node.js は要りません。

## 使い方
1. `kk-files\Strata-Files.bat` をダブルクリックし、AI に触らせるフォルダを入力する。
   - `Strata-Files.bat "C:\Users\kiyom\work"`：フォルダを指定して起動
   - `Strata-Files.bat "C:\Users\kiyom\work" --orca`：Orca（無検閲版）で起動
   - `Strata-Files.bat "C:\Users\kiyom\work" --read-only`：読むだけ（書き込み系ツールを出さない）
2. 開いたチャット画面で「このフォルダに何がある？」「config.ini の port を 9090 にして」のように頼む。
   - 端末で話す場合は、別のウィンドウで `.venv\Scripts\python.exe chat.py` を実行する。
   - `chat.py` で `/tools off` と打つとツールを止められます（`/tools on` で戻す）。

起動時は `Strata-Launch.bat` と同じく、メモリを空けるために他のアプリを閉じます（`kk-close-apps.ps1`）。

## ツール
| ツール | 内容 |
|---|---|
| `list_dir` | フォルダの中身。`recursive=true` で下の階層まで全部 |
| `read_file` | テキストを読む。`start_line` / `end_line` で行範囲。UTF-8 と Shift_JIS に対応 |
| `search_text` | 文字列を含む行を探す |
| `write_file` | ファイルを新規作成、または全体を書き換える |
| `replace_text` | ファイルの一部だけを置き換える（文字コードはそのまま） |
| `move_file` | 移動・名前の変更（移動先が既にあると失敗） |
| `make_dir` | フォルダを作る |

## 安全のための決まり
- 指定フォルダの外には出られません（`..`・絶対パス・外へのリンクは拒否）。
- 上書きする前に、元のファイルを `<名前>.bak-年月日-時分秒` に残します。削除するツールはありません。
- ツールを呼ぶかどうかはモデルが決めます。ファイルの中に書かれた指示にモデルが従ってしまうこともあるので、大事なフォルダを丸ごと渡さず、作業用のフォルダを渡してください。心配なら `--read-only` で起動してください。
- MCP のツールは Strata 自身のチャット画面と `chat.py` からだけ使えます（他のサイトから送られた要求は Strata が拒否します）。

## 仕組み
`start_files.py` が `kk-files\mcp-files.json`（Claude Desktop と同じ `mcpServers` 形式）を書き、
`serve\server.py --engine strata --config <設定> --mcp-config kk-files\mcp-files.json --open` を起動します。
設定は、直近に使った `strata-*.json`（`--orca` のときは `kk-orca\orca-iq3_xxs.json`）です。
Strata が `files_mcp.py` を起動し、ツールを `files__read_file` のような名前でモデルに渡します（`docs/DETAILS.md` の「Tools from MCP servers」）。
