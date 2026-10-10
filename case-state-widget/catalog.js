// Catalog projection never loads case JSONs. Only the selected file is fetched.
const compare=(a,b)=>a.localeCompare(b,'ru',{numeric:true,sensitivity:'base'});
export function catalogPage(entries,{query='',filter='all',page=0,pageSize=12}={}){
 const terms=query.toLocaleLowerCase('ru').trim().split(/\s+/).filter(Boolean);
 const groups=new Map();
 for(const entry of entries){
  const code=String((entry.source==='github'?entry.id:entry.case_id)||entry.filename.replace(/\.json$/i,'')||entry.id);
  const match=code.match(/^(\d+)(?:[-_](.+))?$/),group=match?match[1]:code,variant=match?.[2]||'';
  if(filter==='base'&&variant||filter==='variants'&&!variant)continue;
  if(!terms.every(t=>[code,entry.filename,entry.title].join(' ').toLocaleLowerCase('ru').includes(t)))continue;
  if(!groups.has(group))groups.set(group,[]);
  groups.get(group).push({...entry,code,variant});
 }
 const all=[...groups].sort(([a],[b])=>compare(a,b)).map(([id,items])=>({id,items:items.sort((a,b)=>Boolean(a.variant)-Boolean(b.variant)||compare(a.code,b.code))}));
 const pages=Math.max(1,Math.ceil(all.length/pageSize)),index=Math.max(0,Math.min(page,pages-1));
 return {groups:all.slice(index*pageSize,(index+1)*pageSize),page:index,pages,totalGroups:all.length,totalFiles:all.reduce((n,g)=>n+g.items.length,0)};
}
