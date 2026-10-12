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
    a = ap.parse_args()
    folder = os.path.realpath(os.path.expanduser(a.folder.strip().strip('"')))
    if not os.path.isdir(folder):
        sys.exit("[kk-files] no such folder: " + folder)
    cfg_path = os.path.realpath(a.config) if a.config else pick_config(a.orca)
    if not os.path.isfile(cfg_path):
        sys.exit("[kk-files] no such config: " + cfg_path)
    with open(cfg_path, encoding="utf-8-sig") as f:
        port = a.port or json.load(f).get("port", 8080)
    args = [os.path.join(HERE, "files_mcp.py"), "--root", folder] + (["--read-only"] if a.read_only else [])
    mcp_path = os.path.join(HERE, "mcp-files.json")
    with open(mcp_path, "w", encoding="utf-8") as f:
        json.dump({"mcpServers": {"files": {"command": sys.executable, "args": args}}}, f, ensure_ascii=False, indent=1)
    print("[kk-files] model : %s" % os.path.basename(cfg_path))
    print("[kk-files] folder: %s%s" % (folder, "  (read only)" if a.read_only else "  (read + write, overwritten files kept as .bak-*)"))
    print("[kk-files] chat  : the page that opens, or  .venv\\Scripts\\python.exe chat.py --port %d" % port)
    cmd = [sys.executable, os.path.join(ROOT, "serve", "server.py"), "--engine", "strata", "--config", cfg_path,
           "--mcp-config", mcp_path, "--port", str(port), "--open"]
    try:
        return subprocess.call(cmd, cwd=ROOT)
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    sys.exit(main())
