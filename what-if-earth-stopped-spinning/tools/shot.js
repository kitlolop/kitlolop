// usage: node tools/shot.js out_dir t1 t2 ...   (single sub-frame stills for checking)
const {chromium}=require('playwright'); const path=require('path');
(async()=>{const [out,...ts]=process.argv.slice(2);
 const b=await chromium.launch({args:['--use-angle=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist']});
 const p=await b.newPage({viewport:{width:1920,height:1080}}); const errs=[]; p.on('pageerror',e=>errs.push(String(e))); p.on('console',m=>{if(m.type()==='error')errs.push(m.text())});
 await p.goto('file://'+path.resolve('index.html')+'?render'); await p.waitForFunction('window.READY',null,{timeout:120000}).catch(()=>{});
 if(errs.length){console.log(errs.join('\n'));}
 for(const t of ts){const s=Date.now(); await p.evaluate(t=>renderFrame(+t),t); const e=Date.now(); await p.locator('#c').screenshot({path:`${out}/t${(+t).toFixed(2).padStart(6,'0')}.png`}); console.log(t,'render',e-s,'ms shot',Date.now()-e,'ms');}
 await b.close();})();
