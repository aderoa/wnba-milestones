"""
track.py
--------
Live WNBA milestone tracker. Called by GitHub Actions every 2 minutes during
game windows.

Flow:
  1. Pull today's WNBA games from ESPN scoreboard
  2. For each in-progress / recently-final game, pull the box score
  3. For each tracked active player, compute new career totals per stat
  4. Detect crossings:
       - rank passes inside top-200 leaderboards
       - rank ties (player's new total == an above-rank player's total)
       - round-hundred crossings (career total crosses a multiple of 100)
  5. Prepend any newly-fired milestones to MILESTONES.md and write to the
     GitHub Actions run summary
  6. Persist the fired set to data/fired_milestones.json (committed by workflow)

No external network beyond ESPN. No secrets needed.

Optional flags:
  --dry-run          Don't write anything, just print
  --force-game ID    Pull a specific ESPN event ID (for testing)
"""
import argparse
import datetime as dt
import json
import os
import sys
import unicodedata
import re
from pathlib import Path

import requests

# Allow importing leaderboard.py from same dir
sys.path.insert(0, str(Path(__file__).resolve().parent))
import leaderboard

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
LB_PATH = DATA / "leaderboards.json"
ET_PATH = DATA / "entering_totals.json"
ALL_PATH = DATA / "all_career_totals.json"
FIRED_PATH = DATA / "fired_milestones.json"
MILESTONES_LOG_PATH = DATA / "milestones_log.json"
LIVE_JSON_PATH = DATA / "leaderboards_live.json"
ID_MAP_PATH = DATA / "player_id_map.json"
UNMATCHED_PATH = DATA / "unmatched_names.json"
LOG_PATH = ROOT / "MILESTONES.md"
LB_MD_PATH = ROOT / "LEADERBOARDS.md"

STATS = ["PTS", "REB", "AST", "BLK", "STL", "FG3M", "TOV", "PF"]

# ESPN's box-score uses different short names. We translate.
ESPN_STAT_MAP = {
    "PTS": "PTS",
    "REB": "REB",
    "AST": "AST",
    "BLK": "BLK",
    "STL": "STL",
    "TO": "TOV",
    "PF": "PF",
    # "3PT" is special: string "made-attempted", parsed below.
}

ESPN_SCOREBOARD = "https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/scoreboard"
ESPN_SUMMARY = "https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/summary"

ACTIVE_STATUSES = {
    "STATUS_IN_PROGRESS", "STATUS_HALFTIME", "STATUS_END_PERIOD",
    "STATUS_FIRST_HALF", "STATUS_SECOND_HALF", "STATUS_END_OF_PERIOD",
    "STATUS_FINAL", "STATUS_FULL_TIME",
}

STAT_LABEL = {
    "PTS": "points", "REB": "rebounds", "AST": "assists",
    "BLK": "blocks", "STL": "steals", "FG3M": "three-pointers",
    "TOV": "turnovers", "PF": "fouls",
}


# ---------- name helpers ----------

def normalize_name(name):
    if not isinstance(name, str):
        return ""
    n = unicodedata.normalize("NFKD", name).encode("ASCII", "ignore").decode()
    n = n.lower()
    n = re.sub(r"\s+(jr|sr|ii|iii|iv)\.?\s*$", "", n)
    n = re.sub(r"[^a-z0-9\s]", "", n)
    n = re.sub(r"\s+", " ", n).strip()
    return n


# ---------- IO ----------

