import assert from 'node:assert/strict';
import {catalogPage} from '../catalog.js';
const entries=Array.from({length:100},(_,i)=>{const id=String(i+1).padStart(3,'0');return {id,case_id:id,filename:id+'.json',title:'Кейс '+id}});
for(let i=1;i<=20;i++){const id=String(i).padStart(3,'0')+'-N4';entries.push({id,case_id:id,filename:id+'.json',title:'Кейс '+id})}
const first=catalogPage(entries);assert.equal(first.totalFiles,120);assert.equal(first.totalGroups,100);assert.equal(first.pages,9);assert.equal(first.groups.length,12);assert.deepEqual(first.groups[0].items.map(c=>c.id),['001','001-N4']);
assert.deepEqual(catalogPage(entries,{query:'002'}).groups[0].items.map(c=>c.id),['002','002-N4']);
assert.equal(catalogPage(entries,{filter:'variants'}).totalFiles,20);
assert.equal(catalogPage(entries,{filter:'base'}).totalFiles,100);
assert.equal(catalogPage(entries,{query:'no-such-case'}).totalFiles,0);
assert.equal(catalogPage(entries,{query:'002-N4.json'}).totalFiles,1);
assert.equal(catalogPage(entries,{page:99}).page,8);
assert.equal(catalogPage(entries,{page:8}).groups.length,4);
assert.equal(catalogPage([],{page:8}).page,0);
const visited=Array.from({length:9},(_,page)=>catalogPage(entries,{page}).groups).flat().flatMap(g=>g.items.map(c=>c.id));assert.equal(new Set(visited).size,120);
console.log('Catalog: 120 files, grouping, search, filters and page boundaries passed');
