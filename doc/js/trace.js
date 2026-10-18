const fs = require('fs');
let src = fs.readFileSync('module1514.js', 'utf-8').trim();
src = src.replace(/^\d+:/, '');
if (src.endsWith(',')) src = src.slice(0, -1);
// Instrument __g.x and __g.r to log args and results
src = src.replace('x:function(ei,eo){', 'x:function(ei,eo){if(typeof window!="undefined"&&window.__TRACE){window.__TRACE.push({op:"x",in:Array.from(ei),key:Array.from(eo)});}');
src = src.replace('r:function(ei){', 'r:function(ei){if(typeof window!="undefined"&&window.__TRACE){window.__TRACE.push({op:"r",in:Array.from(ei)});}');
const m = { exports: {} };
global.window = global;
const requireFn = (id) => { if (id === 74185) return {_: (x) => typeof x}; throw new Error('missing '+id); };
const fn = new Function('module','exports','require','return (' + src + ')(module, exports, require);');
fn(m, m.exports, requireFn);
const ZP = m.exports.ZP;

// Run once to build tables (without trace)
window.__TRACE = null;
// Now trace ZP on a simple input
window.__TRACE = [];
const out = ZP('hello');
console.log('ZP(hello) =', out);
const trace = window.__TRACE;
console.log('trace entries:', trace.length);
// show x calls (first 20) and r calls count
const xcalls = trace.filter(t=>t.op==='x');
const rcalls = trace.filter(t=>t.op==='r');
console.log('x calls:', xcalls.length, 'r calls:', rcalls.length);
console.log('--- first x call ---');
console.log(JSON.stringify(xcalls[0]));
console.log('--- last few x calls ---');
for (const c of xcalls.slice(-5)) console.log('x in len', c.in.length, 'key', JSON.stringify(c.key.slice(0,8)));
// Show the r calls' inputs (first 5)
for (const c of rcalls.slice(0,5)) console.log('r in', JSON.stringify(c.in));
