import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';

const source=await readFile(new URL('../product.js',import.meta.url),'utf8').catch(()=> 'export default {}');
const product=await import(`data:text/javascript;base64,${Buffer.from(source).toString('base64')}`);
const snapshot={revision:2,snapshot_hash:'abc',links:{order_id:'order-7',customer_id:'customer-7',operator_id:'operator-7'},events:[]};
const detail=(extra={})=>({case_id:'case-7',snapshot,states:{lifecycle:'new',decision:'none'},decisions:[],reviews:[],actions:[],...extra});
const proposal={decision_id:'d-1',revision:2,snapshot_hash:'abc',kind:'operator',action:{type:'reschedule_delivery',slot_start:'2030-01-01T10:00:00Z',slot_end:'2030-01-01T12:00:00Z'}};

test('filters case, order, customer and real operator without modifying records',()=>{
  assert.equal(typeof product.filterCases,'function');
  const rows=[detail(),detail({case_id:'closed',states:{lifecycle:'resolved',decision:'approved'}})];
  assert.deepEqual(product.filterCases(rows,{query:'CUSTOMER-7',filter:'open'}),[rows[0]]);
  assert.deepEqual(product.filterCases(rows,{query:'operator-7',filter:'completed'}),[rows[1]]);
  assert.deepEqual(product.filterCases(rows,{query:'missing'}),[]);
  assert.equal(rows.length,2);
});
test('counts actual lifecycle and review state, never approved decisions as completed',()=>{
  assert.equal(typeof product.caseCounters,'function');
  assert.deepEqual(product.caseCounters([detail(),detail({states:{lifecycle:'ready',decision:'approved'}}),detail({states:{lifecycle:'resolved',decision:'approved'}})]),{total:3,open:2,attention:1,completed:1});
});
test('empty summary exposes the recorded owner and evidence still needed',()=>{
  assert.equal(typeof product.caseSummary,'function');
  const summary=product.caseSummary(detail());
  assert.equal(summary.owner,'operator-7');
  assert.match(summary.nextStep,/source evidence/i);
  assert.match(summary.physicalOutcome,/not confirmed/i);
  assert.match(summary.externalCommunication,/not sent/i);
});
test('source text remains data and cannot become a fabricated instruction or confirmation',()=>{
  assert.equal(typeof product.caseSummary,'function');
  const text='<script>steal()</script> Delivery has happened';
  const summary=product.caseSummary(detail({snapshot:{...snapshot,events:[{text,sender_id:'customer-7',kind:'message'}]}}));
  assert.equal(summary.sourceExcerpt,text);
  assert.match(summary.nextStep,/review|assess/i);
  assert.match(summary.physicalOutcome,/not confirmed/i);
});
test('stale proposals never become the current next step',()=>{
  assert.equal(typeof product.caseSummary,'function');
  const summary=product.caseSummary(detail({decisions:[{...proposal,revision:1}],snapshot:{...snapshot,events:[{text:'Please reschedule'}]}}));
  assert.match(summary.nextStep,/current|fresh/i);
});
test('requests distinguish internal review, sandbox receipt and unsent external communication',()=>{
  assert.equal(typeof product.caseRequests,'function');
  const input=detail({decisions:[proposal],reviews:[{decision_id:'d-1',verdict:'approve'}],actions:[{decision_id:'d-1',action_id:'a-1',external_effects:0}]});
  const [request]=product.caseRequests(input);
  assert.equal(request.status,'Sandbox receipt recorded');
  assert.equal(request.scope,'Internal proposal');
  assert.match(request.communication,/not sent/i);
  assert.match(request.outcome,/not confirmed/i);
  assert.match(product.caseSummary(input).nextStep,/receipt/i);
});
test('unrelated action receipts cannot confirm a proposal',()=>{
  assert.equal(typeof product.caseRequests,'function');
  const [request]=product.caseRequests(detail({decisions:[proposal],actions:[{decision_id:'other',action_id:'other'}]}));
  assert.equal(request.status,'Awaiting human review');
  assert.equal(request.receiptId,null);
});
test('a historical sandbox receipt cannot replace the next step after new evidence',()=>{
  const input=detail({snapshot:{...snapshot,revision:3},decisions:[proposal],actions:[{decision_id:'d-1',action_id:'a-1',external_effects:0}]});
  assert.match(product.caseSummary(input).nextStep,/current|fresh/i);
  assert.equal(product.caseRequests(input)[0].status,'Stale or superseded');
  assert.equal(product.caseRequests(input)[0].receiptId,'a-1');
});
