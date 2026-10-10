import './viewer.js';
import {catalogPage} from './catalog.js';
const viewer=document.querySelector('case-state-viewer');
const status=document.getElementById('load-status'),error=document.getElementById('load-error'),editor=document.getElementById('json-input');
const picker=document.getElementById('case-picker'),libraryStatus=document.getElementById('library-status'),retry=document.getElementById('retry-save');
let activeName='',activeId='',available=false,access='team',busy=false,source='server',baseRevision=null,proposalId=crypto.randomUUID(),catalog=[],githubRequested=false;
const prPanel=document.getElementById('pr-panel'),prResult=document.getElementById('pr-result');
let token=sessionStorage.getItem('case-library-token')??'';
function localLoad(data,name){viewer.load(data);activeName=name;activeId='';baseRevision=null;proposalId=crypto.randomUUID();prResult.replaceChildren();status.textContent=`Загружен ${name} · шагов: ${data.steps.length}`;error.textContent='';editor.value=JSON.stringify(data,null,2);document.getElementById('download').disabled=false;retry.hidden=true;currentLabel()}
function failure(err){error.textContent=String(err.message).replace(/[.]+$/,'')+'.';document.getElementById('catalog-error').textContent=error.textContent}
function setBusy(value){busy=value;for(const id of ['file','apply-json','case-picker','refresh-cases','retry-save','connect-library','propose-pr','create-pr'])document.getElementById(id).disabled=value}
async function api(route,options={}){
 const response=await fetch('/api'+route,{...options,headers:{...(token?{Authorization:'Bearer '+token}:{}),...(options.body?{'Content-Type':'application/json'}:{}),...options.headers},cache:'no-store'});
 let body;try{body=await response.json()}catch{throw new Error('Сервер архива недоступен')}
 if(!response.ok)throw new Error(body.error??`Ошибка архива: HTTP ${response.status}`);return body;
}
const dialog=document.getElementById('catalog-dialog'),search=document.getElementById('catalog-search');
let catalogQuery='',catalogFilter='all',catalogIndex=0;
function currentLabel(){document.getElementById('active-case').textContent=activeId?viewer.data.title:'Локальный JSON';}
function renderCatalog(){
 const result=catalogPage(catalog,{query:catalogQuery,filter:catalogFilter,page:catalogIndex});catalogIndex=result.page;
 const root=document.getElementById('catalog-results');root.replaceChildren();
 for(const group of result.groups){
  const section=document.createElement('section');section.className='case-group';
  const heading=document.createElement('h3');heading.textContent=group.id;section.append(heading);
  const items=document.createElement('div');items.className='case-entries';
  for(const c of group.items){
   const button=document.createElement('button');button.type='button';button.className='case-entry';button.dataset.caseId=c.id;button.setAttribute('aria-current',String(c.id===activeId));
   const copy=document.createElement('span');copy.className='case-entry-copy';
   const title=document.createElement('span');title.className='case-entry-title';title.textContent=c.title==='Кейс '+c.id?(c.variant?'Сценарий '+c.variant:'Основной сценарий'):c.title;
   const meta=document.createElement('span');meta.className='case-entry-meta';meta.textContent=c.filename+(c.step_count==null?'':' · '+c.step_count+' шагов');copy.append(title,meta);
   const tag=document.createElement('span');tag.className='scenario-tag';tag.textContent=c.id===activeId?'Открыт':c.variant?'Вариант':'Основной';button.append(copy,tag);
   button.addEventListener('click',()=>run(async()=>{await openSaved(c.id);dialog.close()}));items.append(button);
  }
  section.append(items);root.append(section);
 }
 if(!result.totalFiles){const empty=document.createElement('p');empty.className='catalog-empty';empty.textContent=catalogQuery?'Ничего не найдено. Попробуйте другой номер или имя файла.':'В этой категории пока нет кейсов.';root.append(empty)}
 document.getElementById('catalog-results-count').textContent=result.totalFiles+' JSON';
 document.getElementById('catalog-page-status').textContent=`Страница ${result.page+1} из ${result.pages} · кейсов: ${result.totalGroups}`;
 document.getElementById('catalog-prev').disabled=result.page===0;document.getElementById('catalog-next').disabled=result.page+1===result.pages;
}
picker.addEventListener('click',()=>{renderCatalog();dialog.showModal();search.focus()});
document.getElementById('catalog-close').addEventListener('click',()=>dialog.close());
search.addEventListener('input',()=>{catalogQuery=search.value;catalogIndex=0;renderCatalog()});
for(const button of document.querySelectorAll('[data-filter]'))button.addEventListener('click',()=>{catalogFilter=button.dataset.filter;catalogIndex=0;for(const b of document.querySelectorAll('[data-filter]'))b.setAttribute('aria-pressed',String(b===button));renderCatalog()});
for(const [id,delta] of [['catalog-prev',-1],['catalog-next',1]])document.getElementById(id).addEventListener('click',()=>{catalogIndex+=delta;renderCatalog();document.getElementById('catalog-results').scrollTop=0});
async function refresh(force=false){
 const {cases}=await api('/cases'+(force?'?refresh=1':''));catalog=cases;
 document.getElementById('library-count').textContent=cases.length;
 libraryStatus.textContent=source==='github'?'GitHub · main':'Общая библиотека';renderCatalog();return cases;
}
async function openSaved(id){const entry=await api('/cases/'+encodeURIComponent(id));localLoad(entry.data,entry.filename);activeId=entry.id;baseRevision=entry.revision??null;document.getElementById('pr-case-id').value=activeId;catalog=catalog.map(c=>c.id===entry.id?{...c,...entry,data:undefined}:c);currentLabel();renderCatalog();status.textContent=source==='github'?`GitHub · ${entry.path} · ${entry.revision.slice(0,7)}`:`Сохранён на сервере · шагов: ${entry.data.steps.length}`;history.replaceState(null,'','#saved='+activeId)}
async function persist(){
 if(githubRequested){status.textContent='Локальный черновик · предложите изменения через PR';retry.hidden=true;return}
 if(!available){status.textContent='Только в этой вкладке · серверное сохранение недоступно';return}
 try{const {entry}=await api('/cases',{method:'POST',body:JSON.stringify({filename:activeName,data:viewer.data})});activeId=entry.id;status.textContent=`Сохранён на сервере · шагов: ${entry.step_count}`;retry.hidden=true;history.replaceState(null,'','#saved='+activeId);try{await refresh()}catch(e){failure(new Error('Кейс сохранён, но список не обновился: '+e.message))}}
 catch(e){status.textContent='Не сохранён на сервере · JSON остаётся во вкладке';retry.hidden=false;throw e}
}
async function importText(text,name,editing=false){const data=JSON.parse(text),priorId=activeId,priorRevision=baseRevision;localLoad(data,name);if(source==='github'){activeId=editing?priorId:'';baseRevision=editing?priorRevision:null;const suggested=editing&&priorId?priorId:String(data.initial_state.case_id??name.replace(/\.json$/i,'')).replace(/[^a-zA-Z0-9_-]/g,'-').slice(0,100);document.getElementById('pr-case-id').value=suggested;prPanel.open=false;}currentLabel();history.replaceState(null,'',location.pathname+location.search);await persist()}
async function run(action){if(busy)return;setBusy(true);error.textContent='';document.getElementById('catalog-error').textContent='';try{await action()}catch(e){failure(e)}finally{setBusy(false)}}
document.getElementById('file').addEventListener('change',e=>{const file=e.target.files?.[0];if(!file)return;run(async()=>{try{if(file.size>5*1024*1024)throw new Error('Файл больше 5 МБ');await importText(await file.text(),file.name)}finally{e.target.value=''}})});
document.getElementById('apply-json').addEventListener('click',()=>run(()=>importText(editor.value,activeName||'case-edited.json',true)));
retry.addEventListener('click',()=>run(persist));

