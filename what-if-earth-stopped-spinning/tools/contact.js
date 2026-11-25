// Contact sheet: one motion-blurred frame per beat -> build/contact/*.png (+ beats.json)
const {chromium}=require('playwright'); const path=require('path'); const fs=require('fs');
const BEATS=[['open 2.25x','0.6'],['"stopped" swell+flash','T.stopped+0.12'],['shockwave','T.stopped+0.45'],['pull-out to 1x','T.planet+1.2'],
['"wouldn\'t": air keeps going','T.wouldnt+0.45'],['"Right now" rewind','T.right+0.4'],['equator line','T.equator+1.0'],['"sixteen" counter slam','T.sixteen+0.12'],
['push-in streams','T.stand+0.8'],['"you" sign drop','T.you+0.25'],['"play" morph','T.play+0.7'],['"nothing" shrug','T.nothing+0.45'],
['single pull-out','T.earth5+1.4'],['orbit view rings','T.year5+0.5'],['"brakes" stop','T.brakes+0.15'],['"air" wind front','T.air+0.35'],
['"tornado" bars','T.tornado+1.2'],['"waves" tsunami','T.waves+0.2'],['"poles" drain','T.poles+1.7'],['"year" day counter','T.year10+0.3'],
['"daylight"','T.daylight+0.3'],['"night" lights flash','T.night+0.4'],['"sunglasses" drop','T.sunglasses+0.35'],['"mask" drop','T.mask+0.4'],
['"Relax" rewind','T.relax+0.4'],['"milliseconds" counter','T.ms+0.5'],['"By" callback sign','T.by+0.8'],['"kilometers" gold','T.km+0.3'],
['title','T.title+1.2'],['last frame','59.98']];
(async()=>{const out=process.argv[2]; fs.mkdirSync(out,{recursive:true});
 const b=await chromium.launch({args:['--use-angle=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist']});
 const p=await b.newPage({viewport:{width:1920,height:1080}}); const errs=[]; p.on('pageerror',e=>errs.push(String(e)));
 await p.goto('file://'+path.resolve('index.html')+'?render'); await p.waitForFunction('window.READY',null,{timeout:120000});
 const meta=[];
 for(const [i,[name,expr]] of BEATS.entries()){ const t=await p.evaluate(e=>{const t=eval(e);renderFrame(t);return t;},expr);
   const f=`${out}/b${String(i).padStart(2,'0')}.png`; await p.locator('#c').screenshot({path:f}); meta.push({i,name,t,f}); }
 fs.writeFileSync(`${out}/beats.json`,JSON.stringify(meta,null,1)); if(errs.length) console.log('ERRORS',errs); await b.close();})();
