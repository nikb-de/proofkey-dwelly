import {createHash} from 'node:crypto';
import {validateCase} from '../viewer.js';
const fail=(status,message)=>Object.assign(new Error(message),{status});
const normalize=v=>Array.isArray(v)?v.map(normalize):v&&typeof v==='object'?Object.fromEntries(Object.keys(v).sort().map(k=>[k,normalize(v[k])])):v;
const same=(a,b)=>JSON.stringify(normalize(a))===JSON.stringify(normalize(b));
const validId=id=>typeof id==='string'&&/^[a-zA-Z0-9][a-zA-Z0-9_-]{0,99}$/.test(id);
export function createGitHubLibrary({readToken='',fetchImpl=fetch,repo='nikb-de/proofkey-dwelly',branch='main',folder='case-state-widget/cases'}={}){
 const base='https://api.github.com/repos/'+repo,owner=repo.split('/')[0];
 const config={source:'github',repository:repo,branch,folder,read_auth:readToken?'token':'anonymous'};
 async function api(route,{token=readToken,method='GET',body,allow404=false}={}){
  let response;try{response=await fetchImpl(base+route,{method,headers:{Accept:'application/vnd.github+json',...(token?{Authorization:'Bearer '+token}:{}),'X-GitHub-Api-Version':'2022-11-28',...(body?{'Content-Type':'application/json'}:{})},...(body?{body:JSON.stringify(body)}:{}),signal:AbortSignal.timeout(15000),redirect:'error'})}catch{throw fail(502,'GitHub недоступен. Повторите запрос с тем же черновиком.')}
  if(allow404&&response.status===404)return null;
  if(!response.ok){const status=response.status;throw fail(status===401?401:status===403?403:status===404?404:status===409||status===422?409:502,status===401?'GitHub отклонил токен.':status===403?'GitHub запретил действие или исчерпан лимит API.':status===404?'GitHub: репозиторий или файл недоступен. Для приватного репозитория нужен GITHUB_READ_TOKEN.':status===409||status===422?'Конфликт на GitHub. Обновите кейс или повторите тот же запрос.':'Ошибка GitHub.')}
  return response.json();
 }
 const known=new Map();
 const contentPath=id=>'/contents/'+folder+'/'+id+'.json';
 function decode(file){
  if(file.type!=='file'||file.encoding!=='base64'||file.size>5*1024*1024)throw fail(422,'Ожидается JSON-файл до 5 МБ.');
  let data;try{data=JSON.parse(Buffer.from(file.content,'base64').toString('utf8'));validateCase(data)}catch{throw fail(422,'Файл GitHub не соответствует формату кейса.')}
  return data;
 }
 function entry(id,file,data){return {id,filename:id+'.json',title:data.title,case_id:data.initial_state.case_id??null,step_count:data.steps.length,revision:file.sha,source:'github',path:folder+'/'+id+'.json',data}}
 async function get(id){if(!validId(id))throw fail(400,'Некорректный ID кейса.');const file=await api(contentPath(id)+'?ref='+encodeURIComponent(branch));const result=entry(id,file,decode(file));const {data,...meta}=result;known.set(id,meta);return result}
 let cached=null,pending=null;
 async function list({refresh=false}={}){
  if(!refresh&&cached&&Date.now()-cached.at<30000)return cached.value;
  if(pending)return pending;
  pending=(async()=>{const files=await api('/contents/'+folder+'?ref='+encodeURIComponent(branch));if(!Array.isArray(files))throw fail(422,'Папка кейсов не найдена.');
   const names=files.filter(f=>f.type==='file'&&f.name.endsWith('.json')&&validId(f.name.slice(0,-5)));
   if(names.length>=1000)throw fail(422,'Каталог достиг лимита GitHub Contents API; требуется разделить каталог.');
   const cases=names.map(f=>{const id=f.name.slice(0,-5),previous=known.get(id);return previous&&previous.revision===f.sha?previous:{id,filename:f.name,title:'Кейс '+id,case_id:id,step_count:null,revision:f.sha,source:'github',path:folder+'/'+f.name}});
   cases.sort((a,b)=>a.id.localeCompare(b.id));cached={at:Date.now(),value:cases};return cases;
  })();try{return await pending}finally{pending=null}
 }
 async function propose(input,token){
  if(!token)throw fail(401,'Для PR нужен ваш GitHub-токен: Contents: write и Pull requests: write.');
  const {id,data,base_revision,request_id}=input??{};
  if(!validId(id)||!/^\w{8}-\w{4}-\w{4}-\w{4}-\w{12}$/.test(request_id??''))throw fail(400,'Некорректный ID кейса или запроса.');
  try{validateCase(data)}catch(e){throw fail(422,e.message)}
  const body=JSON.stringify(data,null,2)+'\n';if(Buffer.byteLength(body)>5*1024*1024)throw fail(413,'JSON больше 5 МБ.');
  const draftBranch='case-widget/'+request_id;
  const pulls=await api('/pulls?state=all&head='+encodeURIComponent(owner+':'+draftBranch),{token});
  if(pulls.length)return {url:`https://github.com/${repo}/pull/${pulls[0].number}`,number:pulls[0].number,branch:draftBranch,reused:true};
  const head=await api('/git/ref/heads/'+encodeURIComponent(branch),{token});
  const current=await api(contentPath(id)+'?ref='+head.object.sha,{token,allow404:true});
  if(current&&current.sha!==base_revision)throw fail(409,'Кейс в main изменился. Загрузите актуальную версию перед созданием PR.');
  if(!current&&base_revision)throw fail(409,'Исходный файл исчез из main. Обновите список.');
  if(current&&same(decode(current),data))throw fail(409,'В JSON нет изменений относительно main.');
  let existing=await api('/git/ref/heads/'+encodeURIComponent(draftBranch),{token,allow404:true});
  if(!existing)await api('/git/refs',{token,method:'POST',body:{ref:'refs/heads/'+draftBranch,sha:head.object.sha}});
  const draftFile=await api(contentPath(id)+'?ref='+encodeURIComponent(draftBranch),{token,allow404:true});
  if(!draftFile||!same(decode(draftFile),data)){
   if(existing&&draftFile&&draftFile.sha!==current?.sha)throw fail(409,'Черновик с этим ID уже содержит другие данные.');
   await api(contentPath(id),{token,method:'PUT',body:{message:`Update case ${id} from case viewer`,content:Buffer.from(body).toString('base64'),branch:draftBranch,...(draftFile?{sha:draftFile.sha}:{})}});
  }
  const digest=createHash('sha256').update(body).digest('hex').slice(0,12);
  const pr=await api('/pulls',{token,method:'POST',body:{title:`Case ${id}: ${data.title}`.slice(0,240),head:draftBranch,base:branch,draft:true,body:`Предложение из визуализатора кейсов.\n\nФайл: \`${folder}/${id}.json\`\nШагов: ${data.steps.length}. JSON прошёл проверку формата виджета.\n\nПроверьте содержание, источники, ожидания агента и критерии завершения перед слиянием.\n\nSnapshot: ${digest}`}});
  return {url:`https://github.com/${repo}/pull/${pr.number}`,number:pr.number,branch:draftBranch,reused:false};
 }
 return {config,list,get,propose};
}
