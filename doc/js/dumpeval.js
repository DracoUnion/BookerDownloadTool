const fs = require('fs');
let src = fs.readFileSync('module1514.js', 'utf-8').trim();
src = src.replace(/^\d+:/, '');
if (src.endsWith(',')) src = src.slice(0, -1);
// instrument eval cases to log the string
src = src.replace('case 254:this.C[this.c]=eval(i)',
  'case 254:if(typeof window!="undefined"&&window.__EV){window.__EV.push(["254",i]);}this.C[this.c]=eval(i)');
src = src.replace('case 283:this.C[this.c]=eval(String.fromCharCode(this.C[this.I]))',
  'case 283:if(typeof window!="undefined"&&window.__EV){window.__EV.push(["283",String.fromCharCode(this.C[this.I])]);}this.C[this.c]=eval(String.fromCharCode(this.C[this.I]))');
src = src.replace('case 486:this.C[this.e>>16&7]=eval(M.join())',
  'case 486:if(typeof window!="undefined"&&window.__EV){window.__EV.push(["486",M.join()]);}this.C[this.e>>16&7]=eval(M.join())');
const m = { exports: {} };
global.window = global;
const requireFn = (id) => { if (id === 74185) return {_: (x) => typeof x}; throw new Error('missing '+id); };
const fn = new Function('module','exports','require','return (' + src + ')(module, exports, require);');
fn(m, m.exports, requireFn);
const ZP = m.exports.ZP;
window.__EV = null;
ZP('warmup1'); ZP('warmup2');
window.__EV = [];
const out = ZP('hello');
console.log('ZP(hello)=', out);
console.log('eval count:', window.__EV.length);
const seen = new Set();
for (const [caseNo, str] of window.__EV) {
  if (!seen.has(caseNo+':'+str)) { seen.add(caseNo+':'+str); console.log('case', caseNo, 'eval:', JSON.stringify(str).slice(0, 200)); }
}
