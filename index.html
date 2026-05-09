<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>WNBA Milestones · HoopsMatic</title>
<meta name="description" content="Live top-200 WNBA career leaderboards across 8 stats with in-game overlay and milestone tracking.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@500;600;700&display=swap" rel="stylesheet">
<style>
  :root {
    --bg: #fafafa;
    --bg-elev: #ffffff;
    --bg-table-head: #f3f4f6;
    --bg-live-row: #fef2f2;
    --text: #111827;
    --text-soft: #4b5563;
    --muted: #6b7280;
    --border: #e5e7eb;
    --border-strong: #d1d5db;
    --accent: #b45309;
    --live: #dc2626;
    --pass: #047857;
    --header-font: 'JetBrains Mono', ui-monospace, 'SF Mono', Menlo, monospace;
    --body-font: 'Inter', system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
  }

  * { box-sizing: border-box; }
  html, body { margin: 0; padding: 0; }
  body {
    background: var(--bg);
    color: var(--text);
    font-family: var(--body-font);
    font-size: 15px;
    line-height: 1.5;
    -webkit-font-smoothing: antialiased;
  }

  .container { max-width: 980px; margin: 0 auto; padding: 28px 18px 64px; }

  header { margin-bottom: 18px; }
  .brand {
    font-family: var(--header-font);
    font-size: 0.62rem;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: var(--muted);
    font-weight: 600;
  }
  h1 {
    font-family: var(--header-font);
    font-size: 1.6rem;
    font-weight: 700;
    margin: 4px 0 4px;
    letter-spacing: -0.01em;
  }
  .subtitle { color: var(--text-soft); font-size: 0.92rem; margin-bottom: 0; }
  .subtitle code { font-family: var(--header-font); font-size: 0.85em; color: var(--text); }

  .live-bar {
    background: var(--bg-elev);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 12px 14px;
    font-size: 0.88rem;
    margin: 18px 0 22px;
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    align-items: center;
  }
  .live-pulse {
    display: inline-block;
    width: 8px; height: 8px;
    background: var(--live);
    border-radius: 50%;
    animation: pulse 1.5s ease-in-out infinite;
  }
  @keyframes pulse { 0%,100% { opacity: 1; transform: scale(1); } 50% { opacity: 0.45; transform: scale(0.85); } }
  .game-pill {
    background: var(--bg-table-head);
    padding: 4px 10px;
    border-radius: 6px;
    font-family: var(--header-font);
    font-size: 0.78rem;
    color: var(--text-soft);
  }
  .game-pill .status { color: var(--live); margin-left: 4px; font-weight: 600; }

  .tabs {
    display: flex; gap: 6px; flex-wrap: wrap;
    margin-bottom: 14px;
  }
  .tab {
    font-family: var(--header-font);
    font-size: 0.62rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    padding: 9px 13px;
    border: 1px solid var(--border);
    border-radius: 7px;
    background: var(--bg-elev);
    cursor: pointer;
    color: var(--muted);
    transition: all 0.12s;
    user-select: none;
  }
  .tab:hover { color: var(--text); border-color: var(--border-strong); }
  .tab.active {
    background: var(--text);
    color: var(--bg-elev);
    border-color: var(--text);
  }

  .table-wrap {
    background: var(--bg-elev);
    border: 1px solid var(--border);
    border-radius: 10px;
    overflow: hidden;
  }
  table { width: 100%; border-collapse: collapse; }
  thead th {
    background: var(--bg-table-head);
    font-family: var(--header-font);
    font-size: 0.62rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    text-align: left;
    padding: 11px 14px;
    color: var(--muted);
    border-bottom: 1px solid var(--border);
    position: sticky; top: 0;
  }
  thead th.right { text-align: right; }
  tbody td {
    padding: 9px 14px;
    font-size: 0.92rem;
    border-bottom: 1px solid var(--border);
    color: var(--text);
  }
  tbody tr:last-child td { border-bottom: none; }
  tbody tr.live { background: var(--bg-live-row); }
  tbody tr.live td { font-weight: 600; }
  td.rank {
    font-family: var(--header-font);
    color: var(--muted);
    width: 56px;
    text-align: right;
    padding-right: 18px;
    font-weight: 500;
  }
  tr.live td.rank { color: var(--text); }
  td.total {
    font-family: var(--header-font);
    font-weight: 600;
    text-align: right;
    width: 110px;
    color: var(--text);
  }
  .live-marker { color: var(--live); margin-left: 8px; font-size: 0.75rem; }
  .delta {
    color: var(--accent);
    font-family: var(--header-font);
    font-size: 0.78rem;
    margin-left: 6px;
    font-weight: 600;
  }

  .section-title {
    font-family: var(--header-font);
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--muted);
    font-weight: 600;
    margin: 36px 0 12px;
  }
  .milestones-list { display: flex; flex-direction: column; gap: 6px; }
  .milestone-item {
    background: var(--bg-elev);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 10px 14px;
    font-size: 0.9rem;
    line-height: 1.4;
  }
  .milestone-ts {
    color: var(--muted);
    font-family: var(--header-font);
    font-size: 0.7rem;
    margin-bottom: 2px;
  }
  .milestone-text strong {
    font-weight: 600;
    color: var(--text);
  }

  .meta-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 8px;
    color: var(--muted);
    font-size: 0.78rem;
    font-family: var(--header-font);
    margin-bottom: 14px;
  }
  .meta-row .refreshing {
    display: inline-flex;
    align-items: center;
    gap: 6px;
  }
  .spinner {
    width: 10px; height: 10px;
    border: 2px solid var(--border-strong);
    border-top-color: var(--text);
    border-radius: 50%;
    animation: spin 0.7s linear infinite;
  }
  @keyframes spin { to { transform: rotate(360deg); } }

  footer {
    margin-top: 56px;
    padding-top: 18px;
    border-top: 1px solid var(--border);
    color: var(--muted);
    font-size: 0.78rem;
    text-align: center;
  }
  footer a { color: var(--text-soft); text-decoration: none; }
  footer a:hover { text-decoration: underline; }

  .empty-state {
    padding: 40px 20px;
    text-align: center;
    color: var(--muted);
    font-size: 0.92rem;
  }
  .error-state { color: var(--live); }

  @media (max-width: 600px) {
    .container { padding: 20px 12px 48px; }
    h1 { font-size: 1.3rem; }
    td.total { width: 80px; font-size: 0.85rem; }
    tbody td { padding: 8px 10px; font-size: 0.85rem; }
    thead th { padding: 9px 10px; }
    td.rank { padding-right: 10px; width: 42px; }
  }
