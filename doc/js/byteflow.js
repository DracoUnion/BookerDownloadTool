const fs = require('fs');
let src = fs.readFileSync('module1514.js', 'utf-8').trim();
src = src.replace(/^\d+:/, '');
if (src.endsWith(',')) src = src.slice(0, -1);
// Log x inputs fully
src = src.replace('x:function(ei,eo){', 'x:function(ei,eo){if(window.__BF){window.__BF.push({stage:"x-start",ei:ei,eiType:typeof ei,eoSample:Array.from(eo||[]).slice(0,4)});}');
src = src.replace('eo=__g.r(eh),ec=ec.concat(eo),ef++}return ec},',
  'eo=__g.r(eh);if(window.__BF){window.__BF.push({stage:"after-r",ehSample:Array.from(eh),eoOut:Array.from(eo)});}ec=ec.concat(eo),ef++}return ec},');
src = src.replace('return ec},r:function(ei){',
  'return ec},r:function(ei){if(window.__BF){window.__BF.push({stage:"r-enter",block:Array.from(ei)});}');
const m = { exports: {} };
global.window = global;
const requireFn = (id) => { if (id === 74185) return {_: (x) => typeof x}; throw new Error('missing '+id); };
const fn = new Function('module','exports','require','return (' + src + ')(module, exports, require);');
fn(m, m.exports, requireFn);
const ZP = m.exports.ZP;
window.__BF = null; ZP('warmup'); ZP('warmup2');
window.__BF = [];
const out = ZP('hello');
console.log('out:', out);
for (const b of window.__BF) console.log(JSON.stringify(b));
