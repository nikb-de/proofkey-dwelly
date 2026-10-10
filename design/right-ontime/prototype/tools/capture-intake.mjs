import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {createRequire} from 'node:module';
const require=createRequire(process.env.PLAYWRIGHT_PACKAGE_JSON||import.meta.url);
const {chromium}=require('playwright');
const output=process.env.INTAKE_SCREENSHOT_DIR||path.resolve(import.meta.dirname,'../../../../outputs/right-ontime-intake-2026-10-10');
await fs.mkdir(output,{recursive:true});
const browser=await chromium.launch({headless:true,...(process.env.CHROMIUM_EXECUTABLE_PATH?{executablePath:process.env.CHROMIUM_EXECUTABLE_PATH}:{})});
try{
 for(const [name,width,height] of [['desktop',1440,1050],['mobile-360',360,800]]){
  const context=await browser.newContext({viewport:{width,height}});
  const page=await context.newPage();await page.route(/^https?:/,r=>r.abort());
  await page.goto(pathToFileURL(path.resolve(import.meta.dirname,'../intake.html')).href);
  await page.waitForFunction(()=>window.ProofKeyIntake);
  await page.evaluate(async()=>{
   const api=window.ProofKeyIntake;
   await api.store.create({case_id:'delivery-184',links:{order_id:'order-184',customer_id:'customer',operator_id:'operator'},participants:['customer','operator','courier'],language:'en'},'Parcel condition — order 184');
   const canvas=document.createElement('canvas');canvas.width=480;canvas.height=220;
   const c=canvas.getContext('2d');c.fillStyle='#F3EBDD';c.fillRect(0,0,480,220);c.fillStyle='#BEA36A';c.fillRect(135,40,210,145);c.fillStyle='#1D3E23';c.font='18px sans-serif';c.fillText('Local sample attachment',130,210);
   const blob=await new Promise(resolve=>canvas.toBlob(resolve));
   const asset=await api.prepareFile(new File([blob],'parcel-sample.png',{type:'image/png'}));
   await api.store.append('delivery-184',0,[{event_id:'evidence-1',occurred_at:'2026-10-09T08:30:00Z',channel:'chat',sender_id:'customer',recipient_ids:['operator','courier'],kind:'photo',text:'Customer supplied a parcel photo. Review the evidence before proposing any action.',media:asset.media}],[asset]);
  });
  await page.goto(pathToFileURL(path.resolve(import.meta.dirname,'../intake.html')).href+'?case=delivery-184');
  await page.waitForSelector('#history img');await page.evaluate(()=>document.fonts.ready);
  await page.screenshot({path:path.join(output,`${name}.png`),fullPage:true});await context.close();
 }
 console.log(`Screenshots: ${output}`);
}finally{await browser.close();}
