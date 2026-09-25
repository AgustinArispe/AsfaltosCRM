import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
const root = path.dirname(new URL(import.meta.url).pathname);
const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
const timing = JSON.parse(fs.readFileSync(path.join(root,'timing.json'),'utf8'));
const assert = (ok, reason) => { if (!ok) throw new Error(reason); };
assert(timing.duration === 30 && timing.fps === 30 && timing.frames === 900, 'Incorrect timing');
for (const [name, value] of Object.entries({'data-duration':30,'data-width':1920,'data-height':1080,'data-fps':30})) {
  assert(html.includes(`${name}="${value}"`), `Missing ${name}`);
}
const assets = [...new Set([...html.matchAll(/(?:src="|url\(')(assets\/[^"')]+)/g)].map(m=>m[1]))];
const images=[];
for (const asset of assets) {
  const bytes=fs.readFileSync(path.join(root,asset));
  assert(bytes.length>0,`Empty asset: ${asset}`);
  if(asset.endsWith('.png')) {
    assert(bytes.subarray(1,4).toString()==='PNG',`Invalid PNG: ${asset}`);
    images.push({asset,width:bytes.readUInt32BE(16),height:bytes.readUInt32BE(20),sha256:crypto.createHash('sha256').update(bytes).digest('hex')});
  }
}
assert(!/<audio|<video|https?:\/\//.test(html),'Unexpected audio/video/network reference');
assert(!html.includes('happy-beats'),'Unapproved music');
assert(!/data-theme="dark"/.test(html),'Dark theme');
assert(html.includes('window.__timelines[\'pulse-crm\']=tl'),'Missing registered timeline');
const result={ok:true,duration:30,fps:30,frames:900,resolution:[1920,1080],theme:'light',audio:'none',localAssets:assets.length,images};
fs.writeFileSync(path.join(root,'../review/asset-verification.json'),JSON.stringify(result,null,2)+'\n');
console.log(JSON.stringify({ok:true,duration:30,fps:30,frames:900,localAssets:assets.length,pngs:images.length}));
