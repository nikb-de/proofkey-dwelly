const object = v => v !== null && typeof v === 'object' && !Array.isArray(v);
const own = (v, k) => Object.prototype.hasOwnProperty.call(v, k);
const escapeHTML = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const pointer = k => String(k).replace(/~/g,'~0').replace(/\//g,'~1');
const equal = (a,b) => JSON.stringify(a) === JSON.stringify(b);
const clone = v => JSON.parse(JSON.stringify(v));
const statuses = {ready:'Агент готов действовать',acting:'Агент выполняет действие',waiting:'Агент ждёт',completed:'Работа агента завершена'};
const eventTypes = {message_received:'Входящее сообщение',message_sent:'Исходящее сообщение',action:'Действие',state_changed:'Изменение состояния'};

// Check the whole document, including extension fields, before cloning or recursion.
function checkDocumentBudget(data) {
 const stack=[[data,0]], seen=new Set();let nodes=0;
 while(stack.length){
  const [value,depth]=stack.pop();
  if(++nodes>100000)throw new Error('Document exceeds 100000 nodes.');
  if(depth>64)throw new Error('Document exceeds maximum depth 64.');
  if(value===null||['string','boolean'].includes(typeof value))continue;
  if(typeof value==='number'&&Number.isFinite(value))continue;
  if(typeof value!=='object')throw new Error('Document must contain JSON values only.');
  if(seen.has(value))throw new Error('Document contains repeated or cyclic objects.');
  seen.add(value);
  if(!Array.isArray(value)&&![Object.prototype,null].includes(Object.getPrototypeOf(value)))throw new Error('Document must contain plain JSON objects.');
  for(const [key,child] of Object.entries(value)){
   if(['__proto__','prototype','constructor'].includes(key))throw new Error('Unsafe object key in document.');
   stack.push([child,depth+1]);
  }
 }
 if(new TextEncoder().encode(JSON.stringify(data)).byteLength>5*1024*1024)throw new Error('Document exceeds 5 MiB UTF-8.');
}

export function diffStates(a,b,path='') {
 if (equal(a,b)) return [];
 if (Array.isArray(a) && Array.isArray(b)) {
  const changes=[];
  for(let i=0;i<Math.min(a.length,b.length);i++) changes.push(...diffStates(a[i],b[i],`${path}/${i}`));
  for(let i=a.length-1;i>=b.length;i--) changes.push({op:'remove',path:`${path}/${i}`});
  for(let i=a.length;i<b.length;i++) changes.push({op:'add',path:`${path}/${i}`,value:clone(b[i])});
  return changes;
 }
 if(object(a)&&object(b)) {
  const changes=[];
  for(const key of Object.keys(a)) if(!own(b,key)) changes.push({op:'remove',path:`${path}/${pointer(key)}`});
  for(const key of Object.keys(b)) changes.push(...(own(a,key)?diffStates(a[key],b[key],`${path}/${pointer(key)}`):[{op:'add',path:`${path}/${pointer(key)}`,value:clone(b[key])}]));
  return changes;
 }
 return [{op:'replace',path,value:clone(b)}];
}

export function validateCase(data) {
 const need=(test,msg)=>{if(!test)throw new Error(msg)};
 checkDocumentBudget(data);
 const optionalStrings=(item,keys,label)=>{for(const key of keys)need(item[key]===undefined||typeof item[key]==='string',`${label}: ${key} должен быть строкой.`)};
 need(object(data),'Ожидается объект JSON.');
 need(data.schema_version==='case-step-viewer/1.0','schema_version должен быть case-step-viewer/1.0.');
 need(typeof data.title==='string','Нужно поле title.');
 need(Array.isArray(data.steps)&&data.steps.length<=1000,'steps должен быть массивом, не более 1000 шагов.');
 const observed=new Set(), previousMessages=[];
 const checkState=(state,label)=>{
  need(object(state),`${label}: нужно полное состояние.`);
  need(object(state.actors),`${label}: actors должен быть объектом.`);
  for(const [id,actor] of Object.entries(state.actors)){
   need(id.length>0&&object(actor)&&typeof actor.name==='string'&&typeof actor.role==='string',`${label}: неверный участник (actor).`);
  }
  need(typeof state.our_actor_id==='string'&&own(state.actors,state.our_actor_id),`${label}: our_actor_id должен ссылаться на actors.`);
  need(typeof state.goal==='string',`${label}: нужно поле goal.`);
  need(object(state.agent_state)&&own(statuses,state.agent_state.status),`${label}: неверный agent_state.status.`);
  need(state.agent_state.next_action==null||typeof state.agent_state.next_action==='string',`${label}: next_action должен быть строкой или null.`);
  optionalStrings(state.agent_state,['note'],label);
  need(Array.isArray(state.agent_state.waiting_for),`${label}: waiting_for должен быть массивом.`);
  for(const waiting of state.agent_state.waiting_for) {
   need(object(waiting)&&own(state.actors,waiting.actor_id)&&typeof waiting.expected==='string',`${label}: ожидание должно содержать actor_id и expected.`);
  }
  need(state.agent_state.status!=='waiting'||state.agent_state.waiting_for.length>0,`${label}: для waiting укажите, кого и чего ждём.`);
  need(state.agent_state.status==='waiting'||state.agent_state.waiting_for.length===0,`${label}: waiting_for должен быть пуст, если агент не ждёт.`);
  need(Array.isArray(state.messages),`${label}: messages должен быть массивом.`);
  const messageIds=new Set();
  for(const msg of state.messages) {
   need(object(msg)&&typeof msg.event_id==='string'&&!messageIds.has(msg.event_id),`${label}: идентификаторы сообщений должны быть уникальны.`);
   need(own(state.actors,msg.from_actor)&&own(state.actors,msg.to_actor),`${label}: неизвестный участник сообщения ${msg.event_id}.`);
   need(msg.copy_to===undefined||(Array.isArray(msg.copy_to)&&msg.copy_to.every(id=>typeof id==='string'&&own(state.actors,id))),`${label}: copy_to сообщения ${msg.event_id} должен содержать известных участников.`);
   need(typeof (msg.body_ru??msg.body)==='string',`${label}: нет текста сообщения ${msg.event_id}.`);
   optionalStrings(msg,['body','body_ru','channel','timestamp'],label);
   messageIds.add(msg.event_id);
  }
  need(state.messages.length>=previousMessages.length&&previousMessages.every((msg,i)=>equal(msg,state.messages[i])),`${label}: история должна накапливаться без изменения прошлых сообщений.`);
  if(label==='initial_state') for(const id of messageIds) observed.add(id);
  else for(const id of messageIds) need(observed.has(id),`${label}: сообщение ${id} появляется до своего события.`);
  previousMessages.splice(0,previousMessages.length,...state.messages);
  need(Array.isArray(state.success_criteria),`${label}: success_criteria должен быть массивом.`);
  const criterionIds=new Set();
  for(const c of state.success_criteria) {
   need(object(c)&&typeof c.id==='string'&&!criterionIds.has(c.id)&&typeof c.description==='string'&&['pending','met'].includes(c.status)&&Array.isArray(c.evidence_event_ids),`${label}: неверный критерий завершения.`);
   need(c.status!=='met'||c.evidence_event_ids.length>0,`${label}: выполненному критерию нужен источник.`);
   for(const id of c.evidence_event_ids) need(observed.has(id),`${label}: подтверждение критерия ${id} ещё не наступило.`);
   criterionIds.add(c.id);
  }
  need(state.agent_state.status!=='completed'||(state.success_criteria.length>0&&state.success_criteria.every(c=>c.status==='met')&&state.agent_state.next_action===null),`${label}: completed требует непустых выполненных критериев завершения и next_action: null.`);
  need(state.limits===undefined||(Array.isArray(state.limits)&&state.limits.every(item=>typeof item==='string')),`${label}: limits должен быть массивом строк.`);
  need(state.annotations===undefined||Array.isArray(state.annotations),`${label}: annotations должен быть массивом.`);
  for(const note of state.annotations??[]) {
   need(object(note)&&typeof note.text==='string',`${label}: в пояснении нужен text.`);
   optionalStrings(note,['id','kind','title','before_message_id'],`${label}: пояснение (annotation)`);
   need(note.source_event_ids===undefined||Array.isArray(note.source_event_ids),`${label}: source_event_ids должен быть массивом.`);
   if(note.before_message_id) need(messageIds.has(note.before_message_id),`${label}: пояснение ссылается на отсутствующее сообщение.`);
   for(const id of note.source_event_ids??[]) need(observed.has(id),`${label}: источник пояснения ${id} ещё не наступил.`);
  }
 };
 checkState(data.initial_state,'initial_state');
 for(const [i,step] of data.steps.entries()) {
  need(object(step)&&object(step.event)&&typeof step.event.id==='string'&&!observed.has(step.event.id),`Шаг ${i+1}: нужен уникальный event.id.`);
  need(own(eventTypes,step.event.type),`Шаг ${i+1}: неизвестный event.type.`);
  need(typeof step.event.title==='string'&&typeof step.explanation==='string',`Шаг ${i+1}: нужны event.title и explanation.`);
  observed.add(step.event.id);checkState(step.state_after,`Шаг ${i+1}`);
  if(step.event.message_id) need(step.state_after.messages.some(m=>m.event_id===step.event.message_id),`Шаг ${i+1}: сообщение события отсутствует в состоянии.`);
  optionalStrings(step.event,['message_id','timestamp','label'],`Шаг ${i+1}`);
  if(['message_sent','message_received'].includes(step.event.type)){
   const message=step.state_after.messages.find(m=>m.event_id===(step.event.message_id??step.event.id));
   need(message,`Шаг ${i+1}: сообщение события отсутствует в состоянии.`);
   const ours=step.state_after.our_actor_id;
   need(step.event.type==='message_sent'?message.from_actor===ours&&message.to_actor!==ours:message.from_actor!==ours&&message.to_actor===ours,`Шаг ${i+1}: неверное направление сообщения (direction).`);
  }
 }
 return data;
}

export function renderJSON(state,patch) {
 const lines=[];
 const changed=path=>patch.some(op=>op.op==='remove'?path===op.path.slice(0,op.path.lastIndexOf('/')):path===op.path||path.startsWith(op.path+'/'));
 function line(indent,key,text,path,comma){lines.push(`<span class="json-line${changed(path)?' changed':''}" data-json-path="${escapeHTML(path)}">${' '.repeat(indent)}${key===null?'':`<span class="key">${escapeHTML(JSON.stringify(key))}</span>: `}${text}${comma?',':''}</span>`)}
 function visit(v,key,path,indent,comma){
  if(v!==null&&typeof v==='object'){
   const a=Array.isArray(v),entries=Object.entries(v),open=a?'[':'{',close=a?']':'}';
   if(!entries.length)return line(indent,key,open+close,path,comma);
   line(indent,key,open,path,false);entries.forEach(([k,x],i)=>visit(x,a?null:k,`${path}/${pointer(k)}`,indent+2,i<entries.length-1));line(indent,null,close,path+'#end',comma);
  }else line(indent,key,`<span class="${typeof v==='string'?'string':'literal'}">${escapeHTML(JSON.stringify(v))}</span>`,path,comma);
 }
 visit(state,null,'',0,false);return lines.join('');
}

export function presentStep(data,index) {
 const step=index?data.steps[index-1]:null,state=step?.state_after??data.initial_state,prior=index>1?data.steps[index-2].state_after:data.initial_state;
 const actor=id=>{const a=state.actors[id];return a?[id===state.our_actor_id?'Мы':null,a.name||id,a.role].filter(Boolean).join(' · '):id||'—'};
 const agent=state.agent_state;
 return {step,state,patch:index?diffStates(prior,state):[],actor,agent,title:step?.event.title??'Начальное состояние',explanation:step?.explanation??data.initial_explanation??'',message:step?.event.message_id?state.messages.find(m=>m.event_id===step.event.message_id):null};
}

const Base=globalThis.HTMLElement??class{};
export class CaseStateViewer extends Base {
 constructor(){
  super();this._index=0;this._data=null;
  this.attachShadow({mode:'open'});
  this.shadowRoot.innerHTML=`<link rel="stylesheet" href="${new URL('./viewer.css',import.meta.url).href}"><main><header><h1 id="title">Загрузите JSON кейса</h1><p class="muted" id="identity"></p></header><div class="toolbar"><span id="counter"></span><div class="controls"><button id="prev" type="button">← Назад</button><button id="next" type="button" class="primary">Следующий шаг →</button></div></div><nav id="steps" class="steps" aria-label="Шаги кейса"></nav><section id="current" aria-live="polite"></section><section id="ticket" class="ticket" aria-label="Заявка"></section><div class="workspace"><section class="json-panel"><div class="panel-head"><div><h2>JSON состояния</h2><span class="muted">Жёлтым — изменения на этом шаге</span></div><button id="show-messages" type="button">К переписке в JSON</button></div><div id="json-scroll" class="json-scroll"><pre id="state-json" class="json" aria-label="Текущее состояние JSON"></pre></div></section><section class="conversation" aria-label="Общая переписка"><div class="panel-head"><div><h2>Общая переписка</h2><span class="muted">Отправитель → адресат · канал · время</span></div><span id="message-count" class="chat-badge"></span></div><div id="history" class="chat-history" tabindex="0"></div></section></div><details><summary>JSON Patch · изменения, включая удалённые поля</summary><pre id="patch-json"></pre></details></main>`;
  this.el=id=>this.shadowRoot.getElementById(id);
  this.shadowRoot.addEventListener('click',e=>{
   const button=e.target.closest('button');if(!button)return;
   if(button.id==='prev')this.goToStep(this._index-1);
   if(button.id==='next')this.goToStep(this._index+1);
   if(button.dataset.step!==undefined)this.goToStep(Number(button.dataset.step));
   if(button.id==='show-messages'){const line=this.el('state-json').querySelector('[data-json-path="/messages"]');if(line)this.el('json-scroll').scrollTop=Math.max(0,line.offsetTop-15)}
  });
 }
 load(input){
  if(typeof input==='string'){
   if(new TextEncoder().encode(input).byteLength>5*1024*1024)throw new Error('Document exceeds 5 MiB UTF-8.');
   input=JSON.parse(input);
  }
  validateCase(input);const data=clone(input);
  const previous={data:this._data,index:this._index,html:this.shadowRoot?.innerHTML};
  this._data=data;this._index=0;
  try{this.render()}catch(error){
   this._data=previous.data;this._index=previous.index;
   if(this.shadowRoot&&previous.html!==undefined)this.shadowRoot.innerHTML=previous.html;
   throw new Error(`Viewer render failed; previous view restored: ${error.message}`,{cause:error});
  }
  return this;
 }
 get data(){return this._data?clone(this._data):null}
 get stepIndex(){return this._index}
 goToStep(index){if(!this._data||!Number.isInteger(index)||index<0||index>this._data.steps.length)return;this._index=index;this.render();this.dispatchEvent(new CustomEvent('stepchange',{detail:{index,state:clone(presentStep(this._data,index).state)},bubbles:true,composed:true}))}
 render(){
  const data=this._data;if(!data)return;const index=this._index,p=presentStep(data,index),{state,step,actor,agent,message}=p,e=escapeHTML;
  this.el('title').textContent=data.title;
  this.el('identity').textContent=`${actor(state.our_actor_id)}${state.client_actor_id?' · Клиент: '+actor(state.client_actor_id):''}`;
  this.el('counter').textContent=`Шаг ${index} / ${data.steps.length}`;this.el('prev').disabled=index===0;this.el('next').disabled=index===data.steps.length;
  this.el('steps').innerHTML=[`<button type="button" data-step="0" aria-pressed="${index===0}">Старт<small>Начальное состояние</small></button>`,...data.steps.map((s,i)=>`<button type="button" class="${s.event.type==='message_sent'?'agent-step':''}" data-step="${i+1}" aria-pressed="${index===i+1}">${e(s.event.id)}<small>${e(s.event.label??s.event.title)}</small></button>`)].join('');
  const waiting=agent.waiting_for.map(w=>`<p><strong>${e(actor(w.actor_id))}</strong>: ${e(w.expected)}${w.request_id?` <span class="muted">(${e(w.request_id)})</span>`:''}</p>`).join('');
  this.el('current').innerHTML=`<article class="current ${step?.event.type==='message_sent'?'agent':''}"><div class="step-label">${e(step?eventTypes[step.event.type]:'Исходные данные')}${step?.event.timestamp?' · '+e(step.event.timestamp):''}</div><h2>${e(p.title)}</h2>${message&&message.from_actor===state.our_actor_id?`<blockquote class="sent-preview">${e(message.body_ru??message.body)}</blockquote>`:''}<p class="reason"><strong>Обоснование: </strong>${e(p.explanation||'Не указано в JSON.')}</p><div class="agent-state ${agent.status==='waiting'?'wait':'act'}" data-agent-status="${e(agent.status)}"><div class="state-label">${e(statuses[agent.status])}</div>${waiting}${agent.next_action?`<p>${e(agent.next_action)}</p>`:''}${agent.note?`<p class="note">${e(agent.note)}</p>`:''}</div></article>`;
  const criteria=state.success_criteria,met=criteria.filter(c=>c.status==='met').length;
  this.el('ticket').innerHTML=`<div class="ticket-label">Заявка${state.case_id?' · '+e(state.case_id):''}</div><div><strong>${e(state.intake?.summary??state.goal)}</strong><p class="muted">${e([state.intake?.created_at?'Создана: '+state.intake.created_at:null,state.intake?.escalated_at?'Эскалация: '+state.intake.escalated_at:null].filter(Boolean).join(' · '))}</p>${state.intake?.note?`<p class="muted">${e(state.intake.note)}</p>`:''}</div><div class="completion"><div class="completion-title">Критерии завершения · ${met} / ${criteria.length}</div>${criteria.length?`<ul>${criteria.map(c=>`<li><span class="criterion-icon ${c.status==='met'?'met':''}">${c.status==='met'?'✓':'○'}</span><span class="criterion-description">${e(c.description)}</span><small class="criterion-status">${c.status==='met'?'Подтверждено · '+e(c.evidence_event_ids.join(', ')):'Ожидает подтверждения'}</small></li>`).join('')}</ul>`:'<p class="muted">Не заданы в JSON.</p>'}</div>`;
  this.el('state-json').innerHTML=renderJSON(state,p.patch);this.el('patch-json').textContent=JSON.stringify(p.patch,null,2);
  const first=this.el('state-json').querySelector('.changed');this.el('json-scroll').scrollTop=first?Math.max(0,first.offsetTop-60):0;
  const annotation=n=>`<aside class="reported-context" data-annotation-id="${e(n.id)}"><div class="context-label">${e(n.title??'Пояснение')}</div><p>${e(n.text)}</p>${n.source_event_ids?.length?`<small>Источник: ${e(n.source_event_ids.join(', '))}</small>`:''}</aside>`;
  const notes=state.annotations??[];
  this.el('history').innerHTML=state.messages.map(m=>notes.filter(n=>n.before_message_id===m.event_id).map(annotation).join('')+`<article class="history-message ${m.from_actor===state.our_actor_id?'outgoing':''} ${m.event_id===step?.event.message_id?'selected':''}" data-event-id="${e(m.event_id)}"><div class="message-label">${m.from_actor===state.our_actor_id?'Мы · исходящее':'Входящее'}${m.event_id===step?.event.message_id?' · текущий шаг':''}</div><div class="route">${e(actor(m.from_actor))} → ${e(actor(m.to_actor))}${m.copy_to?.length?` · Копия: ${e(m.copy_to.map(actor).join(', '))}`:''}</div><div class="meta">${e([m.event_id,m.timestamp,m.channel].filter(Boolean).join(' · '))}</div><p>${e(m.body_ru??m.body)}</p></article>`).join('')+notes.filter(n=>!n.before_message_id).map(annotation).join('')||'<p class="muted">Сообщений пока нет. Нажмите «Следующий шаг».</p>';
  this.el('message-count').textContent=`Сообщений: ${state.messages.length}`;
  this.el('history').scrollTop=this.el('history').scrollHeight;
 }
}
if(globalThis.customElements&&!customElements.get('case-state-viewer'))customElements.define('case-state-viewer',CaseStateViewer);
