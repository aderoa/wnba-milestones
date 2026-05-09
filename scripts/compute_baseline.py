"""
compute_baseline.py
-------------------
One-shot baseline generator. Run this whenever the historical CSV updates
(or after a nightly 'finalize totals' step). Produces:

  data/leaderboards.json     Top-200 in each tracked stat (rank -> player+total)
  data/entering_totals.json  Career totals for active players (used by tracker)
  data/all_career_totals.json Full career totals for every player (used to
                              re-rank live during games)
  LEADERBOARDS.md            Rendered top-200 view (initial snapshot, no live overlay)
"""
import datetime as dt
import json
import sys
import unicodedata
import re
from pathlib import Path

import pandas as pd

# Allow importing from same dir when run from repo root
sys.path.insert(0, str(Path(__file__).resolve().parent))
import leaderboard

ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = ROOT / "data" / "_merged_base.csv"
SC_PATH = ROOT / "data" / "season_current.json"
LB_PATH = ROOT / "data" / "leaderboards.json"
ET_PATH = ROOT / "data" / "entering_totals.json"
ALL_PATH = ROOT / "data" / "all_career_totals.json"
LB_MD_PATH = ROOT / "LEADERBOARDS.md"
LIVE_JSON_PATH = ROOT / "data" / "leaderboards_live.json"
MILESTONES_LOG_PATH = ROOT / "data" / "milestones_log.json"

STATS = ["PTS", "REB", "AST", "BLK", "STL", "FG3M", "TOV", "PF"]
TOP_N = 200


def normalize_name(name: str) -> str:
    """Lowercase, strip diacritics, drop suffixes (Jr/Sr/II/III/IV) and punct."""
    if not isinstance(name, str):
        return ""
    n = unicodedata.normalize("NFKD", name).encode("ASCII", "ignore").decode()
    n = n.lower()
    n = re.sub(r"\s+(jr|sr|ii|iii|iv)\.?\s*$", "", n)
    n = re.sub(r"[^a-z0-9\s]", "", n)
    n = re.sub(r"\s+", " ", n).strip()
    return n


def load_season_current():
    """Return ({pid_int: {stats...}}, 'as_of' string) or ({}, None) if absent."""
    if not SC_PATH.exists():
        return {}, None
    try:
        data = json.loads(SC_PATH.read_text())
    except json.JSONDecodeError:
        print(f"WARN: {SC_PATH} malformed — ignoring", file=sys.stderr)
        return {}, None
    players = data.get("players") or {}
    out = {}
    for pid_str, v in players.items():
        try:
            out[int(pid_str)] = v
        except ValueError:
            continue
    return out, data.get("as_of")


