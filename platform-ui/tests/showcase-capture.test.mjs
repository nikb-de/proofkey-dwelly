import test from 'node:test';
import assert from 'node:assert/strict';
import {captureContract, validateCapture, validateFrameFooter} from '../../docs/demos/2026-10-10-case-001-terms/showcase-capture-contract.mjs';

const validRecord=()=>({duration_seconds:40,writes:[],errors:[],capture_start_seconds:1.2,
  viewport:{width:450,height:800},browser_viewport:{width:900,height:1600},video_size:{width:900,height:1600},device_scale_factor:1,display_scale:2,
  marks:captureContract.sceneIds.map((scene,index)=>({scene,at:1.2+index*8})),
});

test('mobile film is exactly five eight-second scenes at 30 fps', () => {
  assert.equal(captureContract.sceneIds.length, 5);
  assert.equal(captureContract.sceneSeconds, 8);
  assert.equal(captureContract.durationSeconds, 40);
  assert.equal(captureContract.durationSeconds, captureContract.sceneIds.length * captureContract.sceneSeconds);
  assert.equal(captureContract.frameCount, 1200);
  assert.deepEqual(captureContract.midpoints, [4,12,20,28,36]);
});

test('export rejects changed timing, writes and browser failures', () => {
  const record=validRecord();
  assert.doesNotThrow(()=>validateCapture(record));
  for(const invalid of [{...record,duration_seconds:50},{...record,writes:['POST']},{...record,errors:['failed']}]) {
    assert.throws(()=>validateCapture(invalid));
  }
});

test('export requires all five ordered eight-second beats and capture geometry',()=>{
  for(const overrides of [
    {marks:[{scene:'confirmed',at:1.2}]},
    {marks:captureContract.sceneIds.map((scene,index)=>({scene,at:1.2+index*2}))},
    {marks:captureContract.sceneIds.toReversed().map((scene,index)=>({scene,at:1.2+index*8}))},
    {marks:captureContract.sceneIds.map((scene,index)=>({scene,at:Number.NaN}))},
    {capture_start_seconds:Number.NaN},
    {viewport:{width:1,height:1}},
    {video_size:{width:1,height:1}},
    {device_scale_factor:2},
    {display_scale:1},
    {browser_viewport:{width:450,height:800}},
  ])assert.throws(()=>validateCapture({...validRecord(),...overrides}));
  const record=validRecord();
  record.marks[2].at+=.1;
  assert.doesNotThrow(()=>validateCapture(record),'small browser scheduling jitter is permitted');
});

test('export refuses encoder gray padding that cuts off the phone footer',()=>{
  assert.throws(()=>validateFrameFooter(Buffer.alloc(1080*8*3,126)),/padding/);
  assert.doesNotThrow(()=>validateFrameFooter(Buffer.from([231,230,219,211,217,207,223,225,215])));
  assert.throws(()=>validateFrameFooter(Buffer.alloc(0)),/pixel/);
});
