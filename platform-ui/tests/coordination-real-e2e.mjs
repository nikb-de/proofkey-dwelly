// Opt-in real HTTP / Chrome / PostgreSQL-backed UI verification. Creates only fresh synthetic cases.
import assert from 'node:assert/strict';
import {mkdir,writeFile} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
import {execFile} from 'node:child_process';
import {promisify} from 'node:util';

if(process.env.PROOFKEY_COORDINATION_REAL_E2E!=='1'){
  console.log('SKIP: set PROOFKEY_COORDINATION_REAL_E2E=1 to create fresh local synthetic cases.');
  process.exit(0);
}
const origin=new URL(process.env.PROOFKEY_BASE_URL || 'http://127.0.0.1:8105');
assert.ok(origin.protocol==='http:' && ['127.0.0.1','localhost','[::1]'].includes(origin.hostname) && !origin.username && !origin.password && origin.pathname==='/' && !origin.search && !origin.hash,'Loopback HTTP origin required');
const root=fileURLToPath(new URL('../../',import.meta.url));
const runId=`${Date.now()}-${crypto.randomUUID().slice(0,8)}`;
const output=path.join(root,'docs/verification/coordination-review-ui-2026-10-10',`real-e2e-${runId}`);
await mkdir(output,{recursive:true});
const report={run_id:runId,base_url:origin.origin,qualification:'Real Chrome UI and real localhost HTTP against PostgreSQL; synthetic local actors and source messages, not authenticated customer/carrier activity.',status:'running',model_calls:0,external_effects:0,physical_delivery:'not_confirmed',case_ids:[],http:[],ui_commands:[],snapshots:[],screenshots:[],blocked_requests:[],browser_errors:[]};
const owned=new Set();
async function http(route,body,status=200){
  const method=body?'POST':'GET';
  if(body)assert.ok(route==='/api/platform/cases' || [...owned].some(id=>route.startsWith(`/api/platform/cases/${id}/`)),'Only owned fresh cases may be mutated');
  const response=await fetch(new URL(route,origin),{method,redirect:'error',headers:body?{'Content-Type':'application/json','X-ProofKey-Request':'platform-v1','Idempotency-Key':`real-e2e-${crypto.randomUUID()}`}:{},body:body?JSON.stringify(body):undefined});
  const result=await response.json();report.http.push({method,path:route,status:response.status,request:body || null,response:result});
  assert.equal(response.status,status,JSON.stringify(result));return result;
}
const detail=async id=>(await http(`/api/platform/cases/${id}`)).case;
const terms={slot_start:'2030-06-03T10:00:00+00:00',slot_end:'2030-06-03T12:00:00+00:00',handover:'recipient_only',recipient_present:true,charge:{amount_minor:1250,currency:'GBP'}};
async function create(suffix){
  const id=`coord-ui-${runId}-${suffix}`;await http(`/api/platform/cases/${id}`,null,404);owned.add(id);report.case_ids.push(id);
  await http('/api/platform/cases',{case_id:id,links:{order_id:`SYNTHETIC-${suffix}-${runId}`,customer_id:'customer',operator_id:'operator'},participants:['customer','operator','dispatch'],language:'en'},201);return id;
}
async function append(id,eventId,sender,text){
  const before=await detail(id);
  if(before.snapshot.events.some(event=>event.event_id===eventId))return;
  const event={event_id:eventId,occurred_at:'2030-06-01T10:00:00+00:00',channel:sender==='dispatch'?'email':'chat',sender_id:sender,recipient_ids:['operator'],kind:'message',text:`SYNTHETIC LOCAL E2E ONLY. ${text}`,media:null};
  await http(`/api/platform/cases/${id}/events`,{expected_revision:before.snapshot.revision,event});
}
let browser;
try{
  const cap=await http('/api/platform/capabilities');assert.equal(cap.execution_mode,'local_sandbox');assert.equal(cap.external_effects,0);assert.equal(cap.coordination.customer_acceptance,'operator_assisted_local_preview_not_authenticated');assert.equal(cap.adapters.find(x=>x.id==='cases').mode,'local_postgresql');
  const {chromium}=await import(process.env.PROOFKEY_PLAYWRIGHT_MODULE || '/Users/nbk/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright/index.mjs');
  browser=await chromium.launch({headless:true,executablePath:process.env.PROOFKEY_CHROME || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'});
  const context=await browser.newContext({viewport:{width:1440,height:1000}});
  await context.route('**/*',async route=>{
    const request=route.request(),url=new URL(request.url());
    const safe=url.origin===origin.origin && (request.method()==='GET' || (request.method()==='POST' && [...owned].some(id=>url.pathname===`/api/platform/cases/${id}/coordination`)));
    if(!safe){report.blocked_requests.push({url:url.href,method:request.method()});return route.abort();}return route.continue();
  });
  const team=await context.newPage(),customer=await context.newPage();
  for(const page of [team,customer]){page.setDefaultTimeout(12000);page.on('pageerror',e=>report.browser_errors.push(e.message));}
  async function openTeam(id){await team.goto(`${origin.origin}/#case=${id}`);await team.reload();await team.locator('#coordination-command').waitFor({state:'attached'});}
  async function screenshot(page,name){const target=path.join(output,name);await page.screenshot({path:target,fullPage:true});report.screenshots.push(target);}
  async function check(id,command,phase,previous){
    const d=await detail(id),c=d.coordination;
    assert.equal(c.phase,phase);assert.equal(c.version,(previous?.coordination?.version || 0)+1);assert.equal(c.mode,'local_sandbox');assert.equal(c.external_effects,0);assert.equal(c.physical_delivery,'not_confirmed');
    assert.equal(c.revision,d.snapshot.revision);assert.equal(c.snapshot_hash,d.snapshot.snapshot_hash);assert.equal(c.audit_history.length,c.version);
    const audit=c.audit_history.at(-1);assert.equal(audit.command,command);assert.equal(audit.version,c.version);assert.equal(audit.revision,c.revision);assert.ok(d.snapshot.events.some(e=>e.event_id===`coord-${audit.audit_id}` && e.channel==='internal'));
    assert.equal(d.snapshot.revision-previous.snapshot.revision,command==='record_local_acceptance'?2:1);
    if(!['confirm_booking','escalate'].includes(command))assert.notEqual(c.phase,'booking_confirmed');
    report.snapshots.push({case_id:id,command,phase:c.phase,version:c.version,revision:c.revision,event_count:d.snapshot.events.length,snapshot_hash:d.snapshot.snapshot_hash,audit,consent:c.consent,pending_request:c.pending_request,operation_receipts:c.operation_receipts});return d;
  }
  async function act(id,command,phase,{evidence,configure}={}){
    const previous=await detail(id);await openTeam(id);
    if(command==='initialize')await team.locator('#coordination-panel details').filter({has:team.locator('#coordination-form')}).locator('summary').first().click();
    if(await team.locator('#coordination-command').inputValue()!==command)await team.selectOption('#coordination-command',command);
    if(configure)await configure();
    if(evidence)await team.locator(`[name="coordination-evidence"][value="${evidence}"]`).check();
    assert.equal(await team.locator('#coordination-submit').isDisabled(),true);await team.locator('#coordination-reviewed').check();assert.equal(await team.locator('#coordination-submit').isDisabled(),false);
    const pending=team.waitForResponse(r=>r.url()===`${origin.origin}/api/platform/cases/${id}/coordination` && r.request().method()==='POST');
    await team.locator('#coordination-submit').click();const response=await pending,body=await response.json();
    report.ui_commands.push({case_id:id,command,status:response.status(),request:response.request().postDataJSON(),headers:response.request().headers(),response:body});assert.equal(response.status(),200,JSON.stringify(body));
    await team.locator('#coordination-status').filter({hasText:'Local coordination record saved.'}).waitFor();return check(id,command,phase,previous);
  }
  async function enterTerms(){await team.fill('#coordination-start',terms.slot_start);await team.fill('#coordination-end',terms.slot_end);await team.selectOption('#coordination-handover',terms.handover);await team.fill('#coordination-amount',String(terms.charge.amount_minor));await team.fill('#coordination-currency',terms.charge.currency);}
  async function setup(id){
    await append(id,'request-cancel','customer','Please cancel the existing booking and review a new delivery window.');
    let d=await detail(id);
    if(!d.coordination)d=await act(id,'initialize','booked',{configure:async()=>{await team.selectOption('#coordination-dispatch','dispatch');await team.fill('#coordination-booking',`synthetic-${runId}`);await enterTerms();}});
    if(d.coordination.phase==='booked')d=await act(id,'request_cancellation','cancellation_pending',{evidence:'request-cancel'});
    assert.equal(d.coordination.pending_request.status,'pending_local_readback');assert.equal(d.coordination.operation_receipts.length,0);
    await append(id,'cancel-readback','dispatch',`Cancellation confirmed locally for request ${d.coordination.pending_request.request_id}. No carrier was contacted.`);
    d=await act(id,'confirm_cancellation','awaiting_terms',{evidence:'cancel-readback'});assert.equal(d.coordination.operation_receipts[0].status,'confirmed_locally');
    await append(id,'offer-source','dispatch',`Offer: ${terms.slot_start} to ${terms.slot_end}; recipient only; recipient required; surcharge 1250 minor units GBP.`);
    d=await act(id,'record_offer','awaiting_consent',{evidence:'offer-source',configure:enterTerms});assert.deepEqual(d.coordination.offer.terms,terms);assert.equal(d.coordination.consent,null);return d;
  }
  let id=process.env.PROOFKEY_RESUME_CASE;
  if(id){assert.match(id,/^coord-ui-\d+-[a-f0-9]{8}-customer$/);owned.add(id);report.case_ids.push(id);report.resumed_test_case=id;}else id=await create('customer');
  let d=await setup(id);
  await screenshot(team,'team-awaiting-consent-desktop.png');await team.setViewportSize({width:390,height:844});await screenshot(team,'team-awaiting-consent-mobile.png');assert.equal(await team.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);await team.setViewportSize({width:1440,height:1000});
  await customer.goto(`${origin.origin}/customer.html?case=${id}`);await customer.locator('#local-acceptance-ack').waitFor();
  assert.match(await customer.locator('#customer-coordination').innerText(),/1,250 minor units.*GBP/);assert.equal(await customer.locator('#submit-local-acceptance').isDisabled(),true);
  await screenshot(customer,'customer-awaiting-consent-desktop.png');await customer.setViewportSize({width:390,height:844});await screenshot(customer,'customer-awaiting-consent-mobile.png');assert.equal(await customer.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
  const beforeAcceptance=await detail(id);await customer.locator('#local-acceptance-ack').check();
  const acceptanceResponse=customer.waitForResponse(r=>r.url()===`${origin.origin}/api/platform/cases/${id}/coordination` && r.request().method()==='POST');await customer.locator('#submit-local-acceptance').click();const response=await acceptanceResponse,body=await response.json();
  report.ui_commands.push({case_id:id,command:'record_local_acceptance',status:response.status(),request:response.request().postDataJSON(),headers:response.request().headers(),response:body});assert.equal(response.status(),200,JSON.stringify(body));await customer.getByText('Saved local acceptance receipt',{exact:false}).waitFor();
  d=await check(id,'record_local_acceptance','ready_to_book',beforeAcceptance);assert.equal(d.coordination.consent.authenticated,false);assert.equal(d.coordination.consent.mode,'local_preview_simulation');assert.equal(d.coordination.consent.offer_id,d.coordination.offer.offer_id);assert.equal(d.coordination.consent.terms_hash,d.coordination.offer.terms_hash);assert.equal(d.coordination.consent.evidence_event_ids.length,1);
  const acceptanceEvent=d.snapshot.events.find(e=>e.event_id===d.coordination.consent.evidence_event_ids[0]);assert.equal(acceptanceEvent.sender_id,'customer');assert.deepEqual(acceptanceEvent.recipient_ids,['operator']);assert.match(acceptanceEvent.text,new RegExp(d.coordination.offer.offer_id));assert.match(acceptanceEvent.text,new RegExp(d.coordination.offer.terms_hash));
  await screenshot(customer,'customer-acceptance-saved-mobile.png');
  d=await act(id,'request_booking','booking_pending');assert.equal(d.coordination.pending_request.status,'pending_local_readback');assert.equal(d.coordination.operation_receipts.length,1);const bookingRequest=d.coordination.pending_request;
  await screenshot(team,'team-booking-pending-desktop.png');
  await append(id,'booking-readback','dispatch',`Booking confirmed locally for request ${bookingRequest.request_id} and complete terms hash ${bookingRequest.terms_hash}. No real booking was made.`);
  d=await act(id,'confirm_booking','booking_confirmed',{evidence:'booking-readback'});assert.equal(d.coordination.operation_receipts.length,2);assert.equal(d.coordination.operation_receipts[1].request_id,bookingRequest.request_id);assert.equal(d.coordination.pending_request,null);
  await screenshot(team,'team-booking-confirmed-desktop.png');await customer.reload();await customer.getByRole('heading',{name:'Booking confirmed locally',exact:true}).waitFor();assert.match(await customer.locator('#customer-coordination').innerText(),/Physical delivery\s+Not confirmed/);await screenshot(customer,'customer-booking-confirmed-mobile.png');
  const sourcedId=await create('sourced');d=await setup(sourcedId);await append(sourcedId,'consent-source','customer',`I accept offer ${d.coordination.offer.offer_id} and complete terms hash ${d.coordination.offer.terms_hash}.`);
  d=await act(sourcedId,'record_consent','ready_to_book',{evidence:'consent-source'});assert.deepEqual(d.coordination.consent.evidence_event_ids,['consent-source']);
  d=await act(sourcedId,'escalate','escalated',{evidence:'consent-source',configure:async()=>team.fill('#coordination-reason','Synthetic E2E operator review required; stop before any external action.')});await screenshot(team,'team-escalated-desktop.png');
  assert.deepEqual(report.blocked_requests,[]);assert.deepEqual(report.browser_errors,[]);
  if(process.env.PROOFKEY_E2E_DATABASE_URL){
    const databaseURL=new URL(process.env.PROOFKEY_E2E_DATABASE_URL);assert.ok(['postgres:','postgresql:'].includes(databaseURL.protocol) && ['127.0.0.1','localhost','[::1]'].includes(databaseURL.hostname),'PostgreSQL verification must use loopback');
    const schema=process.env.PROOFKEY_E2E_DATABASE_SCHEMA || 'public';assert.match(schema,/^[A-Za-z_][A-Za-z0-9_]{0,62}$/);
    const query=`import json,sys,psycopg
from psycopg import sql
out=[]
with psycopg.connect(sys.argv[1],connect_timeout=10) as c:
 c.execute('SET TRANSACTION READ ONLY')
 c.execute(sql.SQL('SET LOCAL search_path TO {}, pg_catalog').format(sql.Identifier(sys.argv[2])))
 for case_id in json.loads(sys.argv[3]):
  records=[json.loads(r[0]) for r in c.execute('SELECT record FROM platform_coordination WHERE case_id=%s ORDER BY version',(case_id,))]
  head=c.execute('SELECT current_revision FROM case_heads WHERE case_id=%s',(case_id,)).fetchone()[0]
  snapshot=json.loads(c.execute('SELECT snapshot FROM case_snapshots WHERE case_id=%s AND revision=%s',(case_id,head)).fetchone()[0])
  links=c.execute('SELECT count(*) FROM platform_model_links WHERE case_id=%s',(case_id,)).fetchone()[0]
  out.append(dict(case_id=case_id,versions=[r['version'] for r in records],head=head,snapshot=snapshot,latest=records[-1],model_links=links))
print(json.dumps(out))`;
    const result=await promisify(execFile)(process.env.PROOFKEY_E2E_PYTHON || 'python3',['-c',query,process.env.PROOFKEY_E2E_DATABASE_URL,schema,JSON.stringify(report.case_ids)]);
    report.postgresql=JSON.parse(result.stdout);
    for(const row of report.postgresql){const current=await detail(row.case_id);assert.deepEqual(row.latest,current.coordination);assert.deepEqual(row.snapshot,current.snapshot);assert.deepEqual(row.versions,Array.from({length:row.latest.version},(_,i)=>i+1));assert.equal(row.model_links,0);assert.equal(row.head,current.snapshot.revision);}
  }
  report.counts={new_cases:report.case_ids.length-(report.resumed_test_case?1:0),resumed_cases:report.resumed_test_case?1:0,ui_commands:report.ui_commands.length,http_checks_and_seeds:report.http.length,screenshots:report.screenshots.length};report.status='passed';
}catch(error){report.status='failed';report.failure={message:error.message,stack:error.stack};process.exitCode=1;if(browser){for(const [i,page] of browser.contexts().flatMap(c=>c.pages()).entries()){await page.screenshot({path:path.join(output,`failure-${i}.png`),fullPage:true}).catch(()=>{});}}}finally{if(browser)await browser.close();await writeFile(path.join(output,'report.json'),JSON.stringify(report,null,2));console.log(JSON.stringify({status:report.status,output,case_ids:report.case_ids,counts:report.counts,failure:report.failure},null,2));}
