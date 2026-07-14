/**
 * Video Pipeline Dashboard — CLI + Minimal HTTP Server
 *
 * This module provides:
 *   1. `npx ts-node src/admin/dashboard.ts list` — show top candidates in terminal
 *   2. `npx ts-node src/admin/dashboard.ts serve` — start a local HTTP server with a web UI
 *   3. `npx ts-node src/admin/dashboard.ts render <id1> <id2> ...` — render specific candidates
 *
 * Configuration:
 *   - Set API_BASE_URL env var to point to your backend (default: http://localhost:8000)
 *
 * Usage:
 *   API_BASE_URL=https://api.cookdai.site npx ts-node src/admin/dashboard.ts list
 */

const API_BASE = process.env.API_BASE_URL || "http://localhost:8000";
const API_PATH = `${API_BASE}/api/v1/admin/video-pipeline`;

interface Candidate {
  id: string;
  personName: string;
  strategyLabel: string;
  winningLine: string;
  coachReasoning: string;
  theirLastMessage: string;
  hookStyle: string;
  viralScore: number;
  priority: string;
  transcript: { sender: string; text: string }[];
  createdAt: string;
}

interface CandidatesResponse {
  candidates: Candidate[];
  count: number;
  total_scored: number;
  total_renderable: number;
  score_buckets: { high: number; medium: number };
}

// ── CLI Commands ──

async function listCandidates(limit = 10) {
  console.log(`\n🎬 Fetching top ${limit} video candidates...\n`);

  const res = await fetch(`${API_PATH}/candidates?limit=${limit}`);
  const data: CandidatesResponse = await res.json();

  console.log(
    `Scored: ${data.total_scored} | Renderable: ${data.total_renderable}`,
  );
  console.log(
    `🔥 High: ${data.score_buckets.high} | ✅ Medium: ${data.score_buckets.medium}\n`,
  );

  for (const c of data.candidates) {
    const scoreIcon =
      c.viralScore >= 50 ? "🔥" : c.viralScore >= 30 ? "✅" : "⏸️";
    const styleIcons: Record<string, string> = {
      roast: "🔥",
      gap: "⏰",
      outcome: "🎯",
      strategy: "🧠",
      bet: "🎲",
    };

    console.log(
      `${scoreIcon} [${c.viralScore}] ${styleIcons[c.hookStyle] || "🎬"} ${c.personName}`,
    );
    console.log(`   Hook: ${c.hookStyle} | Strategy: ${c.strategyLabel}`);
    console.log(`   "${c.winningLine.substring(0, 80)}..."`);
    console.log(
      `   ${c.transcript.length} messages | Created: ${c.createdAt.substring(0, 10)}`,
    );
    console.log(`   ID: ${c.id}`);
    console.log("");
  }

  console.log(
    `Run \`npx ts-node src/admin/dashboard.ts render <id>\` to render a candidate.`,
  );
}

async function renderCandidates(ids: string[]) {
  console.log(`\n🎬 Queuing ${ids.length} candidate(s) for rendering...\n`);

  const res = await fetch(`${API_PATH}/render`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(ids),
  });
  const data = await res.json();

  if (data.rendered?.length) {
    console.log(`✅ ${data.rendered.length} candidate(s) rendered:`);
    for (const r of data.rendered) {
      console.log(
        `   - ${r.personName} (${r.hookStyle}): "${r.winningLine.substring(0, 60)}..."`,
      );
    }
    console.log(
      `\n📋 JSON payloads copied to clipboard? Run with --clipboard to auto-copy.`,
    );
  }

  if (data.not_found?.length) {
    console.log(
      `❌ ${data.not_found.length} ID(s) not found: ${data.not_found.join(", ")}`,
    );
  }
}

// ── Simple HTTP Server for Web UI ──