</style>
</head>
<body>
<div class="container">

<header>
  <div class="brand">HoopsMatic / WNBA Milestones</div>
  <h1>WNBA All-Time Leaderboards</h1>
  <p class="subtitle">Live top-200 in <code>PTS · REB · AST · BLK · STL · 3PM · TOV · PF</code>. Active in-game players are flagged with their today-delta.</p>
</header>

<div class="live-bar" id="live-bar">
  <span style="color:var(--muted)">Loading game state…</span>
</div>

<div class="meta-row">
  <span id="last-updated">—</span>
  <span class="refreshing" id="refreshing"><span class="spinner"></span> auto-refresh 60s</span>
</div>

<div class="tabs" id="tabs"></div>

<div class="table-wrap">
  <table>
    <thead>
      <tr>
        <th class="right">Rank</th>
        <th>Player</th>
        <th class="right">Career total</th>
      </tr>
    </thead>
    <tbody id="rows">
      <tr><td colspan="3" class="empty-state">Loading rankings…</td></tr>
    </tbody>
  </table>
</div>

<h2 class="section-title">Recent milestones</h2>
<div id="milestones-list" class="milestones-list">
  <div class="empty-state" style="padding:24px;border:1px solid var(--border);border-radius:8px;background:var(--bg-elev)">
    None yet — milestones will appear here as players cross thresholds.
  </div>
</div>

<footer>
  <a href="https://github.com/aderoa/wnba-milestones" target="_blank" rel="noopener">github.com/aderoa/wnba-milestones</a>
  · auto-updated by GitHub Actions
</footer>
</div>

