import assert from 'node:assert/strict';

const sceneIds=Object.freeze(['request','review','change','consent','confirmed']);
const sceneSeconds=8;
const fps=30;
export const captureContract=Object.freeze({
  sceneIds,sceneSeconds,fps,
  durationSeconds:sceneIds.length*sceneSeconds,
  frameCount:sceneIds.length*sceneSeconds*fps,
  viewport:Object.freeze({width:450,height:800}),
  videoSize:Object.freeze({width:900,height:1600}),
  outputSize:Object.freeze({width:1080,height:1920}),
  midpoints:Object.freeze(sceneIds.map((_,index)=>(index+.5)*sceneSeconds)),
});

export function validateCapture(record) {
  assert.equal(record.duration_seconds,captureContract.durationSeconds,'Capture duration must match the five-scene contract');
  assert.deepEqual(record.writes,[],'Playback must not mutate cases');
  assert.deepEqual(record.errors,[],'Playback must not contain browser errors');
  assert.deepEqual(record.viewport,captureContract.viewport,'Unexpected logical mobile viewport');
  assert.deepEqual(record.video_size,captureContract.videoSize,'Unexpected recorded resolution');
  assert.deepEqual(record.browser_viewport,captureContract.videoSize,'Recorded viewport must fill the video canvas');
  assert.equal(record.device_scale_factor,1,'Video uses physical viewport scaling, not device-pixel-ratio scaling');
  assert.equal(record.display_scale,2,'Capture requires a two-times logical mobile canvas');
  assert(Number.isFinite(record.capture_start_seconds)&&record.capture_start_seconds>=0,'Missing finite capture origin');
  assert(Array.isArray(record.marks)&&record.marks.length===captureContract.sceneIds.length,'All five scene marks are required');
  record.marks.forEach((mark,index)=>{
    assert.equal(mark.scene,captureContract.sceneIds[index],'Scenes must retain source order');
    assert(Number.isFinite(mark.at),'Scene mark must have a finite timestamp');
    const expected=record.capture_start_seconds+index*captureContract.sceneSeconds;
    assert(Math.abs(mark.at-expected)<=0.3,'Scene onset exceeds 300ms browser scheduling tolerance');
  });
}

export function validateFrameFooter(rgb) {
  assert(rgb?.length>0&&rgb.length%3===0,'Footer pixel data is required');
  let min=255,max=0;
  for(const value of rgb){min=Math.min(min,value);max=Math.max(max,value);}
  // The designed footer is a varying warm paper backdrop. Chromium video
  // padding is flat neutral gray and means the recorded image was cropped.
  assert(!(min>=110&&max<=140&&max-min<=4),'Encoder gray padding cropped the phone footer');
}
