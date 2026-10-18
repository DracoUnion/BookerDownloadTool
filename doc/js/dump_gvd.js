const fs = require('fs');
let src = fs.readFileSync('module1514.js', 'utf-8').trim();
src = src.replace(/^\d+:/, '');
if (src.endsWith(',')) src = src.slice(0, -1);
src = src.replace('};l.prototype.O=', '};if(typeof window!="undefined"){window.__gDump=__g;window.__hDump=h;}l.prototype.O=');
const m = { exports: {} };
global.window = global;
const requireFn = (id) => { if (id === 74185) return {_: typeof Symbol === 'function' ? (x)=>typeof x : (x)=>(x && typeof x==='object')?typeof x:typeof x}; throw new Error('missing '+id); };
const fn = new Function('module','exports','require','return (' + src + ')(module, exports, require);');
fn(m, m.exports, requireFn);
const h = global.__hDump;
console.log('h keys:', Object.keys(h));
console.log('h.G type:', typeof (global.__hDump && global.__hDump.G));
if (h && h.G) {
  console.log('h.G length:', h.G.length);
  console.log('h.G sample:', JSON.stringify(h.G.slice(0, 40)));
}
if (h) {
  for (const k of ['V','D','S','d','a']) {
    if (h[k] !== undefined) {
      const v = h[k];
      console.log('h.' + k, 'type', typeof v, Array.isArray(v) ? 'len ' + v.length + ' sample ' + JSON.stringify(v.slice(0,5)) : (typeof v === 'object' && v) ? 'keys ' + Object.keys(v).slice(0,5) : String(v).slice(0,100));
    }
  }
}
// Also dump the closure's t via _encrypt