def load_json(path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        print(f"WARN: {path} malformed — treating as empty", file=sys.stderr)
        return default


def save_json(path, data):
    path.write_text(json.dumps(data, indent=2, default=str))


# ---------- ESPN ----------

def fetch_scoreboard():
    r = requests.get(ESPN_SCOREBOARD, timeout=20)
    r.raise_for_status()
    return r.json()


def fetch_summary(event_id):
    r = requests.get(ESPN_SUMMARY, params={"event": event_id}, timeout=20)
    r.raise_for_status()
    return r.json()


def list_active_games(scoreboard):
    out = []
    for ev in scoreboard.get("events", []):
        comp = (ev.get("competitions") or [{}])[0]
        status_type = (comp.get("status") or {}).get("type") or {}
        status_name = status_type.get("name", "")
        if status_name in ACTIVE_STATUSES:
            out.append({
                "id": str(ev.get("id")),
                "status": status_name,
                "short": ev.get("shortName"),
                "date": ev.get("date"),
                "status_detail": status_type.get("detail", ""),
            })
    return out


def parse_box_player(player_entry, names):
    """Pull our STATS dict out of one ESPN athlete entry."""
    stats_arr = player_entry.get("stats") or []
    if not stats_arr or len(stats_arr) != len(names):
        return None

    out = {}
    for our_key in STATS:
        if our_key == "FG3M":
            try:
                idx = names.index("3PT")
                made = stats_arr[idx].split("-")[0]
                out["FG3M"] = int(made) if made.lstrip("-").isdigit() else 0
            except (ValueError, IndexError):
                out["FG3M"] = 0
        else:
            espn_key = next((k for k, v in ESPN_STAT_MAP.items() if v == our_key), None)
            if espn_key is None:
                out[our_key] = 0
                continue
            try:
                idx = names.index(espn_key)
                v = stats_arr[idx]
                out[our_key] = int(v) if str(v).lstrip("-").isdigit() else 0
            except (ValueError, IndexError):
                out[our_key] = 0
    return out


def extract_player_lines(summary):
    """Yield (name, espn_id, stats_dict) for every player in the box."""
    box = summary.get("boxscore") or {}
    for team in box.get("players") or []:
        for stat_group in team.get("statistics") or []:
            names = stat_group.get("names") or []
            if "PTS" not in names:
                continue
            for ath in stat_group.get("athletes") or []:
                athlete = ath.get("athlete") or {}
                ath_name = athlete.get("displayName") or athlete.get("fullName")
                ath_id = str(athlete.get("id")) if athlete.get("id") else None
                if ath.get("didNotPlay") or not ath_name:
                    continue
                stats = parse_box_player(ath, names)
                if stats is None:
                    continue
                yield ath_name, ath_id, stats


def game_context(summary):
    """Short string like 'Q3 5:42 — NYL @ CON'."""
    header = summary.get("header") or {}
    comps = header.get("competitions") or []
    if not comps:
        return ""
    comp = comps[0]
    status = comp.get("status") or {}
    detail = (status.get("type") or {}).get("shortDetail") or ""
    competitors = comp.get("competitors") or []
    teams = []
    for c in competitors:
        abbr = (c.get("team") or {}).get("abbreviation")
        if abbr:
            teams.append(abbr)
    matchup = " @ ".join(reversed(teams)) if len(teams) == 2 else ""
    parts = [p for p in [detail, matchup] if p]
    return " — ".join(parts)


# ---------- crossing detection ----------

def round_hundred_crossings(prev_total, new_total):
    if new_total <= prev_total:
        return
    start = (prev_total // 100 + 1) * 100
    for v in range(start, new_total + 1, 100):
        yield v


def rank_pass_events(stat, leaderboard, player_id, prev_total, new_total):
    if new_total <= prev_total:
        return
    for entry in leaderboard:
        if entry["player_id"] == player_id:
            continue
        threshold = entry["total"]
        if prev_total < threshold and new_total == threshold:
            yield {
                "type": "tie", "stat": stat, "rank": entry["rank"],
                "passed_player": entry["player_name"],
                "passed_player_id": entry["player_id"],
                "threshold": threshold,
            }
        elif prev_total <= threshold and new_total > threshold:
            yield {
                "type": "pass", "stat": stat, "rank": entry["rank"],
                "passed_player": entry["player_name"],
                "passed_player_id": entry["player_id"],
                "threshold": threshold,
            }


def fired_key(player_id, stat, kind, value):
    return f"{player_id}:{stat}:{kind}:{value}"


# ---------- player matching ----------

def build_matcher(entering_totals):
    by_norm = {}
    by_pid = {}
    for v in entering_totals.values():
        by_pid[v["player_id"]] = v
        by_norm[v["norm_name"]] = v
    return by_norm, by_pid


def match_player(name, espn_id, by_norm, by_pid, id_map, unmatched):
    if espn_id and espn_id in id_map:
        pid = id_map[espn_id]
        return by_pid.get(pid)
    norm = normalize_name(name)
    if norm in by_norm:
        return by_norm[norm]
    parts = norm.split()
    if len(parts) >= 2:
        last_only = parts[-1]
        candidates = [v for k, v in by_norm.items() if k.endswith(" " + last_only)]
        if len(candidates) == 1:
            return candidates[0]
    unmatched.setdefault(name, espn_id)
    return None


# ---------- formatting ----------

def format_event_md(e):
    stat_name = STAT_LABEL.get(e["stat"], e["stat"])
    if e["kind"] == "rank_pass":
        # Backward compat: support both new `passed_players` (list) and
        # legacy `passed_player` (single string) from older events.
        players = e.get("passed_players") or (
            [e["passed_player"]] if e.get("passed_player") else []
        )
        if not players:
            line = json.dumps(e)
        else:
            if len(players) == 1:
                names = f"**{players[0]}**"
            elif len(players) == 2:
                names = f"**{players[0]}** and **{players[1]}**"
            else:
                names = (", ".join(f"**{p}**" for p in players[:-1])
                         + f", and **{players[-1]}**")
            line = (f"**{e['player']}** passed {names} for "
                    f"**#{e['rank']}** all-time in {stat_name} "
                    f"(career {e['new_total']:,})")
            line += _rank_movement_suffix(e)
    elif e["kind"] == "rank_tie":
        # Legacy events only — firing logic no longer creates ties.
        line = (f"**{e['player']}** tied **{e.get('passed_player', 'unknown')}** for "
                f"**#{e['rank']}** all-time in {stat_name} "
                f"(career {e['new_total']:,})")
        line += _rank_movement_suffix(e)
    elif e["kind"] == "round":
        line = (f"**{e['player']}** reached **{e['value']:,}** career "
                f"{stat_name} (now {e['new_total']:,})")
    else:
        line = json.dumps(e)
    if e.get("game_context"):
        line += f" — _{e['game_context']}_"
    return line


def _rank_movement_suffix(e):
    """Return ' — up from #X entering today' or similar, when applicable."""
    entering = e.get("entering_rank")
    new_rank = e.get("rank")
    if entering is None:
        # Player wasn't in top-200 at start of day — they just broke into it
        return " — new to top 200 today"
    if entering > new_rank:
        return f" — up from #{entering} entering today"
    return ""


def get_entering_rank(player_id, stat, leaderboards):
    """Return the player's pre-game rank in this stat, or None if outside top-200."""
    for entry in leaderboards.get(stat, []) or []:
        if entry["player_id"] == player_id:
            return entry["rank"]
    return None


INTRO = (
    "# WNBA Milestones\n\n"
    "Auto-updated by the tracker workflow. Newest entries at the top. "
    "Tracks top-200 rank passes/ties and every multiple of 100 in PTS, REB, "
    "AST, BLK, STL, 3PM, TOV, PF for active players.\n\n"
)


def prepend_log_block(events, polled_at_utc):
    """Prepend a new dated section to MILESTONES.md."""
    timestamp = polled_at_utc.strftime("%Y-%m-%d %H:%M UTC")
    new_block_lines = [f"## {timestamp}", ""]
    for e in events:
        new_block_lines.append(f"- {format_event_md(e)}")
    new_block_lines.append("")
    new_block = "\n".join(new_block_lines)

    if LOG_PATH.exists():
        existing = LOG_PATH.read_text()
        if existing.startswith("# WNBA Milestones"):
            idx = existing.find("\n## ")
            body = existing[idx + 1:] if idx != -1 else ""
        else:
            body = existing
    else:
        body = ""

    LOG_PATH.write_text(INTRO + new_block + "\n" + body)


_MD_SECTION_RE = re.compile(
    r'^## (\d{4}-\d{2}-\d{2} \d{2}:\d{2} UTC)\s*$', re.MULTILINE
)
_MD_BOLD_RE = re.compile(r'\*\*(.+?)\*\*')
_MD_ITALIC_RE = re.compile(r'_(.+?)_')


def parse_milestones_md(md_path):
    """
    Parse MILESTONES.md into a list of {ts, text} dicts, newest first.

    Used to derive milestones_log.json on every track.py run, ensuring the
    structured log always reflects the canonical markdown — including events
    from previous runs whose JSON file wasn't committed.

    Tie events (legacy from before the firing logic was changed) are filtered
    out so the dashboard only shows pass + round milestones.
    """
    if not md_path.exists():
        return []
    text = md_path.read_text()
    parts = _MD_SECTION_RE.split(text)
    # parts: [preamble, ts1, body1, ts2, body2, ...]
    events = []
    for i in range(1, len(parts), 2):
        ts_str = parts[i]
        body = parts[i + 1] if i + 1 < len(parts) else ""
        try:
            ts_iso = (dt.datetime.strptime(ts_str, "%Y-%m-%d %H:%M UTC")
                      .replace(tzinfo=dt.timezone.utc).isoformat())
        except ValueError:
            continue
        for line in body.splitlines():
            line = line.strip()
            if not line.startswith("- "):
                continue
            text_clean = line[2:]
            text_clean = _MD_BOLD_RE.sub(r'\1', text_clean)
            text_clean = _MD_ITALIC_RE.sub(r'(\1)', text_clean)
            # Skip tie events (legacy, no longer fired but remain in MD history)
            if " tied " in text_clean and " for #" in text_clean:
                continue
            events.append({"ts": ts_iso, "text": text_clean})
    return events


def write_job_summary(events, polled_at_utc, active_games):
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return
    lines = [
        f"## WNBA Milestones — {polled_at_utc.strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        f"Active/recent games this poll: **{len(active_games)}**",
        "",
    ]
    if active_games:
        for g in active_games:
            lines.append(f"- {g.get('short')} ({g.get('status')})")
        lines.append("")
    if events:
        lines.append(f"### {len(events)} new milestone(s)")
        lines.append("")
        for e in events:
            lines.append(f"- {format_event_md(e)}")
    else:
        lines.append("_No new milestones this poll._")
    lines.append("")
    with open(summary_path, "a") as f:
        f.write("\n".join(lines))


# ---------- main ----------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force-game", help="Force-poll a specific ESPN event ID")
    args = ap.parse_args()

    leaderboards = load_json(LB_PATH, {})
    entering = load_json(ET_PATH, {})
    all_totals = load_json(ALL_PATH, {})
    fired = set(load_json(FIRED_PATH, []))
    id_map = load_json(ID_MAP_PATH, {})
    unmatched = {}

    if not leaderboards or not entering or not all_totals:
        print("ERROR: missing baseline files. Run compute_baseline.py first.",
              file=sys.stderr)
        return 1

    by_norm, by_pid = build_matcher(entering)

    polled_at_utc = dt.datetime.now(dt.timezone.utc)

    if args.force_game:
        active_games = [{"id": args.force_game, "status": "FORCED",
                         "short": f"event {args.force_game}"}]
    else:
        sb = fetch_scoreboard()
        active_games = list_active_games(sb)

    print(f"Active/recent games: {len(active_games)}")
    for g in active_games:
        print(f"  - {g.get('short')} ({g.get('status')}) id={g['id']}")

    new_events = []
    # Live state for the leaderboard overlay
    live_overrides = {}        # {pid_int: {stat: live_total}}
    active_pids_in_games = set()  # players whose game is still in progress (🔴)
    in_progress_statuses = {
        "STATUS_IN_PROGRESS", "STATUS_HALFTIME", "STATUS_END_PERIOD",
        "STATUS_FIRST_HALF", "STATUS_SECOND_HALF", "STATUS_END_OF_PERIOD",
    }

    for g in active_games:
        try:
            summary = fetch_summary(g["id"])
        except Exception as exc:
            print(f"WARN: failed to fetch game {g['id']}: {exc}", file=sys.stderr)
            continue

        ctx = game_context(summary)
        is_in_progress = g.get("status") in in_progress_statuses

        for name, espn_id, stats in extract_player_lines(summary):
            rec = match_player(name, espn_id, by_norm, by_pid, id_map, unmatched)
            if rec is None:
                continue
            pid = rec["player_id"]

            # Build live override for the leaderboard view
            live_overrides[pid] = {
                stat: rec[stat] + stats.get(stat, 0) for stat in STATS
            }
            if is_in_progress:
                active_pids_in_games.add(pid)

            for stat in STATS:
                prev = rec[stat]
                new_total = prev + stats.get(stat, 0)
                if new_total <= prev:
                    continue

                # Round-hundred crossings
                for v in round_hundred_crossings(prev, new_total):
                    key = fired_key(pid, stat, "round", v)
                    if key in fired:
                        continue
                    fired.add(key)
                    new_events.append({
                        "kind": "round", "player": rec["player_name"],
                        "player_id": pid, "stat": stat,
                        "value": v, "new_total": new_total,
                        "game_context": ctx,
                    })

                # Rank passes — collect all passes for this (player, stat, tick)
                # into a single consolidated event. Ties are skipped entirely
                # (they were noise).
                lb = leaderboards.get(stat) or []
                # Look up start-of-day rank once per (player, stat) so we can
                # annotate the event with "up from #N entering today".
                entering_rank = get_entering_rank(pid, stat, leaderboards)
                passes_this_tick = []
                for ev in rank_pass_events(stat, lb, pid, prev, new_total):
                    if ev["type"] != "pass":
                        continue  # skip ties
                    key_val = f"pass_{ev['rank']}_{ev['passed_player_id']}"
                    key = fired_key(pid, stat, "rank_pass", key_val)
                    if key in fired:
                        continue
                    fired.add(key)
                    passes_this_tick.append(ev)

                if passes_this_tick:
                    # Best rank reached = lowest rank number among passes
                    best_rank = min(p["rank"] for p in passes_this_tick)
                    passed_names = [p["passed_player"] for p in passes_this_tick]
                    passed_ids = [p["passed_player_id"] for p in passes_this_tick]
                    new_events.append({
                        "kind": "rank_pass",
                        "player": rec["player_name"], "player_id": pid,
                        "stat": stat, "rank": best_rank,
                        "passed_players": passed_names,
                        "passed_player_ids": passed_ids,
                        "new_total": new_total,
                        "entering_rank": entering_rank,
                        "game_context": ctx,
                    })

    print(f"New milestones this poll: {len(new_events)}")
    for e in new_events:
        print(f"  - {format_event_md(e)}")

    if not args.dry_run:
        save_json(FIRED_PATH, sorted(fired))
        if unmatched:
            prev_um = load_json(UNMATCHED_PATH, {})
            prev_um.update(unmatched)
            save_json(UNMATCHED_PATH, prev_um)
        if new_events:
            prepend_log_block(new_events, polled_at_utc)
        # Derive milestones_log.json from MILESTONES.md so it always reflects
        # the canonical log — including any historical events from runs that
        # didn't commit the JSON file. Newest-first to match the dashboard's
        # expected order.
        recent_milestones = parse_milestones_md(LOG_PATH)
        save_json(MILESTONES_LOG_PATH, recent_milestones[:250])
        # Build the live game-state list (lightweight — just what the dashboard
        # needs to render the "live games" pill).
        active_games_view = [
            {
                "short": g.get("short"),
                "status": g.get("status_detail") or g.get("status"),
                "in_progress": g.get("status") in in_progress_statuses,
            }
            for g in active_games
        ]
        # Always re-render LEADERBOARDS.md (markdown) and the JSON snapshot used
        # by the live dashboard, so in-game progress is visible even between
        # discrete milestone fires.
        leaderboard.render(
            all_totals=all_totals,
            overrides=live_overrides,
            active_pids_in_games=active_pids_in_games,
            out_path=LB_MD_PATH,
            last_updated_utc=polled_at_utc,
            leaderboards=leaderboards,
        )
        leaderboard.render_live_json(
            all_totals=all_totals,
            overrides=live_overrides,
            active_pids_in_games=active_pids_in_games,
            active_games=active_games_view,
            recent_milestones=recent_milestones,  # already newest-first
            out_path=LIVE_JSON_PATH,
            last_updated_utc=polled_at_utc,
            leaderboards=leaderboards,
        )
        write_job_summary(new_events, polled_at_utc, active_games)

    if unmatched:
        print(f"Unmatched ESPN names: {list(unmatched.keys())}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