def main() -> int:
    if not CSV_PATH.exists():
        print(f"ERROR: missing {CSV_PATH}", file=sys.stderr)
        return 1

    df = pd.read_csv(CSV_PATH)
    latest_csv_season = df["SEASON_LABEL"].max()
    # Cast to native int — pandas returns numpy.int64 from .unique() which
    # then leaks into JSON serialization downstream.
    csv_active_ids = {
        int(p) for p in
        df[df["SEASON_LABEL"] == latest_csv_season]["PLAYER_ID"].unique()
    }
    print(f"Latest season in CSV: {latest_csv_season}")
    print(f"Active in latest CSV season: {len(csv_active_ids)}")

    # ---- Career totals from CSV (frozen historical) ----
    csv_career = (
        df.groupby(["PLAYER_ID", "PLAYER_NAME"])[STATS]
        .sum()
        .reset_index()
    )
    csv_totals = {}
    for _, r in csv_career.iterrows():
        pid = int(r["PLAYER_ID"])
        csv_totals[pid] = {
            "player_id": pid,
            "player_name": str(r["PLAYER_NAME"]),
            **{s: int(r[s]) for s in STATS},
        }

    # ---- Current-season delta (refreshed daily by refresh_season.py) ----
    season_current, season_as_of = load_season_current()
    if season_current:
        print(f"Merging in season_current.json: {len(season_current)} players "
              f"(as of {season_as_of})")
    else:
        print("No season_current.json found — using CSV-only baseline")

    # ---- Merge: CSV historical + current-season delta ----
    # Union of player IDs across both sources (handles rookies in season_current
    # who don't exist in the CSV yet)
    all_pids = set(csv_totals) | set(season_current)
    merged = {}
    for pid in all_pids:
        csv_row = csv_totals.get(pid)
        sc_row = season_current.get(pid)
        # Pick the canonical name: CSV takes priority since it's our historical
        # source; fall back to season_current for rookies
        name = (csv_row or sc_row)["player_name"]
        merged[pid] = {
            "player_id": pid,
            "player_name": name,
            **{
                s: (csv_row[s] if csv_row else 0) + (sc_row[s] if sc_row else 0)
                for s in STATS
            },
        }

    # ---- Active set: latest CSV season ∪ players with current-season data ----
    active_ids = set(csv_active_ids)
    if season_current:
        active_ids |= set(season_current.keys())
    print(f"Active player set after merge: {len(active_ids)}")

    # ---- Leaderboards: top-N per stat ----
    leaderboards = {}
    sorted_pids = list(merged.keys())
    for stat in STATS:
        ranked = sorted(sorted_pids,
                        key=lambda p: (-merged[p][stat], merged[p]["player_name"]))
        rows = []
        for i, pid in enumerate(ranked[:TOP_N]):
            rows.append({
                "rank": i + 1,
                "player_id": pid,
                "player_name": merged[pid]["player_name"],
                "total": merged[pid][stat],
            })
        leaderboards[stat] = rows

    LB_PATH.write_text(json.dumps(leaderboards, indent=2))
    print(f"Wrote {LB_PATH} ({sum(len(v) for v in leaderboards.values())} rows)")

    # ---- Entering totals: every active player's career baseline ----
    entering = {}
    for pid in active_ids:
        if pid not in merged:
            continue
        m = merged[pid]
        entering[str(pid)] = {
            "player_id": pid,
            "player_name": m["player_name"],
            "norm_name": normalize_name(m["player_name"]),
            **{s: m[s] for s in STATS},
        }

    ET_PATH.write_text(json.dumps(entering, indent=2))
    print(f"Wrote {ET_PATH} ({len(entering)} active players)")

    # ---- Full career totals: every player, used for live re-ranking ----
    all_totals = {str(pid): m for pid, m in merged.items()}
    ALL_PATH.write_text(json.dumps(all_totals, indent=2))
    print(f"Wrote {ALL_PATH} ({len(all_totals)} players)")

    # ---- Initial LEADERBOARDS.md render (no live overlay) ----
    leaderboard.render(
        all_totals=all_totals,
        overrides={},
        active_pids_in_games=set(),
        out_path=LB_MD_PATH,
        last_updated_utc=dt.datetime.now(dt.timezone.utc),
    )
    print(f"Wrote {LB_MD_PATH}")

    # ---- Live JSON snapshot used by index.html (no live overlay) ----
    # Preserve any existing milestone history when regenerating
    recent = []
    if MILESTONES_LOG_PATH.exists():
        try:
            recent = json.loads(MILESTONES_LOG_PATH.read_text())
        except json.JSONDecodeError:
            recent = []
    leaderboard.render_live_json(
        all_totals=all_totals,
        overrides={},
        active_pids_in_games=set(),
        active_games=[],
        recent_milestones=list(reversed(recent)),
        out_path=LIVE_JSON_PATH,
        last_updated_utc=dt.datetime.now(dt.timezone.utc),
    )
    print(f"Wrote {LIVE_JSON_PATH}")

    # Spot-check Stewart
    stew = next((v for v in entering.values() if "stewart" in v["norm_name"]
                 and "breanna" in v["norm_name"]), None)
    if stew:
        print(f"Sanity: Breanna Stewart total PTS = {stew['PTS']}")
        rank15 = leaderboards["PTS"][14]
        print(f"        #15 all-time: {rank15['player_name']} = {rank15['total']}")
        print(f"        Gap to tie:   {rank15['total'] - stew['PTS']} pts")

    return 0


if __name__ == "__main__":
    sys.exit(main())
