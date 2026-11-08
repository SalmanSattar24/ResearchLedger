const el = (id) => document.getElementById(id);
const text = (tag, value, className) => { const n = document.createElement(tag); n.textContent = value; if (className) n.className = className; return n; };
let ready = false;
let querying = false;
async function metadata() {
  try {
    const response = await fetch('/evidence-api/meta'); if (!response.ok) throw new Error('Corpus metadata is unavailable.');
    const m = await response.json();
    el('corpus').textContent = `${m.corpus} @ ${m.commit.slice(0, 12)} · ${m.documents} documents · ${m.chunks} chunks · ${m.retriever}`;
    el('generated-option').disabled = !m.generated_enabled;
    el('generated-option').textContent = m.generated_enabled ? `Generated answer · ${m.model} · capped free-tier configuration` : 'Generated answer · unavailable until configured';
    el('model-note').textContent = m.generated_enabled ? 'Generated mode sends the question and public excerpts to Gemini. Requests stop when the allowance is exhausted.' : 'Real retrieval works now. Generated mode needs a server-side key and confirmation that its project has no paid billing.';
    el('limits').textContent = `Model-call caps per retained server ledger: ${m.limits.calls_per_day}/UTC day and ${m.limits.calls_per_minute}/minute; ${m.limits.calls_reserved_per_answer} calls reserved per answer. Failed calls count. Replicas and filesystem resets have separate allowances. These caps do not establish a key’s billing status.`;
    ready = true;
  } catch (e) { showError(e.message); el('submit').disabled = true; }
}
function showError(message) { el('error').hidden = false; el('error').textContent = message; }
function sourceLink(citation, sources) {
  const matching = sources.find(s => s.path === citation.path && s.start <= citation.start && s.end >= citation.end);
  if (!matching) return text('span', 'Source unavailable');
  const a = text('a', `${citation.path} · L${citation.start}–${citation.end}`);
  const u = new URL(matching.url); u.hash = `L${citation.start}-L${citation.end}`;
  a.href = u.href; a.target = '_blank'; a.rel = 'noopener noreferrer'; return a;
}
function render(r) {
  el('status').textContent = `${r.status.toUpperCase()} · ${r.overall || r.verification}`;
  el('answer').append(text('p', r.answer || r.reason));
  el('verification').textContent = `${r.reason || ''} Verification: ${r.verification}.`;
  for (const problem of r.problems || []) el('verification').append(text('p', problem));
  for (const claim of r.claims || []) {
    const item = text('div', '', 'claim'); item.append(text('p', claim.text));
    for (const citation of claim.citations) item.append(sourceLink(citation, r.sources));
    el('claims').append(item);
  }
  el('source-count').textContent = `${r.sources.length} excerpts`;
  const seen = new Set();
  for (const s of r.sources) {
    if (seen.has(s.id)) continue; seen.add(s.id);
    const item = text('article', '', 'source'); item.append(text('h3', s.path), text('p', `${s.commit.slice(0, 12)} · lines ${s.start}–${s.end} · BM25 ${s.score}`));
    const code = text('pre', s.lines.map(l => `${l.number}: ${l.text}`).join('\n')); item.append(code);
    const link = text('a', 'Open pinned source on GitHub ↗'); link.href = s.url; link.target = '_blank'; link.rel = 'noopener noreferrer'; item.append(link); el('sources').append(item);
  }
  if (r.injected_candidate) {
    const panel = text('div', '', 'rejected'); panel.append(text('h3', 'Rejected test candidate · excluded from answer'), text('p', r.injected_candidate.text));
    for (const p of r.injected_candidate.problems) panel.append(text('p', p)); el('injected').append(panel);
  }
}
async function ask() {
  if (!ready || querying) return;
  querying = true;
  for (const id of ['question', 'mode', 'inject']) el(id).disabled = true;
  document.querySelectorAll('.example').forEach(b => b.disabled = true);
  for (const id of ['answer', 'claims', 'sources', 'injected', 'verification']) el(id).replaceChildren();
  el('source-count').textContent = '0 excerpts'; el('error').hidden = true; el('submit').disabled = true; el('status').textContent = 'Retrieving and checking…';
  const controller = new AbortController(); const timeout = setTimeout(() => controller.abort(), 70000);
  try {
    const response = await fetch('/evidence-api/ask', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({question: el('question').value, mode: el('mode').value, inject: el('inject').checked}), signal: controller.signal});
    const result = await response.json(); if (!response.ok) throw new Error(result.error || 'Request failed.'); render(result);
  } catch(e) { el('status').textContent = 'No verified answer returned'; showError(e.name === 'AbortError' ? 'Request timed out. No automatic retry was made.' : e.message); }
  finally {
    clearTimeout(timeout); querying = false; el('submit').disabled = false;
    for (const id of ['question', 'mode', 'inject']) el(id).disabled = false;
    document.querySelectorAll('.example').forEach(b => b.disabled = false);
  }
}
el('query-form').addEventListener('submit', e => { e.preventDefault(); ask(); });
document.querySelectorAll('.example').forEach(b => b.addEventListener('click', () => { el('question').value = b.dataset.query; ask(); }));
metadata();
