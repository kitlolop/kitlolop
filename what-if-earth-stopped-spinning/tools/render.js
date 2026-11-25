// Render frames [a,b) at 60 fps (each = 2 blended sub-frames, shutter 0.6) -> near-lossless chunk
const {chromium}=require('playwright'); const path=require('path'); const {spawn}=require('child_process');
(async()=>{const [a,b,out]=[+process.argv[2],+process.argv[3],process.argv[4]];
 const ff=spawn('ffmpeg',['-y','-v','error','-f','image2pipe','-framerate','60','-c:v','png','-i','-','-c:v','libx264','-preset','veryfast','-crf','6','-pix_fmt','yuv444p',out],{stdio:['pipe','inherit','inherit']});
 const br=await chromium.launch({args:['--use-angle=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist']});
 const p=await br.newPage({viewport:{width:1920,height:1080}}); p.on('pageerror',e=>console.error('ERR',e));
 await p.goto('file://'+path.resolve('index.html')+'?render'); await p.waitForFunction('window.READY',null,{timeout:120000});
 const el=p.locator('#c'); const t0=Date.now();
 for(let f=a;f<b;f++){ await p.evaluate(t=>renderFrame(t),f/60); const buf=await el.screenshot({type:'png'});
   if(!ff.stdin.write(buf)) await new Promise(r=>ff.stdin.once('drain',r));
   if((f-a)%60===0) console.log(`[${a}-${b}] frame ${f} ${((Date.now()-t0)/1000/(f-a+1)).toFixed(2)}s/frame`); }
 ff.stdin.end(); await new Promise(r=>ff.on('close',r)); await br.close(); console.log(`[${a}-${b}] done`);})();
