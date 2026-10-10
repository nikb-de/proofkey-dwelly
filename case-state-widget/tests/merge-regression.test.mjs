import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {execFileSync} from 'node:child_process';

// The optional baseline exercises the unmerged feature implementation to prove red.
const moduleUrl = process.env.WIDGET_BASELINE
  ? 'data:text/javascript;base64,' + Buffer.from(execFileSync('git', ['show', process.env.WIDGET_BASELINE + ':case-state-widget/viewer.js'])).toString('base64')
  : new URL('../viewer.js', import.meta.url).href;
const {validateCase, CaseStateViewer} = await import(moduleUrl);
const fixture = () => {
  const data=JSON.parse(fs.readFileSync(new URL('../examples/minimal.json',import.meta.url)));
  data.steps=[];
  data.initial_state.messages=[{event_id:'seed',from_actor:data.initial_state.our_actor_id,to_actor:Object.keys(data.initial_state.actors).find(id=>id!==data.initial_state.our_actor_id),body:'Hello'}];
  return data;
};
test('copy recipients must reference known actors',()=>{
  for(const copy_to of [['missing'],42]){
    const data=fixture();data.initial_state.messages[0].copy_to=copy_to;
    assert.throws(()=>validateCase(data),/copy_to/);
  }
});
test('empty copy list is valid',()=>{
  const data=fixture();data.initial_state.messages[0].copy_to=[];
  assert.doesNotThrow(()=>validateCase(data));
});
test('numeric copied actor does not match a string actor key',()=>{
  const data=fixture();data.initial_state.actors['1']={name:'Observer',role:'Reviewer'};
  data.initial_state.messages[0].copy_to=[1];
  assert.throws(()=>validateCase(data),/copy_to/);
});
test('limits reject non-string entries',()=>{
  const data=fixture();data.initial_state.limits=[42];
  assert.throws(()=>validateCase(data),/limits/);
});
test('conversation displays named and escaped copy recipients',()=>{
  const data=fixture();data.initial_state.actors.observer={name:'<Observer>',role:'Reviewer'};
  data.initial_state.messages[0].copy_to=['observer'];validateCase(data);
  const elements=new Map();const viewer=Object.create(CaseStateViewer.prototype);
  viewer._data=data;viewer._index=0;
  viewer.el=id=>{if(!elements.has(id))elements.set(id,{querySelector:()=>null});return elements.get(id)};
  viewer.render();
  assert.match(elements.get('history').innerHTML,/Копия:.*&lt;Observer&gt;.*Reviewer/);
});
