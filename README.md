# wnba-milestones

Live milestone tracker + dynamic top-200 leaderboards for the WNBA. Polls
ESPN every 2 minutes during game windows.

Tracks **PTS, REB, AST, BLK, STL, FG3M, TOV, PF** for all active players,
detecting top-200 rank passes/ties and every multiple of 100 in career totals.

## 📊 Live dashboard

**[aderoa.github.io/wnba-milestones](https://aderoa.github.io/wnba-milestones/)** — auto-refreshing leaderboards with live in-game overlay and recent milestone events. The page reads `data/leaderboards_live.json` (regenerated every 2 min by the cron) and refreshes itself every 60 seconds.

For browsing the raw markdown artifacts directly on GitHub:

- **[LEADERBOARDS.md](LEADERBOARDS.md)** — markdown version of the rankings
- **[MILESTONES.md](MILESTONES.md)** — newest-first event log of fired milestones

## What gets surfaced

| File | What it shows | Updates |
|------|---------------|---------|
| `index.html` | The dashboard rendered from `data/leaderboards_live.json` | Each cron tick (auto-refresh on the page every 60s) |
| `MILESTONES.md` | Discrete milestone events (Stewart passed Jackson, Bonner hit 7,800 reb) — newest at top | Each poll that fires anything new |
| `LEADERBOARDS.md` | Current top-200 in each stat with **live in-game totals** for players currently playing (🔴 + delta) | Every poll, regardless of milestones |
| `data/leaderboards_live.json` | Compact JSON snapshot used by the dashboard | Every poll |
| `data/milestones_log.json` | Structured event log (last 250 fires) | Each poll that fires anything |
| `data/fired_milestones.json` | Dedup ledger (just keys) | Each poll |
| Actions tab job summary | Per-tick view: active games + new milestones | Every poll |

## Architecture

```
data/_merged_base.csv          historical career CSV (frozen, refresh occasionally)
data/season_current.json       current-season totals from stats.wnba.com (refreshed daily)
       │
       ▼
scripts/compute_baseline.py    merges CSV historical + current-season delta
       │
       ├──▶ data/leaderboards.json        top-200 per stat (used by milestone detector)
       ├──▶ data/entering_totals.json     active players' career totals
       ├──▶ data/all_career_totals.json   every player's career totals (for live re-rank)
       └──▶ LEADERBOARDS.md                rendered top-200 (no live overlay)
                          │
                          ▼
   scripts/track.py  ◀───────  GH Actions cron every 2 min during games
       │  (pulls ESPN scoreboard + summary)
       │
       ├──▶ MILESTONES.md                 discrete events (newest at top, committed)
       ├──▶ LEADERBOARDS.md                re-rendered every poll w/ live overlay
       ├──▶ data/fired_milestones.json    dedup ledger (committed)
       ├──▶ data/unmatched_names.json     ESPN names we couldn't match (audit)
       └──▶ GitHub Actions job summary    per-run snapshot

scripts/refresh_season.py      runs once daily — fetches stats.wnba.com → season_current.json
scripts/leaderboard.py         shared rendering helper
```

Two cron workflows:

- **`wnba_milestones.yml`** — every 2 min during game windows (22:00 UTC – 06:00 UTC),
  polls ESPN, detects crossings, updates `MILESTONES.md` + `LEADERBOARDS.md`.
- **`refresh_season.yml`** — once daily at 11:00 UTC (after games end, before the
  next day's games start), pulls current-season totals from stats.wnba.com and
  regenerates baseline files.

No secrets. No external storage beyond this repo.

## Setup

1. Create the repo (`aderoa/wnba-milestones`) and push these files.
2. **Enable GitHub Pages** — Settings → Pages → Branch: `main`, folder: `/ (root)`. Save. After ~1 minute, the dashboard will be live at `https://<your-username>.github.io/wnba-milestones/`.
3. **Smoke test** — Actions tab → "WNBA Milestones Tracker" → "Run workflow"
   with `dry_run = true`. Should finish without error and print active games
   in the run log.
4. **Live test** — once today's games tip off (4:30 PT for NYL @ CON), trigger
   another run without `dry_run`. The dashboard will start showing live deltas
   on the next page refresh (auto every 60s, or hard-refresh).
5. Cron takes over from there: `*/2 22-23 * * *` and `*/2 0-5 * * *` UTC for
   the live tracker, plus a daily `0 11 * * *` UTC for the season refresh.

## Maintenance

### Daily season refresh (automatic)

The `refresh_season.yml` workflow runs daily at 11:00 UTC. It calls
`scripts/refresh_season.py` which hits `stats.wnba.com` via `nba_api`, pulls
`LeagueDashPlayerStats` totals for the current season (default `2026-27`), and
writes `data/season_current.json`. Then `compute_baseline.py` regenerates
everything (leaderboards, entering totals, full career totals, LEADERBOARDS.md)
by combining the frozen CSV with that fresh delta.

This means:

- **Rookies** appearing in stats.wnba.com but not in the CSV are auto-added to
  the active set on the next refresh. No manual intervention needed.
- **Returning vets** have their career totals automatically updated to include
  the current season's contribution.
- **Stat corrections** propagate: if the WNBA retroactively adjusts a stat,
  the next daily refresh picks it up.

### Refreshing the historical CSV (rare)

Only needed when the full historical record changes — e.g., once per offseason
when last year's stats are finalized, or if you discover an error in older
data. Replace `data/_merged_base.csv` with the new export from your existing
pipeline, then push. `compute_baseline.py` will run on the next daily refresh
or you can trigger it manually.

### Manual season override

If you need to point at a different season (e.g., to backfill 2025-26 corrections,
or testing), trigger `refresh_season.yml` manually with the `season` input set
to e.g. `2025-26`.

### Player name matching

ESPN and stats.wnba.com use different player IDs. We match by normalized name
(lowercase, no diacritics, no Jr/Sr/II/III/IV suffixes). Unmatched names land
in `data/unmatched_names.json` for audit. To pin a stubborn case, edit
`data/player_id_map.json`:

```json
{
  "<espn_athlete_id>": <stats_wnba_player_id>
}
```

### Adjusting the tracked stats

Edit `STATS = [...]` at the top of `scripts/compute_baseline.py` and
`scripts/track.py`, then re-run `compute_baseline.py`. If you want a stat
universe change to retroactively re-evaluate existing fires, also clear
`data/fired_milestones.json`.

## Files

| Path | Purpose |
|------|---------|
| `MILESTONES.md` | Newest-first event log of fired milestones |
| `LEADERBOARDS.md` | Top-200 per stat with live in-game overlay |
| `.github/workflows/wnba_milestones.yml` | Live tracker cron (every 2 min, game windows) |
| `.github/workflows/refresh_season.yml` | Daily season refresh (11:00 UTC) |
| `scripts/compute_baseline.py` | Merge CSV + season delta, regenerate baselines |
| `scripts/refresh_season.py` | Daily fetch from stats.wnba.com via nba_api |
| `scripts/track.py` | Live ESPN poll, crossing detection, log writer |
| `scripts/leaderboard.py` | Shared markdown rendering |
| `data/_merged_base.csv` | Historical career data input (frozen, occasional refresh) |
| `data/season_current.json` | Current season's totals (refreshed daily) |
| `data/leaderboards.json` | Top-200 per stat (regenerated) |
| `data/entering_totals.json` | Active player career totals (regenerated) |
| `data/all_career_totals.json` | All players' career totals (regenerated) |
| `data/fired_milestones.json` | Dedup ledger (auto-committed) |
| `data/unmatched_names.json` | ESPN names that didn't match (audit) |
| `data/player_id_map.json` | Manual ESPN→stats overrides (optional) |

## Known limitations

- **stats.wnba.com flakiness** — the daily refresh sometimes fails or times
  out. `refresh_season.py` retries 4× with exponential backoff before giving
  up. If a daily run fails, the leaderboard stays at yesterday's totals until
  the next successful run; manually re-trigger `refresh_season.yml` to recover
  faster.
- **Season-string format** — defaults to `2026-27`. If `nba_api` rejects that
  format mid-season (it's been finicky historically), override via the
  workflow's `season` input or the `CURRENT_SEASON` env var.
- **GH Actions cron drift** — scheduled runs are best-effort and can be 5–15
  min late under load. If you want sub-minute fidelity for the live tracker,
  move to the Cloudflare Worker cron path.
- **Stat corrections within the live window** — if a box score is corrected
  during the same game, we don't un-fire a milestone. The next daily refresh
  rebases on stats.wnba.com so the leaderboard self-corrects, but
  `MILESTONES.md` would show a now-incorrect entry.
- **Player name collisions** — two active players sharing a normalized name
  would route to the first match. Add an entry to `player_id_map.json` if so.
