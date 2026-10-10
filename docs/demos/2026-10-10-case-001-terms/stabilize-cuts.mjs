// Trim navigation/scroll transients from recorded spans. Never modifies sources.
import assert from 'node:assert/strict';
import {readFile,writeFile} from 'node:fs/promises';
import path from 'node:path';
const dir=path.resolve(process.argv[2]);
const source=JSON.parse(await readFile(path.join(dir,'assembly-final.json'),'utf8'));
const result=structuredClone(source);
for(const segment of result.segments)for(const clip of segment.clips){
  assert.ok(clip.end-clip.start>1.5);
  clip.start=Number((clip.start+0.6).toFixed(6));
  clip.end=Number((clip.end-0.2).toFixed(6));
}
result.output=source.output.replace('-50s-final.mp4','-50s-stable.mp4');
assert.notEqual(result.output,source.output);
await writeFile(path.join(dir,'assembly-stable.json'),JSON.stringify(result,null,2),{flag:'wx'});
console.log(path.join(dir,'assembly-stable.json'));
