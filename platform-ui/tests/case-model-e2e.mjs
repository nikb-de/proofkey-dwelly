// Real platform HTTP + PostgreSQL + worker. Only external model transport is SIMULATED.
import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {mkdtemp, readFile, writeFile} from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import readline from 'node:readline';
import {once} from 'node:events';
const {chromium} = await import(process.env.PROOFKEY_PLAYWRIGHT_MODULE || '/Users/nbk/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright/index.mjs');
const output = process.env.PROOFKEY_QA_DIR || await mkdtemp(path.join(os.tmpdir(), 'proofkey-case-model-e2e-'));
const python = process.env.PROOFKEY_TEST_PYTHON || '/tmp/proofkey-postgres-tests-20261010/bin/python';
const server = spawn(python, ['-m', 'tools.dwelly_e2e.tests.fixture_server', '--output-dir', output,
  '--run-id', 'integration', '--run-id', 'ui', '--unknown-run-id', 'unknown'], {env: process.env, stdio: ['ignore', 'pipe', 'pipe']});
let stderr = ''; server.stderr.on('data', chunk => { stderr += chunk; });
const lines = readline.createInterface({input: server.stdout});
const errors = [], posts = [], checks = [];
let ready, browser, result, failure, readyTimer;
try {
  ready = await Promise.race([once(lines, 'line').then(([line]) => JSON.parse(line)),
    once(server, 'exit').then(([code]) => { throw Error(`Fixture exited ${code}: ${stderr}`); }),
    new Promise((_, reject) => { readyTimer = setTimeout(() => reject(Error('Fixture readiness timeout')), 15000); })]);
  clearTimeout(readyTimer);
  assert.equal(ready.mode, 'simulated');
  browser = await chromium.launch({headless: true, executablePath: process.env.PROOFKEY_CHROME_PATH || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'});
  // The CLI is external to the SUT. It uses only the same public HTTP routes as the UI.
  const runner = spawn(python, ['-m', 'tools.dwelly_e2e', 'run', '--base-url', ready.origin,
    '--mode', 'simulated', '--profile', 'simulated-case-fixture', '--run-id', 'integration',
    '--output', path.join(output, 'runner')], {env: process.env, stdio: ['ignore', 'pipe', 'pipe']});
  let runnerOutput = ''; runner.stdout.on('data', c => { runnerOutput += c; });
  runner.stderr.on('data', c => { runnerOutput += c; });
  const [runnerCode] = await once(runner, 'exit');
  assert.equal(runnerCode, 0, runnerOutput);
  result = JSON.parse(await readFile(path.join(output, 'runner/report.json'), 'utf8'));
  assert.equal(result.records.length, 16);
  assert.equal(result.summary.record_count, 16);
  const expectedCutoffs = [
    ...Array.from({length: 6}, (_, index) => `case-002:${index}`),
    ...Array.from({length: 8}, (_, index) => `case-002-n4:${index}`),
    'minimal:0', 'minimal:1'
  ];
  assert.deepEqual(result.records.map(record => `${record.plan.source.source_id}:${record.plan.source.step_index}`).sort(), expectedCutoffs.sort());
  assert.ok(result.records.every(record => record.status === 'succeeded' && record.job.transaction.dispatch_attempts === 1));
  checks.push('16 authored cutoffs via external CLI and real HTTP');

  const plans = JSON.parse(await readFile(path.join(output, 'plans.json'), 'utf8'));
  const plan = plans.find(p => p.case_id === 'e2e-ui-case-002-s3');
  const unknown = plans.find(p => p.case_id === 'e2e-unknown-case-002-s3');
  assert.ok(plan && unknown);
  async function post(route, data, key) {
    const response = await fetch(ready.origin + '/api/platform' + route, {method: 'POST',
      headers: {'Content-Type': 'application/json', 'X-ProofKey-Request': 'platform-v1', 'Idempotency-Key': key},
      body: JSON.stringify(data)});
    const body = await response.json(); assert.ok(response.ok, JSON.stringify(body)); return body;
  }
  async function seed(p) {
    await post('/cases', p.declaration, 'browser-create-' + p.case_id);
    for (const [index, event] of p.events.entries()) await post('/cases/' + p.case_id + '/events',
      {expected_revision: index, event}, 'browser-event-' + p.case_id + '-' + index);
  }
  await seed(plan); await seed(unknown);
  const page = await browser.newPage({viewport: {width: 1512, height: 1080}});
  page.on('pageerror', error => errors.push(error.message));
  page.on('request', request => { if (request.method() === 'POST' && request.url().includes('/model-runs')) posts.push(request.url()); });
  await page.goto(ready.origin + '/#case=' + plan.case_id);
  await page.locator(`#case-detail[data-case-id="${plan.case_id}"]`).waitFor();
  await page.locator('.model-options > summary').click();
  await page.selectOption('#model-profile', 'simulated-case-fixture');
  const submitted = page.waitForResponse(response => response.request().method() === 'POST' && response.url().endsWith('/model-runs'));
  await page.locator('#run-model').click();
  const firstJob = await (await submitted).json();
  const card = page.locator(`.job-item[data-job-id="${firstJob.run_id}"]`);
  await card.waitFor();
  await card.locator('.model-transport').filter({hasText: /Queued|Running|Response received/}).waitFor();
  await card.getByText('Full model run and receipt', {exact: true}).click();
  await card.locator('.model-coordination').filter({hasText: 'Coordination: Waiting'}).waitFor();
  assert.equal(await card.getByText('Full model run and receipt', {exact: true}).evaluate(element => element.parentElement.open), true);
  assert.match(await card.locator('.model-waiting').innerText(), /recipient/);
  assert.match(await card.locator('.model-action').innerText(), /Wait.*recipient/);
  assert.match(await card.locator('.model-counters').innerText(), /Dispatch attempts: 1.*Automatic retries: 0.*Operational effects: 0/);
  assert.match(await card.locator('.model-binding').innerText(), /Current evidence/);
  checks.push('UI observes queued/running → waiting with actor and one dispatch; inspector stays open');
  await page.reload();
  await page.locator(`#case-detail[data-case-id="${plan.case_id}"]`).waitFor();
  await page.locator('.model-options > summary').click();
  await card.locator('.model-coordination').filter({hasText: 'Coordination: Waiting'}).waitFor();
  assert.equal(posts.length, 1);
  checks.push('reload preserves job and never resubmits');
  await page.getByRole('tab',{name:/Sources/}).click();
  await page.fill('#evidence-text', 'SYNTHETIC E2E PROBE: later evidence invalidates the previous analysis.');
  const appended = page.waitForResponse(response => response.request().method() === 'POST' && response.url().endsWith('/events'));
  await page.locator('#evidence-form button').click();
  assert.ok((await appended).ok());
  await page.getByRole('tab',{name:/Summary/}).click();
  await card.locator('.model-binding').filter({hasText: /Stale/}).waitFor();
  assert.match(await card.locator('.model-coordination').innerText(), /Not available for the current evidence/);
  assert.equal(posts.length, 1);
  checks.push('new evidence marks old inference stale, not current');
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({path: path.join(output, 'desktop-stale.png'), fullPage: true});

  // Exercise actual workspace selection; changing only a URL fragment does not
  // reload the document and is not the application's case-selection control.
  await page.locator(`#case-list [data-case-id="${unknown.case_id}"]`).click();
  await page.locator(`#case-detail[data-case-id="${unknown.case_id}"]`).waitFor();
  if (!await page.locator('.model-options').evaluate(element => element.open)) await page.locator('.model-options > summary').click();
  await page.selectOption('#model-profile', 'simulated-case-fixture');
  const unknownSubmitted = page.waitForResponse(response => response.request().method() === 'POST' && response.url().endsWith('/model-runs'));
  await page.locator('#run-model').click();
  const unknownJob = await (await unknownSubmitted).json();
  const unknownCard = page.locator(`.job-item[data-job-id="${unknownJob.run_id}"]`);
  await unknownCard.locator('.model-transport').filter({hasText: /Outcome unknown/}).waitFor();
  assert.match(await unknownCard.locator('.model-coordination').innerText(), /Not available/);
  assert.match(await unknownCard.locator('.model-counters').innerText(), /Automatic retries: 0/);
  await page.reload(); await page.locator(`#case-detail[data-case-id="${unknown.case_id}"]`).waitFor();
  await page.locator('.model-options > summary').click();
  await unknownCard.locator('.model-transport').filter({hasText: /Outcome unknown/}).waitFor();
  assert.equal(posts.length, 2);
  checks.push('uncertain provider outcome remains unknown across reload; no retry');
  const detail = (await (await fetch(ready.origin + '/api/platform/cases/' + unknown.case_id)).json()).case;
  assert.equal(detail.external_effects, 0); assert.deepEqual(detail.actions, []); assert.deepEqual(detail.decisions, []);
  assert.notEqual(detail.states.lifecycle, 'resolved');
  const mobile = await browser.newPage({viewport: {width: 390, height: 844}});
  mobile.on('pageerror', error => errors.push(error.message));
  await mobile.goto(ready.origin + '/#case=' + unknown.case_id);
  await mobile.locator(`#case-detail[data-case-id="${unknown.case_id}"]`).waitFor();
  await mobile.locator('.model-options > summary').click();
  await mobile.evaluate(() => document.fonts.ready);
  assert.equal(await mobile.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
  await mobile.screenshot({path: path.join(output, 'mobile-unknown.png'), fullPage: true});
  assert.deepEqual(errors, []);
  checks.push('zero business effects, no browser exceptions, no mobile overflow');
} catch (error) {
  failure = error;
} finally {
  clearTimeout(readyTimer);
  if (browser) {
    try { await browser.close(); }
    catch (error) { failure ??= error; }
  }
  if (server.exitCode === null && server.signalCode === null) {
    const stopped = once(server, 'exit'); server.kill('SIGTERM'); await stopped;
  }
  lines.close();
  await writeFile(path.join(output, 'fixture-stderr.txt'), stderr);
}
let database;
try { database = JSON.parse(await readFile(path.join(output, 'database-report.json'), 'utf8')); }
catch { database = {schema_dropped: false, calls: [], cases: []}; }
if (!failure) assert.equal(database.schema_dropped, true);
if (!failure) {
  assert.equal(database.calls.length, 18);
  assert.equal(new Set(database.calls.map(call => call.case_id)).size, 18);
  assert.equal(database.cases.length, 18);
  for (const item of database.cases) {
    assert.equal(item.model_jobs.length, 1);
    assert.equal(item.model_jobs[0].transaction.dispatch_attempts, 1);
    assert.equal(item.model_jobs[0].transaction.automatic_retries, 0);
    assert.equal(item.external_effects, 0);
    assert.deepEqual(item.actions, []);
    assert.deepEqual(item.decisions, []);
  }
}
const report = {status: failure ? 'failed' : 'passed', mode: 'simulated',
  qualification: 'fixture_only_not_live_evidence', liveProviderCalls: 0, checks,
  scriptedDispatches: database.calls.length, schemaDropped: database.schema_dropped,
  browserErrors: errors, failure: failure?.message ?? null, runner: result, output};
await writeFile(path.join(output, 'browser-report.json'), JSON.stringify(report, null, 2));
console.log(JSON.stringify({status: report.status, output, checks, scriptedDispatches: report.scriptedDispatches, liveProviderCalls: 0}));
if (failure) throw failure;
