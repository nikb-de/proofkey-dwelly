import './viewer.js';
const viewer=document.querySelector('case-state-viewer');
const status=document.getElementById('load-status'),error=document.getElementById('load-error'),editor=document.getElementById('json-input');
const picker=document.getElementById('case-picker'),libraryStatus=document.getElementById('library-status'),retry=document.getElementById('retry-save');
let activeName='',activeId='',available=false,access='team',busy=false;
let token=sessionStorage.getItem('case-library-token')??'';
function localLoad(data,name){viewer.load(data);activeName=name;activeId='';status.textContent=`Загружен ${name} · шагов: ${data.steps.length}`;error.textContent='';editor.value=JSON.stringify(data,null,2);document.getElementById('download').disabled=false;retry.hidden=true}
function failure(err){error.textContent=String(err.message).replace(/[.]+$/,'')+'.'}
function setBusy(value){busy=value;for(const id of ['file','apply-json','case-picker','refresh-cases','retry-save','connect-library'])document.getElementById(id).disabled=value}
async function api(route,options={}){
 const response=await fetch('/api'+route,{...options,headers:{...(token?{Authorization:'Bearer '+token}:{}),...(options.body?{'Content-Type':'application/json'}:{}),...options.headers},cache:'no-store'});
 let body;try{body=await response.json()}catch{throw new Error('Сервер архива недоступен')}
 if(!response.ok)throw new Error(body.error??`Ошибка архива: HTTP ${response.status}`);return body;
}
async function refresh(){
 const {cases}=await api('/cases');
 picker.replaceChildren(new Option('Выберите сохранённый кейс',''));
 for(const c of cases){const date=new Date(c.created_at).toLocaleString('ru-RU');picker.add(new Option(`${c.title} · шагов: ${c.step_count} · ${date} · ${c.id.slice(0,6)}`,c.id))}
 picker.value=activeId;libraryStatus.textContent=`На сервере: ${cases.length}`;return cases;
}
async function openSaved(id){const entry=await api('/cases/'+encodeURIComponent(id));localLoad(entry.data,entry.filename);activeId=entry.id;picker.value=activeId;status.textContent=`Сохранён на сервере · шагов: ${entry.data.steps.length}`;history.replaceState(null,'','#saved='+activeId)}
async function persist(){
 if(!available){status.textContent='Только в этой вкладке · серверное сохранение недоступно';return}
 try{const {entry}=await api('/cases',{method:'POST',body:JSON.stringify({filename:activeName,data:viewer.data})});activeId=entry.id;status.textContent=`Сохранён на сервере · шагов: ${entry.step_count}`;retry.hidden=true;history.replaceState(null,'','#saved='+activeId);try{await refresh()}catch(e){failure(new Error('Кейс сохранён, но список не обновился: '+e.message))}}
 catch(e){status.textContent='Не сохранён на сервере · JSON остаётся во вкладке';retry.hidden=false;throw e}
}
async function importText(text,name){const data=JSON.parse(text);localLoad(data,name);picker.value='';history.replaceState(null,'',location.pathname+location.search);await persist()}
async function run(action){if(busy)return;setBusy(true);error.textContent='';try{await action()}catch(e){failure(e)}finally{setBusy(false)}}
document.getElementById('file').addEventListener('change',e=>{const file=e.target.files?.[0];if(!file)return;run(async()=>{try{if(file.size>5*1024*1024)throw new Error('Файл больше 5 МБ');await importText(await file.text(),file.name)}finally{e.target.value=''}})});
document.getElementById('apply-json').addEventListener('click',()=>run(()=>importText(editor.value,'case-edited.json')));
retry.addEventListener('click',()=>run(persist));
picker.addEventListener('change',()=>{if(picker.value)run(async()=>{try{await openSaved(picker.value)}catch(e){picker.value=activeId;throw e}})});
document.getElementById('refresh-cases').addEventListener('click',()=>run(refresh));
document.getElementById('connect-library').addEventListener('click',()=>run(async()=>{
 token=document.getElementById('library-key').value.trim();
 const cases=await refresh();sessionStorage.setItem('case-library-token',token);document.getElementById('library-key').value='';document.getElementById('library-auth').hidden=true;
 const requested=location.hash.match(/^#saved=([a-f0-9]{64})$/)?.[1];
 if(retry.hidden===false){await persist()}else if(requested||cases.length)await openSaved(requested??cases[0].id);
}));
document.getElementById('download').addEventListener('click',()=>{const url=URL.createObjectURL(new Blob([JSON.stringify(viewer.data,null,2)+'\n'],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download=activeName.endsWith('.json')?activeName:'case.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)});
await run(async()=>{
 const response=await fetch(new URL('./case-002.json',import.meta.url),{cache:'no-store'});if(!response.ok)throw new Error(`HTTP ${response.status}`);localLoad(await response.json(),'case-002.json');
 try{const config=await api('/config');available=true;access=config.access;document.getElementById('library').hidden=false;document.getElementById('save-hint').textContent=access==='public'?'Загруженные JSON сохраняются в общей библиотеке':'Загруженные JSON сохраняются в архиве команды';
  if(access==='team'&&!token){document.getElementById('library-auth').hidden=false;libraryStatus.textContent='Введите ключ команды';return}
  const cases=await refresh();const requested=location.hash.match(/^#saved=([a-f0-9]{64})$/)?.[1];const selected=requested??cases.find(c=>c.filename==='case-002.json')?.id??cases[0]?.id;if(selected)await openSaved(selected);
 }catch(e){if(available){document.getElementById('library-auth').hidden=access!=='team';failure(e)}else document.getElementById('save-hint').textContent='Локальный режим · серверный архив не подключён'}
});
