import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import {fileURLToPath} from 'node:url';
// Проверка cases/*.json: валидатор самого виджета + реплей патчей + инварианты + защита от «утечки будущего».
// Использование: node pipeline/validate.mjs [cases/001.json ...]   (без аргументов — все cases/*.json)
const REPO_VIEWER = path.join(process.env.PROOFKEY_REPO || path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..'), 'case-state-widget', 'viewer.js');
const viewerPath = fs.existsSync(REPO_VIEWER) ? REPO_VIEWER : path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../viewer.js');
const {validateCase, presentStep, renderJSON} = await import(viewerPath);

const HERE = path.dirname(fileURLToPath(import.meta.url));
const WIDGET = path.resolve(HERE, '..');
const ROOT = path.resolve(WIDGET, '..');
const SRC = process.env.PROOFKEY_PUBLIC || path.join(ROOT, 'data', 'dwelly-public-cases', 'raw', 'Delivery & Logistics');
const REPO = process.env.PROOFKEY_REPO || path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const NEG = path.join(REPO, 'data', 'negative-branches-001-050');
const AUG = path.join(REPO, 'data', 'context-augmentations-001-050');
function folderFor(cid) {
  if (/^\d{3}$/.test(cid)) return path.join(SRC, cid);
  if (/^\d{3}-N\d$/.test(cid)) {
    for (const row of fs.readFileSync(path.join(NEG, 'index.csv'), 'utf8').split('\n')) {
      const mm = /^(\d{3}),([\w-]+),([^,]+),/.exec(row);
      if (mm && mm[2] === cid) return path.join(NEG, mm[3]);
    }
  }
  if (/^\d{3}-A\d$/.test(cid)) {
    for (const row of fs.readFileSync(path.join(AUG, 'index.csv'), 'utf8').split('\n')) {
      const mm = /^(\d{3}),([\w-]+),([^,]+),/.exec(row);
      if (mm && mm[2] === cid) return path.join(AUG, mm[3]);
    }
  }
  throw new Error(`неизвестный кейс ${cid}`);
}
function parseHistory(text) {
  const events = [], re = /<a id="event-(\d+)"><\/a>\s*\n## (.+?) — event \1\n([\s\S]*?)(?=\n<a id="event-|$)/g;
  let m;
  while ((m = re.exec(text))) {
    const meta = {}, body = [];
    for (const line of m[3].replace(/^\n+|\n+$/g, '').split('\n')) {
      const mm = /^- \*\*(.+?):\*\* (.*)$/.exec(line);
      if (mm && !body.length) meta[mm[1]] = mm[2].trim(); else if (body.length || line.trim()) body.push(line);
    }
    events.push({id: m[1], timestamp: m[2].trim(), meta, body: body.join('\n').trim()});
  }
  return events;
}
function parseDetails(card) {
  const sec = /## Case details\n([\s\S]*?)(?=\n## |$)/.exec(card), d = {};
  if (sec) for (const mm of sec[1].matchAll(/- \*\*(.+?):\*\* (.*)/g)) d[mm[1]] = mm[2].trim();
  return d;
}
const REQ_TYPES = new Set(['information', 'decision', 'permission', 'action', 'confirmation', 'verification']);
const REQ_STATUS = new Set(['planned', 'awaiting_response', 'received', 'answered', 'completed', 'declined', 'cancelled', 'outcome_unknown', 'superseded']);
const CASE_STATUS = new Set(['not_started', 'context_received', 'escalated', 'awaiting_response', 'awaiting_confirmation', 'awaiting_decision', 'awaiting_verification', 'action_required', 'verification_required', 'in_progress', 'blocked', 'completed']);

function replay(state, patch) {
  state = structuredClone(state);
  for (const op of patch) {
    if (op.path === '') { state = structuredClone(op.value); continue; }
    const keys = op.path.slice(1).split('/').map(s => s.replace(/~1/g, '/').replace(/~0/g, '~'));
    let parent = state;
    for (const key of keys.slice(0, -1)) parent = parent[key];
    const key = keys.at(-1);
    if (op.op === 'remove') { if (Array.isArray(parent)) parent.splice(Number(key), 1); else delete parent[key]; }
    else if (op.op === 'add' && Array.isArray(parent)) parent.splice(Number(key), 0, structuredClone(op.value));
    else parent[key] = structuredClone(op.value);
  }
  return state;
}
const canon = v => Array.isArray(v) ? '[' + v.map(canon).join(',') + ']' : (v && typeof v === 'object') ? '{' + Object.keys(v).sort().map(k => JSON.stringify(k) + ':' + canon(v[k])).join(',') + '}' : JSON.stringify(v);
const text = html => html.replace(/<[^>]*>/g, '').replace(/&quot;/g, '"').replace(/&#39;/g, "'").replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&amp;/g, '&');
const tokens = s => new Set((String(s).toLowerCase().match(/\b[a-z]{1,5}-\d[\w-]*\b|\b\d+[a-z]\b|\b\d{2,}(?:[:.]\d+)?\b/g) || []));
function stateText(state) { const {messages, actors, conversations, attachments, ...rest} = state; return JSON.stringify(rest); }

function check(file) {
  const errors = [], warns = [];
  let data;
  try { data = JSON.parse(fs.readFileSync(file, 'utf8')); } catch (e) { return {file, errors: ['JSON не читается: ' + e.message], warns}; }
  try { validateCase(data); } catch (e) { errors.push('validateCase: ' + e.message); }
  if (/\bTODO\b/.test(JSON.stringify(data))) errors.push('в файле остались заглушки TODO');
  const cid = data.initial_state?.case_id;
  let folder;
  try { folder = folderFor(cid); } catch (e) { return {file, errors: [...errors, e.message], warns}; }
  // На старте известны только заголовок, Case details и Context: остальные разделы карточки пересказывают будущие события.
  const cardFull = fs.readFileSync(path.join(folder, 'index.md'), 'utf8');
  const cut = cardFull.search(/^## Initial request/m);
  const card = (cut > 0 ? cardFull.slice(0, cut) : cardFull).toLowerCase();
  const events = parseHistory(fs.readFileSync(path.join(folder, 'history.md'), 'utf8'));
  const src = {details: parseDetails(cardFull)};
  const lastState = (data.steps?.at(-1)?.state_after) ?? data.initial_state;
  const ruById = Object.fromEntries((lastState.messages || []).map(m => [m.event_id, m.body_ru || '']));
  const steps = data.steps || [];
  for (let i = 0; i <= steps.length; i++) {
    try {
      const p = presentStep(data, i), prior = i > 1 ? steps[i - 2].state_after : data.initial_state;
      if (canon(replay(prior, p.patch)) !== canon(p.state)) errors.push(`шаг ${i}: реплей патча не совпадает с состоянием`);
      if (canon(JSON.parse(text(renderJSON(p.state, p.patch)))) !== canon(p.state)) errors.push(`шаг ${i}: renderJSON не воспроизводит состояние`);
      if (p.state.messages.length !== i) errors.push(`шаг ${i}: ожидалось ${i} сообщений, найдено ${p.state.messages.length}`);
    } catch (e) { errors.push(`шаг ${i}: presentStep упал: ${e.message}`); }
  }
  for (const [i, e] of events.entries()) {
    const m = (steps[i]?.state_after?.messages || []).find(x => x.event_id === e.id);
    if (m && m.body !== undefined && m.body !== e.body) errors.push(`сообщение ${e.id}: body отличается от history.md`);
  }
  const ids = events.map(e => e.id), got = steps.map(s => s.event.id);
  if (JSON.stringify(ids) !== JSON.stringify(got)) errors.push(`шаги ${got.join(',')} ≠ события ${ids.join(',')}`);
  const states = [['initial_state', data.initial_state], ...steps.map((s, i) => [`шаг ${i + 1} (${s.event.id})`, s.state_after])];
  const observed = new Set();
  let avail = card;
  const evText = e => (e.timestamp + ' ' + e.body + ' ' + (ruById[e.id] || '')).toLowerCase();
  states.forEach(([label, st], i) => {
    if (i > 0) { observed.add(steps[i - 1].event.id); if (events[i - 1]) avail += ' ' + evText(events[i - 1]); }
    const actors = st.actors || {};
    const has = id => Object.prototype.hasOwnProperty.call(actors, id);
    if (st.client_actor_id != null && !has(st.client_actor_id)) errors.push(`${label}: client_actor_id не в actors`);
    if (st.limits !== undefined && (!Array.isArray(st.limits) || !st.limits.length)) errors.push(`${label}: limits пустой — ключ не пишется`);
    if (i > 0 && canon(st.limits ?? null) !== canon(states[0][1].limits ?? null)) errors.push(`${label}: limits отличается от initial_state (список должен быть одинаковым во всех снимках)`);
    for (const m of st.messages || []) if (m.to_actors) errors.push(`${label}: сообщение ${m.event_id}: to_actors устарело, остальные адресаты идут в copy_to`);
    const fids = new Set();
    for (const f of st.facts || []) {
      if (!f.id || fids.has(f.id)) errors.push(`${label}: факт без id или дубль ${f.id}`); fids.add(f.id);
      if (typeof f.text !== 'string' || !f.text.trim()) errors.push(`${label}: факт ${f.id} без текста`);
      const s = f.source || {};
      if (!['case_card', 'message'].includes(s.type)) errors.push(`${label}: факт ${f.id}: source.type должен быть case_card|message`);
      if (s.type === 'message' && !observed.has(s.id)) errors.push(`${label}: факт ${f.id} ссылается на ещё не наступившее сообщение ${s.id}`);
      if (s.type === 'case_card' && s.id !== cid && s.id !== cid.split('-')[0]) errors.push(`${label}: факт ${f.id}: source.id для case_card должен быть ${cid} (или родительский ${cid.split('-')[0]})`);
    }
    for (const [rid, r] of Object.entries(st.requests || {})) {
      if (!REQ_TYPES.has(r.type)) errors.push(`${label}: запрос ${rid}: type '${r.type}' вне словаря`);
      if (!REQ_STATUS.has(r.status)) errors.push(`${label}: запрос ${rid}: status '${r.status}' вне словаря`);
      for (const k of ['from_actor', 'to_actor', 'responsible_actor']) if (!has(r[k])) errors.push(`${label}: запрос ${rid}.${k}='${r[k]}' не в actors`);
      if (typeof r.purpose !== 'string') errors.push(`${label}: запрос ${rid} без purpose`);
      if (r.responded_by !== undefined && (!has(r.responded_by) || r.responded_by === r.to_actor)) errors.push(`${label}: запрос ${rid}.responded_by должен быть участником, отличным от to_actor`);
      if (r.responded_by !== undefined && !['answered', 'completed', 'declined'].includes(r.status)) errors.push(`${label}: запрос ${rid}.responded_by пишется только после ответа`);
      for (const id of r.evidence_event_ids || []) if (!observed.has(id)) errors.push(`${label}: запрос ${rid} ссылается на будущее событие ${id}`);
      if (['answered', 'completed'].includes(r.status) && !(r.evidence_event_ids || []).length) errors.push(`${label}: запрос ${rid} ${r.status} без evidence_event_ids`);
    }
    if (st.next_step) {
      if (!has(st.next_step.responsible_actor)) errors.push(`${label}: next_step.responsible_actor не в actors`);
      if (st.next_step.request_id != null && !(st.requests || {})[st.next_step.request_id]) errors.push(`${label}: next_step.request_id '${st.next_step.request_id}' нет в requests`);
      if (!REQ_TYPES.has(st.next_step.type)) errors.push(`${label}: next_step.type '${st.next_step.type}' вне словаря`);
    }
    if (st.result) {
      for (const id of st.result.evidence_event_ids || []) if (!observed.has(id)) errors.push(`${label}: result ссылается на будущее событие ${id}`);
      if (st.result.confirmed_by != null && !has(st.result.confirmed_by)) errors.push(`${label}: result.confirmed_by не в actors`);
    }
    for (const w of st.agent_state?.waiting_for || []) if (w.request_id != null && !(st.requests || {})[w.request_id]) errors.push(`${label}: waiting_for.request_id '${w.request_id}' нет в requests`);
    if (!CASE_STATUS.has(st.status)) warns.push(`${label}: status '${st.status}' вне словаря`);
    const d = st.decision || {};
    if (d.required === true) {
      if (typeof d.question !== 'string') errors.push(`${label}: decision.required, но нет question`);
      if (!(d.options || []).length) errors.push(`${label}: decision.required, но нет options`);
      if (d.decision_maker != null && !has(d.decision_maker)) errors.push(`${label}: decision_maker не в actors`);
    }
    if (st.agent_state?.status === 'completed' && st.result == null) warns.push(`${label}: агент completed, а result пустой`);
    for (const n of st.annotations || []) {
      if (n.kind !== 'gap') continue;
      const ia = n.implied_action;
      if (!ia || typeof ia !== 'object') { errors.push(`${label}: пояснение-пробел '${n.id}' без implied_action`); continue; }
      for (const k of ['from_actor', 'to_actor']) if (!has(ia[k])) errors.push(`${label}: пробел '${n.id}': implied_action.${k}='${ia[k]}' не в actors`);
      if (!REQ_TYPES.has(ia.type)) errors.push(`${label}: пробел '${n.id}': implied_action.type '${ia.type}' вне словаря`);
      if (typeof ia.purpose !== 'string') errors.push(`${label}: пробел '${n.id}': implied_action без purpose`);
      if (i === states.length - 1 && !n.before_message_id && st.agent_state?.status === 'completed') warns.push(`${label}: пробел '${n.id}' на финале без before_message_id (к концу подразумевающее событие уже должно быть)`);
    }
    const availTokens = tokens(avail), futureTokens = tokens(events.slice(i).map(evText).join(' '));
    for (const t of tokens(stateText(st))) if (!availTokens.has(t) && futureTokens.has(t)) errors.push(`${label}: «${t}» упоминается раньше сообщения, где впервые появляется`);
  });
  const last = states.at(-1)[1], status = src.details?.Status || '';
  const completed = /^completed/i.test(status);
  if (completed && last.agent_state?.status !== 'completed') warns.push(`финал: карточка '${status}', а agent_state=${last.agent_state?.status}`);
  if (!completed && last.agent_state?.status === 'completed') warns.push(`финал: карточка '${status}', а agent_state=completed`);
  const unmet = (last.success_criteria || []).filter(c => c.status !== 'met').map(c => c.id);
  if (completed && unmet.length) warns.push(`финал: не выполнены критерии ${unmet.join(',')}, хотя карточка completed`);
  if (!(last.success_criteria || []).length) errors.push('нет ни одного success_criteria');
  return {file, errors, warns};
}

console.log(`viewer.js: ${viewerPath}`);
const args = process.argv.slice(2);
const files = args.length ? args : fs.readdirSync(path.join(WIDGET, 'cases')).filter(f => /^\d{3}\.json$/.test(f)).sort().map(f => path.join(WIDGET, 'cases', f));
let failed = 0;
for (const f of files) {
  const r = check(f);
  const name = path.basename(f);
  if (r.errors.length) { failed++; console.log(`FAIL ${name}`); for (const e of r.errors) console.log('   ✗ ' + e); }
  else console.log(`OK   ${name}${r.warns.length ? '' : ''}`);
  for (const w of r.warns) console.log('   ⚠ ' + w);
}
console.log(`\n${files.length - failed}/${files.length} OK`);
process.exit(failed ? 1 : 0);
