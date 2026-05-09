"""
leaderboard.py
--------------
Shared module that renders LEADERBOARDS.md from full career totals + an optional
set of live overrides (for in-progress games). Imported by both compute_baseline.py
(initial render, no overrides) and track.py (live render every poll).
"""
import datetime as dt
import json
from pathlib import Path

STATS = ["PTS", "REB", "AST", "BLK", "STL", "FG3M", "TOV", "PF"]
STAT_TITLE = {
    "PTS": "Points", "REB": "Rebounds", "AST": "Assists",
    "BLK": "Blocks", "STL": "Steals", "FG3M": "Three-pointers",
    "TOV": "Turnovers", "PF": "Personal fouls",
}
STAT_ANCHOR = {
    "PTS": "points", "REB": "rebounds", "AST": "assists",
    "BLK": "blocks", "STL": "steals", "FG3M": "three-pointers",
    "TOV": "turnovers", "PF": "personal-fouls",
}
TOP_N = 200


def build_ranked_rows(all_totals, stat, overrides, active_pids_in_games):
    """
    Return list of dicts representing the top-N rows for a stat.

    all_totals       — {pid_str: {player_id, player_name, PTS, REB, ...}}
    overrides        — {pid_int: {stat_key: live_total, ...}}
    active_pids_in_games — set of pid_ints currently in an in-progress game
    """
    rows = []
    for v in all_totals.values():
        pid = v["player_id"]
        baseline_total = v[stat]
        live_total = overrides.get(pid, {}).get(stat)
        if live_total is not None:
            total = live_total
            delta = live_total - baseline_total
        else:
            total = baseline_total
            delta = 0
        rows.append({
            "player_id": pid,
            "player_name": v["player_name"],
            "total": total,
            "delta": delta,
            "is_live": pid in active_pids_in_games,
        })

    # Sort descending by total; tie-break by name for determinism
    rows.sort(key=lambda r: (-r["total"], r["player_name"]))

    # Apply standard "min" ranking — tied players share the same rank,
    # the next distinct value gets rank = position+1
    last_total = None
    last_rank = 0
    for i, r in enumerate(rows):
        if r["total"] != last_total:
            last_rank = i + 1
            last_total = r["total"]
        r["rank"] = last_rank

    # Trim to top-N, but keep all players tied with the cutoff value
    if len(rows) <= TOP_N:
        return rows
    cutoff_value = rows[TOP_N - 1]["total"]
    return [r for r in rows if r["total"] >= cutoff_value]


def format_row(r):
    name = f"**{r['player_name']}**" if r["is_live"] else r["player_name"]
    if r["is_live"]:
        if r["delta"] > 0:
            name = f"{name} 🔴 +{r['delta']}"
        else:
            name = f"{name} 🔴"
    return f"| {r['rank']} | {name} | {r['total']:,} |"


def render(all_totals, overrides, active_pids_in_games, out_path,
           last_updated_utc=None):
    """Write LEADERBOARDS.md to out_path."""
    last_updated_utc = last_updated_utc or dt.datetime.now(dt.timezone.utc)
    ts = last_updated_utc.strftime("%Y-%m-%d %H:%M UTC")

    lines = [
        "# WNBA All-Time Leaderboards",
        "",
        ("Top 200 in each tracked stat. Live in-game totals are reflected during "
         "game windows — players currently in an active game are marked "
         "**bold** with 🔴 and a today-delta. Auto-updated by the tracker workflow."),
        "",
        f"_Last updated: {ts}_",
        "",
        "## Contents",
        "",
    ]
    for stat in STATS:
        lines.append(f"- [{STAT_TITLE[stat]}](#{STAT_ANCHOR[stat]})")
    lines.append("")

    for stat in STATS:
        lines.append(f"## {STAT_TITLE[stat]}")
        lines.append("")
        lines.append("| Rank | Player | Total |")
        lines.append("|-----:|--------|------:|")
        rows = build_ranked_rows(all_totals, stat, overrides, active_pids_in_games)
        for r in rows:
            lines.append(format_row(r))
        lines.append("")

    Path(out_path).write_text("\n".join(lines))


def load_all_totals(path):
    return json.loads(Path(path).read_text())
