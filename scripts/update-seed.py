#!/usr/bin/env python3
"""Refresh games-seed.json.gz, the offline copy of Discord's game list shipped in releases."""

import gzip
import json
import os
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import bluestacks_discord_presence as bdp  # noqa: E402

req = urllib.request.Request(bdp.DETECTABLE_URL, headers={"User-Agent": "bluestacks-discord-presence"})
with urllib.request.urlopen(req, timeout=60) as resp:
    games = bdp.build_games(json.load(resp))

out = os.path.join(ROOT, "games-seed.json.gz")
with gzip.open(out, "wt", compresslevel=9) as f:
    json.dump(games, f, separators=(",", ":"))
print(f"wrote {out}: {len(games['packages'])} Play Store IDs, {len(games['names'])} names")
