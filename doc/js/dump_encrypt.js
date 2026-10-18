const fs = require('fs');
// Load module 1514 with a patch that exposes __g after VM builds it
let src = fs.readFileSync('module1514.js', 'utf-8').trim();
src = src.replace(/^\d+:/, '');
if (src.endsWith(',')) src = src.slice(0, -1);
// patch: after var __g={x:...,r:...}; add exposure. Find "};l.prototype.O=" and insert before it
src = src.replace('};l.prototype.O=', '};if(typeof window!="undefined"){window.__gDump=__g;}l.prototype.O=');

const m = { exports: {} };
global.window = global;
const requireFn = (id) => { if (id === 74185) return {_: typeof Symbol === 'function' ? (x)=>typeof x : (x)=>(x && typeof x==='object' && x.constructor===Symbol && x!==Symbol.prototype ? 'symbol' : typeof x)}; throw new Error('missing '+id); };
const fn = new Function('module','exports','require','return (' + src + ')(module, exports, require);');
try { fn(m, m.exports, requireFn); } catch(e) { console.log('load err', e.message); }

const g = global.__gDump;
if (g) {
  console.log('__g keys:', Object.keys(g));
  if (g._encrypt) {
    console.log('--- _encrypt.toString() ---');
    console.log(g._encrypt.toString());
  }
  if (g.decrypt) console.log('--- decrypt ---\n' + g.decrypt.toString());
} else {
  console.log('__gDump missing');
}
