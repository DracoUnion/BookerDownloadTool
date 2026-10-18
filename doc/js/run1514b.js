const fs = require('fs');
function loadModule(file, requireFn) {
  let src = fs.readFileSync(file, 'utf-8').trim();
  src = src.replace(/^\d+:/, '');
  if (src.endsWith(',')) src = src.slice(0, -1);
  const m = { exports: {} };
  const callable = new Function('module','exports','require','return (' + src + ')(module, exports, require);');
  callable(m, m.exports, requireFn);
  return m.exports;
}
const m74185 = loadModule('module_74185.js', () => {});
global.window = global;
const requireFn = (id) => { if (id === 74185) return m74185; throw new Error('missing ' + id); };
const exports1514 = loadModule('module1514.js', requireFn);
const zse = global.__ZH__.zse;
console.log('zse keys:', Object.keys(zse));
for (const k of Object.keys(zse)) {
  const v = zse[k];
  console.log('--- zse.' + k + ' ---');
  console.log('type:', typeof v, 'len:', v ? (v.length || v.size) : 0);
  if (Array.isArray(v)) {
    console.log('first 16:', JSON.stringify(v.slice(0,16)));
  } else if (v && typeof v === 'object') {
    console.log(JSON.stringify(v).slice(0,300));
  }
}
