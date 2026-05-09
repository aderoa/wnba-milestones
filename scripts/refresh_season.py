"""
refresh_season.py
-----------------
Fetches the current WNBA season's player totals from stats.wnba.com (via the
nba_api package) and writes data/season_current.json. Intended to run once
per day after all games have finalized; the workflow then re-runs
compute_baseline.py to fold these totals into the leaderboards.

Why this exists: the historical CSV is frozen at end-of-2025-26, so without a
refresh, every poll's baseline remains 2025-26 forever. This script keeps the
"current-season delta" up to date so career totals stay correct as the year
progresses (and brand-new rookies get added).

Configurable via env or constants:
  CURRENT_SEASON   default "2026-27"  (WNBA's 2026 calendar season)
  WNBA_LEAGUE_ID   "10"

Network: hits stats.wnba.com only. No secrets.
"""
import json
import os
import sys
import time
import datetime as dt
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
SC_PATH = ROOT / "data" / "season_current.json"

CURRENT_SEASON = os.environ.get("CURRENT_SEASON", "2026-27")
WNBA_LEAGUE_ID = "10"

STATS = ["PTS", "REB", "AST", "BLK", "STL", "FG3M", "TOV", "PF"]


def fetch_totals(retries=4, base_timeout=90):
    """
    Pull LeagueDashPlayerStats with PerMode=Totals for the current season.
    Retries with exponential backoff — stats.wnba.com is occasionally flaky.
    Lets nba_api use its built-in headers (don't pass custom headers).
    """
    from nba_api.stats.endpoints import leaguedashplayerstats

    last_exc = None
    for attempt in range(1, retries + 1):
        try:
            print(f"Fetching LeagueDashPlayerStats (attempt {attempt})...")
            ep = leaguedashplayerstats.LeagueDashPlayerStats(
                league_id_nullable=WNBA_LEAGUE_ID,
                season=CURRENT_SEASON,
                season_type_all_star="Regular Season",
                per_mode_detailed="Totals",
                timeout=base_timeout,
            )
            df = ep.get_data_frames()[0]
            print(f"  → {len(df)} player rows")
            return df
        except Exception as exc:
            print(f"  attempt {attempt} failed: {exc}", file=sys.stderr)
            last_exc = exc
            if attempt < retries:
                sleep_s = min(2 ** attempt, 30)
                print(f"  sleeping {sleep_s}s before retry...")
                time.sleep(sleep_s)
    raise RuntimeError(f"Failed after {retries} attempts: {last_exc}")


def main():
    try:
        df = fetch_totals()
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    # Fail-safe: if we got 0 rows, write an empty file rather than blank the
    # whole baseline. This handles the season-not-started case gracefully.
    players = {}
    for _, r in df.iterrows():
        pid = int(r["PLAYER_ID"])
        try:
            players[str(pid)] = {
                "player_id": pid,
                "player_name": str(r["PLAYER_NAME"]),
                **{s: int(r[s]) for s in STATS},
            }
        except (KeyError, ValueError) as exc:
            # Defensive: nba_api column names occasionally drift. Surface the
            # bad row instead of silently dropping data.
            print(f"WARN: skipped row for player_id={pid}: {exc}", file=sys.stderr)

    out = {
        "season": CURRENT_SEASON,
        "as_of": dt.datetime.now(dt.timezone.utc).isoformat(),
        "row_count": len(players),
        "players": players,
    }
    SC_PATH.write_text(json.dumps(out, indent=2))
    print(f"Wrote {SC_PATH} (season={CURRENT_SEASON}, players={len(players)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
