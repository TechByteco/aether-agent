"""
AETHER Operator Dashboard — HUD Panel for Autonomous Operations
================================================================
This HTML panel is injected into the existing AETHER HUD to show the owner:
• Live ops status (scheduler health, next job times)
• Approval inbox (lead signals, payment alerts, pricing decisions)
• Payment history
• Portfolio health (site uptime per venture)

It communicates with the /api/owner/* REST endpoints added by owner_dashboard.py
and auto-refreshes every 60 seconds.
"""
OPERATOR_PANEL_HTML = """
<!-- ═══ AUTONOMOUS OPERATOR PANEL ═══ -->
<div id="operator-panel" style="display:none;" class="fixed inset-0 z-[9999] bg-black/80 backdrop-blur-xl flex items-center justify-center p-4">
  <div class="w-full max-w-5xl bg-[#0E0F14] border border-slate-700/60 rounded-2xl shadow-2xl flex flex-col max-h-[90vh] overflow-hidden">

    <!-- Header -->
    <div class="flex items-center justify-between px-6 py-4 border-b border-slate-800">
      <div class="flex items-center gap-3">
        <div class="w-3 h-3 rounded-full bg-emerald-400 animate-pulse shadow-lg shadow-emerald-500/50"></div>
        <span class="text-white font-semibold text-base">LEON Autonomous Operator</span>
        <span id="op-scheduler-badge" class="text-[10px] font-mono bg-slate-800 text-slate-400 px-2 py-0.5 rounded-full border border-slate-700">loading…</span>
      </div>
      <button onclick="closeOperatorPanel()" class="text-slate-500 hover:text-white transition-colors text-xl font-light">✕</button>
    </div>

    <!-- Tab Bar -->
    <div class="flex border-b border-slate-800 px-6">
      <button onclick="opTab('inbox')" id="tab-inbox" class="op-tab active-tab px-4 py-3 text-sm font-medium text-white border-b-2 border-indigo-500">Inbox</button>
      <button onclick="opTab('payments')" id="tab-payments" class="op-tab px-4 py-3 text-sm font-medium text-slate-400 hover:text-white border-b-2 border-transparent">Payments</button>
      <button onclick="opTab('leads')" id="tab-leads" class="op-tab px-4 py-3 text-sm font-medium text-slate-400 hover:text-white border-b-2 border-transparent">Leads</button>
      <button onclick="opTab('health')" id="tab-health" class="op-tab px-4 py-3 text-sm font-medium text-slate-400 hover:text-white border-b-2 border-transparent">Portfolio Health</button>
      <button onclick="opTab('log')" id="tab-log" class="op-tab px-4 py-3 text-sm font-medium text-slate-400 hover:text-white border-b-2 border-transparent">Ops Log</button>
    </div>

    <!-- Content -->
    <div id="op-content" class="flex-1 overflow-y-auto p-6 text-sm text-slate-300 space-y-3">
      <div class="text-slate-500 text-center py-8">Loading…</div>
    </div>

    <!-- Footer -->
    <div class="px-6 py-3 border-t border-slate-800 flex items-center justify-between">
      <span id="op-last-refresh" class="text-xs text-slate-600">Refreshing every 60s</span>
      <button onclick="refreshOperatorPanel()" class="text-xs text-indigo-400 hover:text-indigo-300">↺ Refresh now</button>
    </div>
  </div>
</div>

<script>
let _opCurrentTab = 'inbox';

function openOperatorPanel() {
  document.getElementById('operator-panel').style.display = 'flex';
  refreshOperatorPanel();
}
function closeOperatorPanel() {
  document.getElementById('operator-panel').style.display = 'none';
}
function opTab(tab) {
  _opCurrentTab = tab;
  document.querySelectorAll('.op-tab').forEach(t => {
    t.classList.remove('active-tab', 'text-white', 'border-indigo-500');
    t.classList.add('text-slate-400', 'border-transparent');
  });
  const el = document.getElementById('tab-' + tab);
  if (el) { el.classList.add('active-tab', 'text-white', 'border-indigo-500'); el.classList.remove('text-slate-400', 'border-transparent'); }
  refreshOperatorPanel();
}

async function refreshOperatorPanel() {
  const content = document.getElementById('op-content');
  content.innerHTML = '<div class="text-slate-500 text-center py-8">Loading…</div>';
  try {
    if (_opCurrentTab === 'inbox') await renderInbox(content);
    else if (_opCurrentTab === 'payments') await renderPayments(content);
    else if (_opCurrentTab === 'leads') await renderLeads(content);
    else if (_opCurrentTab === 'health') await renderHealth(content);
    else if (_opCurrentTab === 'log') await renderLog(content);
    document.getElementById('op-last-refresh').textContent = 'Last refresh: ' + new Date().toLocaleTimeString();
    await refreshStatus();
  } catch(e) { content.innerHTML = '<div class="text-red-400 p-4">Error: ' + e.message + '</div>'; }
}

async function refreshStatus() {
  try {
    const r = await fetch('/api/owner/status'); const d = await r.json();
    const badge = document.getElementById('op-scheduler-badge');
    badge.textContent = d.scheduler_running ? '● RUNNING' : '○ STOPPED';
    badge.className = d.scheduler_running
      ? 'text-[10px] font-mono bg-emerald-950 text-emerald-400 px-2 py-0.5 rounded-full border border-emerald-800'
      : 'text-[10px] font-mono bg-red-950 text-red-400 px-2 py-0.5 rounded-full border border-red-800';
  } catch(e) {}
}

function card(html, cls='') {
  return `<div class="bg-slate-900/60 border border-slate-800/80 rounded-xl p-4 ${cls}">${html}</div>`;
}
function badge(text, color='slate') {
  const m = {slate:'bg-slate-800 text-slate-300', green:'bg-emerald-950 text-emerald-400', red:'bg-red-950 text-red-400', yellow:'bg-yellow-950 text-yellow-400', blue:'bg-indigo-950 text-indigo-400'};
  return `<span class="text-[10px] font-mono px-2 py-0.5 rounded-full ${m[color]||m.slate}">${text}</span>`;
}

async function renderInbox(el) {
  const r = await fetch('/api/owner/inbox'); const d = await r.json();
  const items = d.items || [];
  const pending = items.filter(i => i.status === 'pending');
  let html = `<div class="flex gap-3 mb-4">${badge(pending.length + ' pending approval', pending.length ? 'yellow' : 'green')}${badge(items.length + ' total', 'slate')}</div>`;
  if (!items.length) { html += '<div class="text-slate-500 text-center py-8">Inbox empty — LEON is working autonomously 🤖</div>'; }
  items.slice().reverse().forEach(item => {
    const isPending = item.status === 'pending' && item.requires_approval;
    html += card(`
      <div class="flex items-start justify-between gap-3">
        <div class="flex-1">
          <div class="flex items-center gap-2 mb-1">${badge(item.category || 'info', 'blue')}<span class="font-medium text-white text-xs">${item.title}</span></div>
          <div class="text-slate-500 text-xs">${item.created_at ? new Date(item.created_at).toLocaleString() : ''}</div>
        </div>
        ${isPending ? `<div class="flex gap-2 flex-shrink-0"><button onclick="opApprove('${item.id}')" class="text-xs bg-emerald-600 hover:bg-emerald-500 text-white px-3 py-1 rounded-lg">Approve</button><button onclick="opDismiss('${item.id}')" class="text-xs bg-slate-700 hover:bg-slate-600 text-slate-300 px-3 py-1 rounded-lg">Dismiss</button></div>` : badge(item.status, item.status === 'approved' ? 'green' : 'slate')}
      </div>`, 'mb-2');
  });
  el.innerHTML = html;
}

async function renderPayments(el) {
  const r = await fetch('/api/owner/payments'); const d = await r.json();
  const payments = d.payments || [];
  let total = payments.reduce((s, p) => s + (p.amount_inr || 0), 0);
  let html = `<div class="flex gap-3 mb-4">${badge('₹' + total.toFixed(0) + ' total', 'green')}${badge(payments.length + ' payments', 'slate')}</div>`;
  if (!payments.length) { html += '<div class="text-slate-500 text-center py-8">No payments yet. Share your venture URLs to get first customers 🚀</div>'; }
  payments.slice().reverse().forEach(p => {
    html += card(`<div class="flex justify-between items-center"><div><div class="text-white font-medium text-xs">${p.description || p.venture_name || 'Payment'}</div><div class="text-slate-500 text-xs mt-0.5">${p.payment_id} · ${p.email || ''} · ${p.created_at ? new Date(p.created_at).toLocaleString() : ''}</div></div><div class="text-emerald-400 font-bold">₹${(p.amount_inr || 0).toFixed(0)}</div></div>`, 'mb-2');
  });
  el.innerHTML = html;
}

async function renderLeads(el) {
  const r = await fetch('/api/owner/leads'); const d = await r.json();
  const leads = d.signals || [];
  let html = `<div class="mb-4">${badge(leads.length + ' intent signals', leads.length ? 'blue' : 'slate')}</div>`;
  if (!leads.length) { html += '<div class="text-slate-500 text-center py-8">No leads discovered yet. Lead scan runs every 6 hours automatically.</div>'; }
  leads.slice(0, 20).forEach(s => {
    html += card(`
      <div class="flex items-start gap-3">
        <div class="flex-shrink-0 w-8 h-8 rounded-lg bg-indigo-950 border border-indigo-800/50 flex items-center justify-center text-indigo-400 font-bold text-xs">${s.intent_score}</div>
        <div class="flex-1 min-w-0">
          <a href="${s.url}" target="_blank" class="text-indigo-300 hover:text-indigo-200 text-xs font-medium truncate block">${s.title}</a>
          <div class="text-slate-500 text-xs mt-0.5">${s.source} · ${s.venture_slug}</div>
          <div class="text-slate-400 text-xs mt-1 line-clamp-2">${s.suggested_action}</div>
        </div>
      </div>`, 'mb-2');
  });
  el.innerHTML = html;
}

async function renderHealth(el) {
  const r = await fetch('/api/owner/status'); const d = await r.json();
  const portfolio = d.portfolio || [];
  let html = `<div class="mb-4">${badge(portfolio.length + ' ventures', 'blue')}</div>`;
  if (!portfolio.length) { html += '<div class="text-slate-500 text-center py-8">Portfolio empty</div>'; }
  portfolio.forEach(v => {
    const up = v.last_health_status === 200;
    html += card(`
      <div class="flex items-center justify-between">
        <div><div class="text-white text-xs font-medium">${v.name}</div><div class="text-slate-500 text-xs mt-0.5"><a href="${v.live_url}" target="_blank" class="hover:text-indigo-400">${v.live_url}</a></div></div>
        <div class="text-right"><div class="${up?'text-emerald-400':'text-red-400'} font-bold text-sm">${up?'✓ UP':'✗ DOWN'}</div><div class="text-slate-500 text-xs">${v.monthly_price}</div></div>
      </div>`, 'mb-2');
  });
  el.innerHTML = html;
}

async function renderLog(el) {
  const r = await fetch('/api/owner/ops_log'); const d = await r.json();
  const entries = d.entries || [];
  let html = '';
  if (!entries.length) { html = '<div class="text-slate-500 text-center py-8">No ops log entries yet.</div>'; }
  entries.slice().reverse().forEach(e => {
    const lvl = e.level || 'INFO';
    const col = {ERROR:'text-red-400', WARNING:'text-yellow-400', INFO:'text-slate-300'}[lvl] || 'text-slate-300';
    html += `<div class="flex gap-3 py-1.5 border-b border-slate-800/50 text-xs"><span class="text-slate-600 font-mono flex-shrink-0">${e.ts ? new Date(e.ts).toLocaleTimeString() : ''}</span><span class="font-mono ${col} flex-shrink-0 w-14">${lvl}</span><span class="text-slate-400">${e.message || ''}</span></div>`;
  });
  el.innerHTML = html;
}

async function opApprove(id) {
  await fetch('/api/owner/approve/' + id, {method:'POST'});
  refreshOperatorPanel();
}
async function opDismiss(id) {
  await fetch('/api/owner/dismiss/' + id, {method:'POST'});
  refreshOperatorPanel();
}

// Auto-refresh every 60s when panel is open
setInterval(() => {
  if (document.getElementById('operator-panel').style.display !== 'none') refreshOperatorPanel();
}, 60000);
</script>
<!-- ═══ END OPERATOR PANEL ═══ -->
"""
