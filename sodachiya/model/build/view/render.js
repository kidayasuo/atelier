const {chromium}=require('playwright-core');const http=require('http');const fs=require('fs');const path=require('path');
const views=JSON.parse(fs.readFileSync(process.argv[2]));
const root=__dirname;
const srv=http.createServer((q,s)=>{const u=decodeURIComponent(q.url.split('?')[0]);const f=path.join(root,u);
  if(!fs.existsSync(f)){s.writeHead(404);s.end();return;}
  const t=f.endsWith('.js')?'text/javascript':f.endsWith('.html')?'text/html':'application/octet-stream';s.writeHead(200,{'Content-Type':t});fs.createReadStream(f).pipe(s);}).listen(8765);
(async()=>{const b=await chromium.launch({executablePath:(()=>{const fs=require('fs');const d='/opt/pw-browsers';const h=fs.readdirSync(d).filter(n=>n.startsWith('chromium_headless_shell-')).sort().pop();for(const x of ['/chrome-linux/headless_shell','/chrome-headless-shell-linux64/chrome-headless-shell']){if(fs.existsSync(d+'/'+h+x))return d+'/'+h+x;}return d+'/'+h+'/chrome-linux/headless_shell'})(),args:['--use-gl=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist']});
 const p=await b.newPage({viewport:{width:1600,height:1000}});
 for(const v of views){const qs=new URLSearchParams({glb:v.glb,eye:JSON.stringify(v.eye),tgt:JSON.stringify(v.tgt),fov:v.fov||40,hide:v.hide||'',w:v.w||1600,h:v.h||1000,...(v.ortho?{ortho:v.ortho}:{}),...(v.clipz?{clipz:v.clipz}:{})});
  await p.setViewportSize({width:v.w||1600,height:v.h||1000});
  await p.goto('http://localhost:8765/page.html?'+qs);await p.waitForFunction(()=>document.title==='done',null,{timeout:180000});
  await p.screenshot({path:v.out});console.log('shot',v.out);}
 await b.close();srv.close();})();