<script>
const STATS = ['PTS', 'REB', 'AST', 'BLK', 'STL', 'FG3M', 'TOV', 'PF'];
const TITLES = {
  PTS: 'Points', REB: 'Rebounds', AST: 'Assists', BLK: 'Blocks',
  STL: 'Steals', FG3M: 'Three-pointers', TOV: 'Turnovers', PF: 'Fouls'
};

let currentStat = (location.hash || '').replace('#', '').toUpperCase();
if (!STATS.includes(currentStat)) currentStat = 'PTS';
let liveData = null;

function fmt(n) { return n.toLocaleString(); }

function renderTabs() {
  const el = document.getElementById('tabs');
  el.innerHTML = STATS.map(s =>
    `<div class="tab ${s === currentStat ? 'active' : ''}" data-stat="${s}">${TITLES[s]}</div>`
  ).join('');
  el.querySelectorAll('.tab').forEach(t => {
    t.addEventListener('click', () => {
      currentStat = t.dataset.stat;
      history.replaceState(null, '', '#' + currentStat);
      renderTabs();
      renderTable();
    });
  });
}

function renderTable() {
  const tbody = document.getElementById('rows');
  if (!liveData || !liveData.stats || !liveData.stats[currentStat]) {
    tbody.innerHTML = '<tr><td colspan="3" class="empty-state">No data for this stat.</td></tr>';
    return;
  }
  const rows = liveData.stats[currentStat].rows;
  tbody.innerHTML = rows.map(r => {
    let nameCell = r.name;
    if (r.live) {
      nameCell += '<span class="live-marker">🔴</span>';
      if (r.delta > 0) nameCell += `<span class="delta">+${r.delta}</span>`;
    }
    return `<tr class="${r.live ? 'live' : ''}">
      <td class="rank">${r.rank}</td>
      <td>${nameCell}</td>
      <td class="total">${fmt(r.total)}</td>
    </tr>`;
  }).join('');
}

function renderLiveBar() {
  const el = document.getElementById('live-bar');
  if (!liveData) return;
  const games = (liveData.active_games || []).filter(g => g.in_progress);
  if (games.length === 0) {
    el.innerHTML = '<span style="color:var(--muted)">No games currently in progress.</span>';
    return;
  }
  el.innerHTML = `<span class="live-pulse"></span>
    <strong>${games.length} live game${games.length > 1 ? 's' : ''}</strong>
    ${games.map(g => `<span class="game-pill">${g.short || '—'}<span class="status">${g.status || ''}</span></span>`).join('')}`;
}

function renderMilestones() {
  const el = document.getElementById('milestones-list');
  const list = liveData && liveData.recent_milestones || [];
  if (list.length === 0) {
    el.innerHTML = `<div class="empty-state" style="padding:24px;border:1px solid var(--border);border-radius:8px;background:var(--bg-elev)">
      None yet — milestones will appear here as players cross thresholds.
    </div>`;
    return;
  }
  el.innerHTML = list.slice(0, 20).map(m => {
    const t = new Date(m.ts);
    const tStr = t.toLocaleString([], { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' });
    return `<div class="milestone-item">
      <div class="milestone-ts">${tStr}</div>
      <div class="milestone-text">${escapeHtml(m.text)}</div>
    </div>`;
  }).join('');
}

function renderTimestamp() {
  const el = document.getElementById('last-updated');
  if (!liveData) { el.textContent = '—'; return; }
  const t = new Date(liveData.last_polled_utc);
  el.textContent = `Last poll: ${t.toLocaleString([], { hour: 'numeric', minute: '2-digit', second: '2-digit' })}`;
}

function escapeHtml(s) {
  const div = document.createElement('div');
  div.textContent = String(s == null ? '' : s);
  return div.innerHTML;
}

async function fetchData() {
  try {
    const res = await fetch('data/leaderboards_live.json?_=' + Date.now());
    if (!res.ok) throw new Error('HTTP ' + res.status);
    liveData = await res.json();
    renderLiveBar();
    renderTable();
    renderMilestones();
    renderTimestamp();
  } catch (e) {
    console.error('Fetch failed:', e);
    const bar = document.getElementById('live-bar');
    bar.innerHTML = `<span class="error-state">Failed to load live state: ${escapeHtml(e.message)}.</span>`;
  }
}

renderTabs();
fetchData();
setInterval(fetchData, 60000);
</script>
</body>
</html>