document.getElementById('refresh-cases').addEventListener('click',()=>run(()=>refresh(true)));
document.getElementById('connect-library').addEventListener('click',()=>run(async()=>{
 token=document.getElementById('library-key').value.trim();
 const cases=await refresh();sessionStorage.setItem('case-library-token',token);document.getElementById('library-key').value='';document.getElementById('library-auth').hidden=true;
 const requested=location.hash.match(/^#saved=([a-zA-Z0-9][a-zA-Z0-9_-]{0,99})$/)?.[1];
 if(retry.hidden===false){await persist()}else if(requested||cases.length)await openSaved(requested??cases[0].id);
}));
document.getElementById('download').addEventListener('click',()=>{const url=URL.createObjectURL(new Blob([JSON.stringify(viewer.data,null,2)+'\n'],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download=activeName.endsWith('.json')?activeName:'case.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)});
document.getElementById('propose-pr').addEventListener('click',()=>{prPanel.open=true});
document.getElementById('create-pr').addEventListener('click',()=>run(async()=>{
 const id=document.getElementById('pr-case-id').value.trim(),writeToken=document.getElementById('pr-token').value.trim();
 if(!writeToken)throw new Error('Введите ваш GitHub-токен для создания PR');
 const result=await api('/github/pull-requests',{method:'POST',headers:{'X-GitHub-Token':writeToken},body:JSON.stringify({id,data:viewer.data,base_revision:id===activeId?baseRevision:null,request_id:proposalId})});
 document.getElementById('pr-token').value='';const link=document.createElement('a');link.href=result.url;link.target='_blank';link.rel='noopener';link.textContent=`Открыть PR #${result.number}`;prResult.replaceChildren('Черновик PR создан. ',link);status.textContent='Изменения предложены · в библиотеке появятся после слияния PR';
}));
await run(async()=>{
 const response=await fetch(new URL('./case-002.json',import.meta.url),{cache:'no-store'});if(!response.ok)throw new Error(`HTTP ${response.status}`);localLoad(await response.json(),'case-002.json');
 try{const config=await api('/config');available=true;access=config.access;source=config.source??'server';githubRequested=Boolean(config.github_requested);if(config.notice)failure(new Error(config.notice));document.getElementById('propose-pr').hidden=source!=='github';document.getElementById('source-link').hidden=source!=='github';document.getElementById('pr-panel').hidden=source!=='github';document.getElementById('library').hidden=false;document.getElementById('save-hint').textContent=githubRequested?(source==='github'?'Кейсы из main · изменения через PR':'GitHub ожидает подключения · новые JSON остаются черновиками'):access==='public'?'Загруженные JSON сохраняются в общей библиотеке':'Загруженные JSON сохраняются в архиве команды';
  if(access==='team'&&!token){document.getElementById('library-auth').hidden=false;libraryStatus.textContent='Введите ключ команды';return}
  const cases=await refresh();const requested=location.hash.match(/^#saved=([a-zA-Z0-9][a-zA-Z0-9_-]{0,99})$/)?.[1];const selected=(cases.some(c=>c.id===requested)?requested:null)??cases.find(c=>['case-002.json','002.json'].includes(c.filename))?.id??cases[0]?.id;if(selected)await openSaved(selected);if(config.notice)failure(new Error(config.notice));
 }catch(e){if(available){document.getElementById('library-auth').hidden=access!=='team';failure(e)}else document.getElementById('save-hint').textContent='Локальный режим · серверный архив не подключён'}
});

setInterval(()=>{if(source==='github'&&available&&!busy&&!document.hidden)refresh().catch(()=>{libraryStatus.textContent='GitHub временно недоступен · показан прежний список'})},60000);
setInterval(async()=>{if(githubRequested&&source!=='github'&&!busy&&!document.hidden){try{const config=await api('/config');if(config.source==='github'){source='github';document.getElementById('propose-pr').hidden=false;document.getElementById('source-link').hidden=false;document.getElementById('pr-panel').hidden=false;document.getElementById('save-hint').textContent='Кейсы из main · изменения через PR';error.textContent='';await refresh(true);status.textContent='GitHub подключён · выберите кейс'}}catch{}}},60000);
