import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {spawn} from 'node:child_process';
import path from 'node:path';
import assert from 'node:assert/strict';
import {captureContract as contract,validateCapture,validateFrameFooter} from './showcase-capture-contract.mjs';

const directory=path.resolve(process.argv[2]);
const manifest=JSON.parse(await readFile(path.join(directory,'capture.json'),'utf8'));
const run=(command,args,binary=false)=>new Promise((resolve,reject)=>{const child=spawn(command,args,{stdio:['ignore','pipe','pipe']});const chunks=[];let err='';child.stdout.on('data',v=>chunks.push(v));child.stderr.on('data',v=>err+=v);child.on('error',reject);child.on('close',code=>code===0?resolve(binary?Buffer.concat(chunks):Buffer.concat(chunks).toString('utf8')):reject(new Error(`${command} exited ${code}: ${err.slice(-3000)}`)));});
const outputs=await Promise.all(manifest.receipts.filter(row=>row.raw_video).map(async record=>{
  validateCapture(record);
  const output=path.join(directory,`Right-onTime-${record.mode}-mobile-40s${record.presentation?'-clean':''}.mp4`);
  // Browser wall-clock starts before the first encoded frame. Anchor to the
  // recorded end, not that wall-clock origin; retain the full final receipt.
  const rawProbe=JSON.parse(await run('/opt/homebrew/bin/ffprobe',['-v','error','-show_entries','format=duration','-of','json',record.raw_video]));
  const rawDuration=Number(rawProbe.format.duration);assert(rawDuration>=contract.durationSeconds,'Raw capture must contain forty seconds');
  const start=rawDuration-contract.durationSeconds;
  await run('/opt/homebrew/bin/ffmpeg',['-hide_banner','-loglevel','error','-n','-ss',String(start),'-i',record.raw_video,'-t',String(contract.durationSeconds),'-an','-vf',`scale=${contract.outputSize.width}:${contract.outputSize.height}:flags=lanczos,fps=${contract.fps},tpad=stop_mode=clone:stop_duration=0.04,format=yuv420p`,'-c:v','libx264','-crf','18','-preset','fast','-threads','2','-movflags','+faststart',output]);
  const probe=JSON.parse(await run('/opt/homebrew/bin/ffprobe',['-v','error','-select_streams','v:0','-show_entries','stream=width,height,r_frame_rate,nb_frames:format=duration','-of','json',output]));
  const stream=probe.streams[0];assert.equal(stream.width,contract.outputSize.width);assert.equal(stream.height,contract.outputSize.height);assert.equal(stream.r_frame_rate,`${contract.fps}/1`);assert.equal(Number(stream.nb_frames),contract.frameCount);assert.equal(Number(probe.format.duration),contract.durationSeconds);
  await run('/opt/homebrew/bin/ffmpeg',['-hide_banner','-loglevel','error','-i',output,'-f','null','-']);
  const qa=path.join(directory,`${record.mode}-frames`);await mkdir(qa,{recursive:true});
  for(const second of contract.midpoints){
    const frame=path.join(qa,`second-${second}.png`);
    await run('/opt/homebrew/bin/ffmpeg',['-hide_banner','-loglevel','error','-n','-ss',String(second),'-i',output,'-frames:v','1',frame]);
    validateFrameFooter(await run('/opt/homebrew/bin/ffmpeg',['-hide_banner','-loglevel','error','-i',frame,'-vf','crop=iw:8:0:ih-8','-frames:v','1','-pix_fmt','rgb24','-f','rawvideo','pipe:1'],true));
  }
  return {mode:record.mode,path:output,sha256:createHash('sha256').update(await readFile(output)).digest('hex'),probe,full_decode:'passed',frame_footer_checks:'passed',edit:{raw_duration:rawDuration,start_seconds:start,end_anchored:true,maximum_final_frame_padding_seconds:0.04},qualification:record.qualification};
}));
await writeFile(path.join(directory,'exports.json'),JSON.stringify({assets:manifest.assets,outputs},null,2));
console.log(JSON.stringify(outputs,null,2));
