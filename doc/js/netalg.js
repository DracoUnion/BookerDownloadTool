const fs = require('fs');
let src = fs.readFileSync('module1514.js', 'utf-8').trim();
src = src.replace(/^\d+:/, '');
if (src.endsWith(',')) src = src.slice(0, -1);
// We want to understand what _encrypt does. Patch the case 478 closure to log.
// The closure: this.C[3]=function(ei){var eo=new l;return eo.S=t,eo.S[0]=ei,eo.O(h.G,h.V,h.D),eo.C[3]}
// Patch: capture the result C[3] and initial input.
src = src.replace(
  'this.C[3]=function(ei){var eo=new l;return eo.S=t,eo.S[0]=ei,eo.O(h.G,h.V,h.D),eo.C[3]},',
  'this.C[3]=function(ei){if(window.__ENCIN){window.__ENCIN.push(ei);}var eo=new l;eo.S=t;eo.S[0]=ei;eo.O(h.G,h.V,h.D);if(window.__ENCOUT){window.__ENCOUT.push(eo.C[3]);}return eo.C[3]},'
);
const m = { exports: {} };
global.window = global;
const requireFn = (id) => { if (id === 74185) return {_: (x) => typeof x}; throw new Error('missing '+id); };
const fn = new Function('module','exports','require','return (' + src + ')(module, exports, require);');
fn(m, m.exports, requireFn);
const ZP = m.exports.ZP;
window.__ENCIN = window.__ENCOUT = null;
ZP('warmup1'); ZP('warmup2');
window.__ENCIN = []; window.__ENCOUT = [];
const out = ZP('hello');
console.log('ZP(hello)=', out);
console.log('ENCIN:', JSON.stringify(window.__ENCIN));
console.log('ENCOUT:', JSON.stringify(window.__ENCOUT));
