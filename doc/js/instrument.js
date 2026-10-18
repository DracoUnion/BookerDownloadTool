const fs = require('fs');
function loadModule(file, requireFn, patch) {
  let src = fs.readFileSync(file, 'utf-8').trim();
  src = src.replace(/^\d+:/, '');
  if (src.endsWith(',')) src = src.slice(0, -1);
  if (patch) src = patch(src);
  const m = { exports: {} };
  const callable = new Function('module','exports','require','return (' + src + ')(module, exports, require);');
  callable(m, m.exports, requireFn);
  return m.exports;
}
const m74185 = loadModule('module_74185.js', () => {});
global.window = global;
const requireFn = (id) => { if (id === 74185) return m74185; throw new Error('missing ' + id); };

// Patch: log what _encrypt receives. We can't easily hook _encrypt (defined in VM), but we CAN
// hook __g.x and __g.r which are plain object methods.
// Strategy: after main load, overwrite __g methods? They're module-closed.
// Instead, patch the module source to add console.log inside x and r.
function patch(src) {
  // add logging to __g.x
  src = src.replace(
    '__g={x:function(ei,eo){',
    '__g={x:function(ei,eo){console.log("x input", JSON.stringify(ei), "key", JSON.stringify(eo));'
  );
  src = src.replace(
    'r:function(ei){',
    'r:function(ei){console.log("r input", JSON.stringify(ei));'
  );
  return src;
}

const exports1514 = loadModule('module1514.js', requireFn, patch);
console.log('ZP("hello") =', exports1514.ZP('hello'));
