# Strata (snapshot)

Snapshot of the Strata inference engine used in the LocalAgent game bench.

- Upstream: https://github.com/Niko1221/Strata (MIT, see `LICENSE`)
- Local version: v0.1.38 (HEAD 99f3dbd0)
- Includes the CLI chat mode (`chat.py`) and the web chat UI (`serve/web/`).
- Own additions: `kk-orca/` (Orca uncensored configs), `kk-bench/`, `kk-wiki/`, `kk-files/` (the chat can read and edit the files in one folder: `kk-files/Strata-Files.bat`, see `kk-files/README.md`), `kk-close-apps.ps1`, `Strata-Launch.bat`.
- Changed: `chat.py` asks the server for its MCP tools (`/tools on|off`) and shows each tool call.
- Not included: `.venv/`, `engine/` binaries, model files, logs.
