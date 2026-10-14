"""kk-files/start_files.py - start Strata with the kk-files MCP server, so its chat (web page and chat.py) can work on
the files in one folder.  Strata-Files.bat calls this with the venv's Python.

    python kk-files/start_files.py --folder C:\\Users\\me\\work [--orca] [--read-only] [--config X.json] [--port 8080]

Writes kk-files/mcp-files.json (Claude Desktop's "mcpServers" format) and runs
serve/server.py --engine strata --config <config> --mcp-config kk-files/mcp-files.json --port N --open
in the foreground: closing the window stops the model, as with run-<model>.bat.
"""
from __future__ import annotations

import argparse
import glob
import json
import shutil
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def pick_config(orca: bool) -> str:
    if orca:
        return os.path.join(ROOT, "kk-orca", "orca-iq3_xxs.json")
    cands = [p for p in glob.glob(os.path.join(ROOT, "strata-*.json")) if not p.endswith(".shared-settings.json")]
    if not cands:
        sys.exit("[kk-files] no strata-<model>.json in %s: run Strata-Launch.bat once first" % ROOT)
    return max(cands, key=os.path.getmtime)          # setup touches the most recently used model's config


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--folder", required=True, help="the only folder the model may read and change")
    ap.add_argument("--orca", action="store_true", help="the Orca uncensored model (kk-orca/orca-iq3_xxs.json)")
    ap.add_argument("--config", help="a run config to use instead (default: the most recently used strata-*.json)")
    ap.add_argument("--read-only", action="store_true", help="the model may only list, read and search")
    ap.add_argument("--port", type=int, default=0, help="default: the config's port (8080)")
    ap.add_argument("--max-rounds", type=int, default=30,
                    help="tool calls the model may make in one answer (Strata's own default is 8)")
    ap.add_argument("--max-chars", type=int, default=0,
                    help="characters per read_file result (default: 6,000 / 12,000 / 18,000 for a 32K / 64K / 128K+ context)")
    a = ap.parse_args()
    folder = os.path.realpath(os.path.expanduser(a.folder.strip().strip('"')))
    if not os.path.isdir(folder):
        sys.exit("[kk-files] no such folder: " + folder)
    cfg_path = os.path.realpath(a.config) if a.config else pick_config(a.orca)
    if not os.path.isfile(cfg_path):
        sys.exit("[kk-files] no such config: " + cfg_path)
    with open(cfg_path, encoding="utf-8-sig") as f:
        cfg = json.load(f)
    port = a.port or cfg.get("port", 8080)
    ctx = int(cfg["args"][cfg["args"].index("--max-context") + 1]) if "--max-context" in cfg.get("args", []) else 32768
    # characters per read_file: small for a 32K context (the chat page resends every tool result), larger with more
    # room, but under 20,000 - Strata cuts any tool result past its max_result_chars (20,000 by default)
    max_chars = a.max_chars or (18000 if ctx >= 131072 else 12000 if ctx >= 65536 else 6000)
    args = [os.path.join(HERE, "files_mcp.py"), "--root", folder, "--max-chars", str(max_chars)] + \
        (["--read-only"] if a.read_only else [])
    # Strata reads mcp.max_rounds only from the run config: start it from a copy with the limit raised (the chat
    # settings saved next to the original config are carried over the first time)
    mcp_cfg = dict(cfg.get("mcp") or {})
    if a.max_rounds and mcp_cfg.get("max_rounds", 8) < a.max_rounds:
        mcp_cfg["max_rounds"] = a.max_rounds
        run_dir = os.path.join(HERE, "run")
        os.makedirs(run_dir, exist_ok=True)
        stem = os.path.splitext(os.path.basename(cfg_path))[0]
        run_cfg = os.path.join(run_dir, stem + ".json")
        with open(run_cfg, "w", encoding="utf-8") as f:
            json.dump(dict(cfg, mcp=mcp_cfg), f, ensure_ascii=False, indent=1)
        shared_src = os.path.splitext(cfg_path)[0] + ".shared-settings.json"
        shared_dst = os.path.join(run_dir, stem + ".shared-settings.json")
        if os.path.isfile(shared_src) and not os.path.exists(shared_dst):
            shutil.copy2(shared_src, shared_dst)
        cfg_path = run_cfg
    mcp_path = os.path.join(HERE, "mcp-files.json")
    with open(mcp_path, "w", encoding="utf-8") as f:
        json.dump({"mcpServers": {"files": {"command": sys.executable, "args": args}}}, f, ensure_ascii=False, indent=1)
    print("[kk-files] model : %s" % os.path.basename(cfg_path))
    print("[kk-files] folder: %s%s" % (folder, "  (read only)" if a.read_only else "  (read + write, overwritten files kept in .kk-backup/)"))
    print("[kk-files] context %d tokens, read_file up to %d characters per call, up to %d tool calls per answer"
          % (ctx, max_chars, mcp_cfg.get("max_rounds", 8)))
    print("[kk-files] chat  : the page that opens, or  .venv\\Scripts\\python.exe chat.py --port %d" % port)
    cmd = [sys.executable, os.path.join(ROOT, "serve", "server.py"), "--engine", "strata", "--config", cfg_path,
           "--mcp-config", mcp_path, "--port", str(port), "--open"]
    try:
        return subprocess.call(cmd, cwd=ROOT)
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    sys.exit(main())
