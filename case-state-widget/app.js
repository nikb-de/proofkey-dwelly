import './viewer.js';
const viewer=document.querySelector('case-state-viewer');
const status=document.getElementById('load-status'),error=document.getElementById('load-error'),editor=document.getElementById('json-input');
let activeName='';
function load(text,name){
 const data=JSON.parse(text);viewer.load(data);activeName=name;
 status.textContent=`Загружен ${name} · шагов: ${data.steps.length}`;
 error.textContent='';editor.value=JSON.stringify(data,null,2);
 document.getElementById('download').disabled=false;
}
function failure(err){error.textContent=`JSON не загружен: ${String(err.message).replace(/[.]+$/, '')}.${viewer.data?' Предыдущий кейс сохранён.':''}`}
document.getElementById('file').addEventListener('change',async e=>{
 const file=e.target.files?.[0];if(!file)return;
 try{if(file.size>5*1024*1024)throw new Error('Файл больше 5 МБ');load(await file.text(),file.name)}catch(err){failure(err)}finally{e.target.value=''}
});
document.getElementById('apply-json').addEventListener('click',()=>{try{load(editor.value,'JSON из редактора')}catch(err){failure(err)}});
document.getElementById('download').addEventListener('click',()=>{
 const url=URL.createObjectURL(new Blob([JSON.stringify(viewer.data,null,2)+'\n'],{type:'application/json'}));
 const a=document.createElement('a');a.href=url;a.download=activeName.endsWith('.json')?activeName:'case.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
});
try{const response=await fetch(new URL('./case-002.json',import.meta.url),{cache:'no-store'});if(!response.ok)throw new Error(`HTTP ${response.status}`);load(await response.text(),'case-002.json')}catch(err){failure(err)}
