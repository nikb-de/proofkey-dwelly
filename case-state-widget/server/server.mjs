import http from 'node:http';
import {createHash,timingSafeEqual,randomUUID} from 'node:crypto';
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {validateCase} from '../viewer.js';
import {createGitHubLibrary} from './github.mjs';

const MAX_BYTES=5*1024*1024;
const canonical=v=>Array.isArray(v)?v.map(canonical):v&&typeof v==='object'?Object.fromEntries(Object.keys(v).sort().map(k=>[k,canonical(v[k])])):v;
const metadata=({data,...rest})=>rest;
const failure=(status,message)=>Object.assign(new Error(message),{status});
export async function createLibrary({dataDir,staticDir,access='team',token='',maxEntries=1000,maxStorageBytes=250*1024*1024,github=null}){
 if(!['team','public'].includes(access))throw new Error('LIBRARY_ACCESS must be team or public');
 if(access==='team'&&token.length<24)throw new Error('LIBRARY_TOKEN must contain at least 24 characters');
 dataDir=path.resolve(dataDir);staticDir=await fs.realpath(path.resolve(staticDir));
 if(dataDir===staticDir||dataDir.startsWith(staticDir+path.sep))throw new Error('Storage must be outside the static directory');
 await fs.mkdir(dataDir,{recursive:true});
 const configuredGithub=github;let githubError=null,lastConnectAttempt=0;
 async function connectGithub(){
  if(!configuredGithub||github&&!githubError)return;
  if(Date.now()-lastConnectAttempt<60000)return;
  lastConnectAttempt=Date.now();
  try{await configuredGithub.list({refresh:true});github=configuredGithub;githubError=null}catch(e){github=null;githubError=e.message}
 }
 if(configuredGithub){github=null;await connectGithub()}
 let queue=Promise.resolve();
 async function entries(){return (await fs.readdir(dataDir)).filter(n=>/^[a-f0-9]{64}\.json$/.test(n))}
 async function list(){return (await Promise.all((await entries()).map(async n=>metadata(JSON.parse(await fs.readFile(path.join(dataDir,n),'utf8')))))).sort((a,b)=>b.created_at.localeCompare(a.created_at)||a.id.localeCompare(b.id))}
 async function save(data,filename='case.json'){
  try{validateCase(data)}catch(e){throw failure(422,e.message)}
  const serialized=JSON.stringify(canonical(data));
  if(Buffer.byteLength(serialized)>MAX_BYTES)throw failure(413,'JSON больше 5 МБ.');
  const id=createHash('sha256').update(serialized).digest('hex');
  const task=queue.then(async()=>{
   const target=path.join(dataDir,id+'.json');
   try{return {entry:metadata(JSON.parse(await fs.readFile(target,'utf8'))),created:false}}catch(e){if(e.code!=='ENOENT')throw e}
   const names=await entries();
   if(names.length>=maxEntries)throw failure(507,'Архив заполнен: достигнут лимит кейсов.');
   const used=(await Promise.all(names.map(n=>fs.stat(path.join(dataDir,n))))).reduce((sum,s)=>sum+s.size,0);
   const entry={id,filename:path.basename(String(filename)).replace(/[\x00-\x1f]/g,'').slice(0,180)||'case.json',title:data.title,case_id:typeof data.initial_state.case_id==='string'?data.initial_state.case_id:null,step_count:data.steps.length,created_at:new Date().toISOString(),data};
   const bytes=JSON.stringify(entry);
   if(used+Buffer.byteLength(bytes)>maxStorageBytes)throw failure(507,'Архив заполнен: достигнут лимит объёма.');
   const temporary=path.join(dataDir,'.'+randomUUID()+'.tmp');
   try{await fs.writeFile(temporary,bytes,{flag:'wx',mode:0o600});await fs.rename(temporary,target)}finally{await fs.rm(temporary,{force:true})}
   return {entry:metadata(entry),created:true};
  });
  queue=task.catch(()=>{});return task;
 }
 const mime={'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.css':'text/css; charset=utf-8','.json':'application/json; charset=utf-8','.png':'image/png','.svg':'image/svg+xml','.md':'text/plain; charset=utf-8','.zip':'application/zip'};
 const server=http.createServer(async(req,res)=>{
  res.setHeader('X-Content-Type-Options','nosniff');res.setHeader('Referrer-Policy','same-origin');
  const send=(status,body)=>{res.writeHead(status,{'Content-Type':'application/json; charset=utf-8','Cache-Control':'no-store'});res.end(JSON.stringify(body))};
  try{
   const url=new URL(req.url,'http://localhost');
   if(url.pathname==='/healthz'){res.writeHead(200,{'Content-Type':'text/plain'});res.end('ok');return}
   if(url.pathname.startsWith('/api/')){
    if(url.pathname==='/api/config'&&req.method==='GET'){await connectGithub();send(200,{access,max_file_bytes:MAX_BYTES,...(github?github.config:{source:'server'}),github_requested:Boolean(configuredGithub),...(githubError?{notice:'Пока показан прежний серверный архив. '+githubError}:{})});return}
    if(access==='team'){
     const supplied=req.headers.authorization??'',expected='Bearer '+token;
     const a=Buffer.from(supplied),b=Buffer.from(expected);
     if(a.length!==b.length||!timingSafeEqual(a,b)){send(401,{error:'Введите ключ команды для доступа к архиву.'});return}
    }
    if(github){
     if(url.pathname==='/api/cases'&&req.method==='GET'){send(200,{cases:await github.list({refresh:url.searchParams.get('refresh')==='1'})});return}
     const caseMatch=url.pathname.match(/^\/api\/cases\/([a-zA-Z0-9][a-zA-Z0-9_-]{0,99})$/);
     if(caseMatch&&req.method==='GET'){send(200,await github.get(caseMatch[1]));return}
     if(url.pathname==='/api/github/pull-requests'&&req.method==='POST'){
      if(req.headers.origin&&new URL(req.headers.origin).host!==req.headers.host)throw failure(403,'Запрос с другого сайта запрещён.');
      if(!/^application\/json(?:;|$)/i.test(req.headers['content-type']??''))throw failure(415,'Ожидается application/json.');
      const chunks=[];let bytes=0;for await(const chunk of req){bytes+=chunk.length;if(bytes>MAX_BYTES+128*1024)throw failure(413,'JSON больше 5 МБ.');chunks.push(chunk)}
      let input;try{input=JSON.parse(Buffer.concat(chunks).toString('utf8'))}catch{throw failure(400,'Некорректный JSON.')}
      send(201,await github.propose(input,req.headers['x-github-token']??''));return;
     }
     if(url.pathname==='/api/cases'&&req.method==='POST')throw failure(409,'В режиме GitHub изменения предлагаются через PR.');
    }
    if(url.pathname==='/api/cases'&&req.method==='GET'){send(200,{cases:await list()});return}
    if(url.pathname==='/api/cases'&&req.method==='POST'){
     if(req.headers.origin){const origin=new URL(req.headers.origin);if(origin.host!==req.headers.host)throw failure(403,'Запрос с другого сайта запрещён.')}
     if(!/^application\/json(?:;|$)/i.test(req.headers['content-type']??''))throw failure(415,'Ожидается application/json.');
     const chunks=[];let bytes=0;
     for await(const chunk of req){bytes+=chunk.length;if(bytes>MAX_BYTES+128*1024)throw failure(413,'JSON больше 5 МБ.');chunks.push(chunk)}
     let input;try{input=JSON.parse(Buffer.concat(chunks).toString('utf8'))}catch{throw failure(400,'Некорректный JSON.')}
     const result=await save(input?.data,input?.filename);send(result.created?201:200,result);return;
    }
    const match=url.pathname.match(/^\/api\/cases\/([a-f0-9]{64})$/);
    if(match&&req.method==='GET'){
     let entry;try{entry=JSON.parse(await fs.readFile(path.join(dataDir,match[1]+'.json'),'utf8'))}catch(e){if(e.code==='ENOENT')throw failure(404,'Кейс не найден.');throw e}
     send(200,entry);return;
    }
    send(404,{error:'Не найдено.'});return;
   }
   if(!['GET','HEAD'].includes(req.method)){send(405,{error:'Метод не поддерживается.'});return}
   let pathname;try{pathname=decodeURIComponent(url.pathname)}catch{throw failure(400,'Некорректный путь.')}
   if(pathname.includes('\0')||pathname.split('/').some(p=>p.startsWith('.'))){send(404,{error:'Не найдено.'});return}
   let file=path.resolve(staticDir,'.'+pathname);if(!file.startsWith(staticDir+path.sep)&&file!==staticDir)throw failure(404,'Не найдено.');
   try{if((await fs.stat(file)).isDirectory())file=path.join(file,'index.html');const real=await fs.realpath(file);if(!real.startsWith(staticDir+path.sep))throw failure(404,'Не найдено.');const content=await fs.readFile(real);res.writeHead(200,{'Content-Type':mime[path.extname(file)]??'application/octet-stream','Cache-Control':'no-cache'});res.end(req.method==='HEAD'?undefined:content)}catch(e){if(['ENOENT','ENOTDIR','EISDIR'].includes(e.code))throw failure(404,'Не найдено.');throw e}
  }catch(e){if(!res.headersSent)send(e.status??500,{error:e.status?e.message:'Ошибка сервера. JSON не сохранён.'});else res.end()}
 });
 server.requestTimeout=15000;server.headersTimeout=10000;
 return {server,save,list};
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 const dataDir=process.env.CASES_DIR??'/data/cases';
 const app=await createLibrary({dataDir,staticDir:process.env.STATIC_DIR??new URL('../',import.meta.url).pathname,access:process.env.LIBRARY_ACCESS??'team',token:process.env.LIBRARY_TOKEN??'',github:process.env.LIBRARY_SOURCE==='github'?createGitHubLibrary({readToken:process.env.GITHUB_READ_TOKEN??''}):null});
 if(process.env.SEED_DIR&&process.env.LIBRARY_SOURCE!=='github'){for(const name of ['case-002.json','examples/case-002-channel-failure.json']){const data=JSON.parse(await fs.readFile(path.join(process.env.SEED_DIR,name),'utf8'));await app.save(data,path.basename(name))}}
 app.server.listen(Number(process.env.PORT??8080),process.env.HOST??'0.0.0.0',()=>console.log('Case library is listening'));
}