async function serveDashboard() {
  const http = await import("http");
  const port = parseInt(process.env.PORT || "3456", 10);

  const server = http.createServer(async (req, res) => {
    if (req.url === "/api/candidates" && req.method === "GET") {
      // Proxy to backend
      const backendRes = await fetch(`${API_PATH}/candidates?limit=50`);
      const data = await backendRes.json();
      res.writeHead(200, {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
      });
      res.end(JSON.stringify(data));
      return;
    }

    if (req.url === "/api/render" && req.method === "POST") {
      let body = "";
      req.on("data", (chunk) => (body += chunk));
      req.on("end", async () => {
        const ids = JSON.parse(body);
        const backendRes = await fetch(`${API_PATH}/render`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(ids),
        });
        const data = await backendRes.json();
        res.writeHead(200, {
          "Content-Type": "application/json",
          "Access-Control-Allow-Origin": "*",
        });
        res.end(JSON.stringify(data));
      });
      return;
    }

    // Serve HTML dashboard
    res.writeHead(200, { "Content-Type": "text/html" });
    res.end(`
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>🎬 Cookd Video Pipeline</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { background: #000; color: #fff; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; padding: 24px; }
  .container { max-width: 900px; margin: 0 auto; }
  h1 { font-size: 28px; font-weight: 800; margin-bottom: 8px; }
  p { color: rgba(255,255,255,0.45); font-size: 14px; margin-bottom: 24px; }
  .stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 24px; }
  .stat { background: #0a0a0a; border: 1px solid rgba(255,255,255,0.1); border-radius: 12px; padding: 16px; }
  .stat-label { font-size: 10px; text-transform: uppercase; letter-spacing: 0.15em; color: rgba(255,255,255,0.3); }
  .stat-value { font-size: 28px; font-weight: 800; margin-top: 4px; }
  .stat-value.high { color: #FF003C; }
  .stat-value.medium { color: #2563EB; }
  .stat-value.good { color: #00FF66; }
  .actions { display: flex; gap: 12px; margin-bottom: 16px; align-items: center; }
  .actions button { padding: 8px 24px; border-radius: 999px; font-size: 12px; font-weight: 700; border: none; cursor: pointer; transition: all 0.2s; }
  .btn-render { background: #FF003C; color: #fff; }
  .btn-render:disabled { background: rgba(255,255,255,0.05); color: rgba(255,255,255,0.3); cursor: not-allowed; }
  .btn-render:hover:not(:disabled) { box-shadow: 0 0 20px rgba(255,0,60,0.25); }
  .btn-select { background: transparent; color: rgba(255,255,255,0.45); border: 1px solid rgba(255,255,255,0.1) !important; font-size: 11px !important; }
  .btn-select:hover { color: #fff; border-color: rgba(255,255,255,0.3) !important; }
  .count { font-size: 12px; color: rgba(255,255,255,0.3); }
  .card { background: #0a0a0a; border: 1px solid rgba(255,255,255,0.1); border-radius: 12px; padding: 16px; margin-bottom: 8px; cursor: pointer; transition: all 0.2s; }
  .card:hover { border-color: rgba(255,255,255,0.2); }
  .card.selected { border-color: #FF003C; background: rgba(255,0,60,0.05); }
  .card-header { display: flex; align-items: center; gap: 12px; margin-bottom: 8px; }
  .checkbox { width: 20px; height: 20px; border: 2px solid rgba(255,255,255,0.2); border-radius: 4px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
  .checkbox.checked { background: #FF003C; border-color: #FF003C; }
  .card-title { font-size: 16px; font-weight: 700; }
  .badge { font-size: 10px; font-weight: 700; padding: 2px 8px; border-radius: 999px; border: 1px solid; }
  .badge-roast { color: #FF003C; border-color: #FF003C; }
  .badge-gap { color: #FF8C00; border-color: #FF8C00; }
  .badge-outcome { color: #00FF66; border-color: #00FF66; }
  .badge-strategy { color: #2563EB; border-color: #2563EB; }
  .badge-bet { color: #fff; border-color: rgba(255,255,255,0.3); }
  .card-score { font-size: 14px; font-weight: 800; font-family: monospace; }
  .card-line { font-size: 13px; color: rgba(255,255,255,0.7); margin-bottom: 8px; font-style: italic; }
  .card-meta { font-size: 11px; color: rgba(255,255,255,0.3); }
  .details { margin-top: 8px; }
  .details summary { font-size: 11px; color: rgba(255,255,255,0.3); cursor: pointer; }
  .chat-msg { display: flex; margin-bottom: 4px; }
  .chat-msg.you { justify-content: flex-end; }
  .chat-bubble { max-width: 80%; padding: 6px 10px; border-radius: 8px; font-size: 12px; }
  .chat-msg.them .chat-bubble { background: #0a0a0a; border: 1px solid rgba(255,255,255,0.1); color: rgba(255,255,255,0.7); }
  .chat-msg.you .chat-bubble { background: rgba(255,0,60,0.2); border: 1px solid rgba(255,0,60,0.3); color: #fff; }
  .loading { text-align: center; padding: 48px; color: rgba(255,255,255,0.3); }
  .toast { position: fixed; bottom: 24px; right: 24px; background: #00FF66; color: #000; padding: 12px 24px; border-radius: 12px; font-weight: 700; font-size: 13px; opacity: 0; transition: opacity 0.3s; }
  .toast.show { opacity: 1; }
</style>
</head>
<body>
<div class="container">
  <h1>🎬 Video Pipeline</h1>
  <p>Review scored interactions and queue them for Remotion rendering.</p>

  <div class="stats" id="stats">
    <div class="stat"><div class="stat-label">Scored</div><div class="stat-value" id="totalScored">—</div></div>
    <div class="stat"><div class="stat-label">Renderable</div><div class="stat-value good" id="totalRenderable">—</div></div>
    <div class="stat"><div class="stat-label">🔥 Viral</div><div class="stat-value high" id="highCount">—</div></div>
    <div class="stat"><div class="stat-label">✅ Good</div><div class="stat-value medium" id="mediumCount">—</div></div>
  </div>

  <div class="actions">
    <button class="btn-select" onclick="selectAll()">Select All</button>
    <span class="count" id="selectedCount">0 selected</span>
    <button class="btn-render" id="renderBtn" onclick="renderSelected()" disabled>Render 0 Videos</button>
  </div>

  <div id="candidates"></div>
</div>

<div class="toast" id="toast"></div>

<script>
let candidates = [];
let selected = new Set();

async function load() {
  document.getElementById('candidates').innerHTML = '<div class="loading">Loading...</div>';
  const res = await fetch('/api/candidates');
  const data = await res.json();
  candidates = data.candidates || [];

  document.getElementById('totalScored').textContent = data.total_scored;
  document.getElementById('totalRenderable').textContent = data.total_renderable;
  document.getElementById('highCount').textContent = data.score_buckets?.high || 0;
  document.getElementById('mediumCount').textContent = data.score_buckets?.medium || 0;

  render();
}

function render() {
  const container = document.getElementById('candidates');
  if (candidates.length === 0) {
    container.innerHTML = '<div class="loading">No candidates found. Generate some replies first.</div>';
    return;
  }

  container.innerHTML = candidates.map(c => {
    const isSelected = selected.has(c.id);
    const hookBadge = {
      roast: 'badge-roast', gap: 'badge-gap', outcome: 'badge-outcome', strategy: 'badge-strategy', bet: 'badge-bet'
    }[c.hookStyle] || 'badge-bet';
    const scoreClass = c.viralScore >= 50 ? 'high' : c.viralScore >= 30 ? '' : '';
    const scoreIcon = c.viralScore >= 50 ? '🔥' : c.viralScore >= 30 ? '✅' : '⏸️';

    return \`
      <div class="card \${isSelected ? 'selected' : ''}" onclick="toggle('\${c.id}')">
        <div class="card-header">
          <div class="checkbox \${isSelected ? 'checked' : ''}">\${isSelected ? '✓' : ''}</div>
          <span class="card-title">\${c.personName}</span>
          <span class="badge \${hookBadge}">\${c.hookStyle}</span>
          <span class="card-score \${scoreClass}">\${scoreIcon} \${c.viralScore}</span>
        </div>
        <div class="card-line">"\${c.winningLine.substring(0, 100)}\${c.winningLine.length > 100 ? '...' : ''}"</div>
        <div class="card-meta">\${c.transcript.length} messages · \${c.strategyLabel} · \${c.createdAt.substring(0, 10)}</div>
        <details class="details">
          <summary>Chat Transcript (\${c.transcript.length} messages)</summary>
          <div style="margin-top: 8px;">
            \${c.transcript.slice(0, 10).map(m => \`
              <div class="chat-msg \${m.sender}">
                <div class="chat-bubble">\${m.text}</div>
              </div>
            \`).join('')}
            \${c.transcript.length > 10 ? '<p style="font-size: 10px; color: rgba(255,255,255,0.3); margin-top: 4px;">+' + (c.transcript.length - 10) + ' more</p>' : ''}
          </div>
        </details>
      </div>
    \`;
  }).join('');
}

function toggle(id) {
  if (selected.has(id)) selected.delete(id);
  else selected.add(id);
  updateUI();
}

function selectAll() {
  if (selected.size === candidates.length) selected.clear();
  else candidates.forEach(c => selected.add(c.id));
  updateUI();
}

function updateUI() {
  const btn = document.getElementById('renderBtn');
  btn.textContent = \`Render \${selected.size} Video\${selected.size !== 1 ? 's' : ''}\`;
  btn.disabled = selected.size === 0;
  document.getElementById('selectedCount').textContent = \`\${selected.size} selected\`;
  render();
}

async function renderSelected() {
  if (selected.size === 0) return;
  const ids = Array.from(selected);

  const res = await fetch('/api/render', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(ids),
  });
  const data = await res.json();

  showToast(\`✅ \${data.rendered?.length || 0} videos queued for rendering!\`);
  selected.clear();
  updateUI();
}

function showToast(msg) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), 3000);
}

load();
</script>
</body>
</html>
`);
  });

  server.listen(port, () => {
    console.log(`
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  🎬 Cookd Video Pipeline Dashboard
  
  Web UI:        http://localhost:${port}
  API Backend:   ${API_BASE}
  
  CLI commands:
    list         npx ts-node src/admin/dashboard.ts list
    serve        npx ts-node src/admin/dashboard.ts serve
    render       npx ts-node src/admin/dashboard.ts render <id1> <id2>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
`);
  });
}

// ── CLI Entry ──

const [cmd, ...args] = process.argv.slice(2);

if (cmd === "list") listCandidates(parseInt(args[0]) || 10);
else if (cmd === "serve") serveDashboard();
else if (cmd === "render") renderCandidates(args.length > 0 ? args : []);
else {
  console.log(`
Usage:
  npx ts-node src/admin/dashboard.ts list [limit]    Show top video candidates
  npx ts-node src/admin/dashboard.ts serve           Start web dashboard UI
  npx ts-node src/admin/dashboard.ts render <id...>  Queue candidates for rendering

Environment:
  API_BASE_URL  Backend API URL (default: http://localhost:8000)
  PORT          Web UI port (default: 3456)
`);
}
