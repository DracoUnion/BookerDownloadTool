/*
 * patch_env_mock_wasm.js
 *
 * 通过 Playwright context.add_init_script() 注入的浏览器环境补丁。
 * 目标：让自动化浏览器（Chromium + AutomationControlled）在
 *   CleanTalk (cleantalk.org/am-i-a-bot)
 *   incolumitas (bot.incolumitas.com)
 *   BrowserScan (browserscan.net/bot-detection)
 *   APIVoid (apivoid.com/tools/bot-detection-test)
 * 等反爬页面的客户端检测下看起来像真实浏览器。
 *
 * 注意：真实浏览器行为基准 ——
 *   navigator.webdriver 值为 false，但 'webdriver' in navigator 为 true
 *   （getter 位于 Navigator.prototype，由引擎提供）。不能把原型 getter 删掉。
 */

(() => {
  // 注意：Playwright add_init_script 每个 document/frame 只执行一次，无需全局守卫。
  // 守卫反而会让补丁只在首个文档(about:blank)生效，后续页面跳过。

  // ============================================================
  // 1. navigator.webdriver 置 false（最核心，四站都查）
  //    真实 Chrome 中 webdriver 位于 Navigator.prototype（getter），
  //    实例上无 own 属性 —— BrowserScan/incolumitas 会检查 own 属性。
  //    若启动参数 --disable-blink-features=AutomationControlled 已让
  //    webdriver 原生为 false，则原型 getter 保持原生，绝不改动；
  //    仅当其为 true 时才把原型 getter 替换为返回 false。
  // ============================================================
  try {
    if (navigator.webdriver === true) {
      Object.defineProperty(Navigator.prototype, 'webdriver', {
        configurable: true,
        enumerable: true,
        get: () => false,
      });
    }
  } catch (e) {}

  // ============================================================
  // 2. window.chrome 对象（真实 Chrome 必有；BrowserScan/incolumitas 检查）
  //    至少提供 runtime/webstore/app/csi/loadTimes，connect/sendMessage 存在。
  //    stealth.min.js 会覆盖，这里兜底。
  // ============================================================
  if (!window.chrome || typeof window.chrome !== 'object') {
    const runtime = {
      connect() { throw new Error('Connect failed.'); },
      sendMessage() {},
      id: 'mock-extension-id',
    };
    window.chrome = {
      runtime,
      app: {},
      csi: function () {},
      loadTimes: function () {},
      webstore: {},
    };
  }

  // ============================================================
  // 3. navigator.plugins / mimeTypes（CleanTalk/incolumitas 检查长度与条目）
  //    - plugins 条目可按下标访问，且每个 plugin 带可遍历的 mimeTypes 子项
  //    - mimeTypes 数量与 plugins 数量匹配
  // ============================================================
  const mimeEntries = [
    { type: 'application/pdf', suffixes: 'pdf', description: 'Portable Document Format' },
    { type: 'text/pdf', suffixes: 'pdf', description: 'Portable Document Format' },
  ];
  const pluginDefs = [
    {
      name: 'Chrome PDF Plugin',
      filename: 'internal-pdf-viewer',
      description: 'Portable Document Format',
      mimes: ['application/pdf', 'text/pdf'],
    },
    {
      name: 'Chrome PDF Viewer',
      filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai',
      description: '',
      mimes: ['application/pdf', 'text/pdf'],
    },
    {
      name: 'Native Client',
      filename: 'internal-nacl-plugin',
      description: '',
      mimes: [],
    },
  ];

  function buildPlugins() {
    const PluginCtor = function () {};
    PluginCtor.prototype[Symbol.toStringTag] = 'Plugin'; // plugins[i].toString() === '[object Plugin]'
    const plugins = [];
    pluginDefs.forEach((def) => {
      const plugin = new PluginCtor();
      // 每个 mimeType 子对象带 enabledPlugin 回链（incolumitas newTests 读取
      // navigator.plugins[0][0].enabledPlugin.name）
      const mimeObjs = def.mimes.map((type) =>
        Object.assign(Object.create(null), mimeEntries.find((m) => m.type === type), { enabledPlugin: null })
      );
      mimeObjs.forEach((m, idx) => {
        Object.defineProperty(plugin, idx, {
          value: m,
          enumerable: true,
          configurable: true,
        });
      });
      // 二次遍历把 enabledPlugin 指回 plugin 自身
      mimeObjs.forEach((m) => { m.enabledPlugin = plugin; });
      Object.defineProperties(plugin, {
        name: { value: def.name, enumerable: true },
        filename: { value: def.filename, enumerable: true },
        description: { value: def.description, enumerable: true },
        length: { value: def.mimes.length },
      });
      plugins.push(plugin);
    });
    // plugins 必须是真 PluginArray 的实例（incolumitas: instanceof PluginArray）
    Object.setPrototypeOf(plugins, PluginArray.prototype || Array.prototype);
    // item()/namedItem() 自实现 —— 避免调用原生 PluginArray 方法时 Illegal invocation。
    // 真实 Chrome 中 item 对下标做 uint32 回绕，越界大值返回首位。
    Object.defineProperty(plugins, 'item', {
      value: function (i) { i = i >>> 0; return this[i % this.length] || null; },
    });
    Object.defineProperty(plugins, 'namedItem', {
      value: function (name) {
        for (let i = 0; i < this.length; i++) {
          if (this[i] && this[i].name === name) return this[i];
        }
        return null;
      },
    });
    return plugins;
  }

  const plugins = buildPlugins();
  Object.defineProperty(navigator, 'plugins', {
    configurable: true,
    enumerable: true,
    get: () => plugins,
  });
  Object.defineProperty(navigator, 'mimeTypes', {
    configurable: true,
    enumerable: true,
    get: () => mimeEntries,
  });
  // 真实 Chrome 桌面端 PDF 查看器默认开启
  try {
    Object.defineProperty(navigator, 'pdfViewerEnabled', {
      configurable: true,
      enumerable: true,
      get: () => true,
    });
  } catch (e) {}

  // ============================================================
  // 4. 窗口尺寸：outer 应大于 inner（真实浏览器含窗口边框/标题栏）
  //    CleanTalk/APIVoid 比较 outer vs inner；0 尺寸与相等都是可疑信号
  // ============================================================
  try {
    const innerW = window.innerWidth;
    const innerH = window.innerHeight;
    const outerW = innerW + 16;   // 纵向滚动条
    const outerH = innerH + 120;  // 标题栏 + 顶部 chrome
    Object.defineProperty(window, 'outerWidth', {
      configurable: true,
      get: () => outerW,
    });
    Object.defineProperty(window, 'outerHeight', {
      configurable: true,
      get: () => outerH,
    });
  } catch (e) {}

  // ============================================================
  // 5. documentMode —— IE 遗留属性，CleanTalk 检查其为 undefined
  // ============================================================
  try {
    Object.defineProperty(document, 'documentMode', {
      configurable: true,
      get: () => undefined,
    });
  } catch (e) {}

  // ============================================================
  // 6. navigator.userAgentData（客户端提示 / Client Hints）
  //    Playwright headless 的 brands 会暴露 "HeadlessChrome" —— APIVoid 与
  //    BrowserScan 都据此判机器人。必须与伪造的 UA (Chrome/124) 对齐。
  //    userAgentData 的 getter 位于 Navigator.prototype 且 configurable=true，
  //    因此整体替换 getter，返回一个与 UA 一致的 mock 对象。
  // ============================================================
  try {
    const realBrands = [
      { brand: 'Chromium', version: '124' },
      { brand: 'Google Chrome', version: '124' },
      { brand: 'Not;A=Brand', version: '24' },
    ];
    const fullVersionList = [
      { brand: 'Chromium', version: '124.0.6367.91' },
      { brand: 'Google Chrome', version: '124.0.6367.91' },
      { brand: 'Not;A=Brand', version: '24.0.0.0' },
    ];
    function makeUAData() {
      const obj = {
        brands: realBrands.slice(),
        mobile: false,
        platform: 'Windows',
        platformVersion: '10.0.0',
        architecture: 'x86',
        bitness: '64',
        model: '',
        wow64: false,
        uaFullVersion: '124.0.6367.91',
        toJSON() {
          return { brands: this.brands, mobile: this.mobile, platform: this.platform, architecture: this.architecture, bitness: this.bitness, model: this.model, platformVersion: this.platformVersion, uaFullVersion: this.uaFullVersion, fullVersionList: fullVersionList.slice(), wow64: this.wow64 };
        },
        getHighEntropyValues(hints) {
          const out = {};
          if (Array.isArray(hints)) {
            if (hints.includes('brands')) out.brands = realBrands.slice();
            if (hints.includes('fullVersionList')) out.fullVersionList = fullVersionList.slice();
            if (hints.includes('platform')) out.platform = 'Windows';
            if (hints.includes('platformVersion')) out.platformVersion = '10.0.0';
            if (hints.includes('architecture')) out.architecture = 'x86';
            if (hints.includes('bitness')) out.bitness = '64';
            if (hints.includes('model')) out.model = '';
            if (hints.includes('mobile')) out.mobile = false;
            if (hints.includes('wow64')) out.wow64 = false;
            if (hints.includes('uaFullVersion')) out.uaFullVersion = '124.0.6367.91';
          }
          return Promise.resolve(out);
        },
      };
      return obj;
    }
    // 整体替换 Navigator.prototype.userAgentData
    const desc = Object.getOwnPropertyDescriptor(Navigator.prototype, 'userAgentData');
    if (desc && desc.configurable) {
      Object.defineProperty(Navigator.prototype, 'userAgentData', {
        configurable: true,
        get: () => makeUAData(),
      });
    }
  } catch (e) {}

  // ============================================================
  // 7. 清理可能残留的自动化全局标记（防御性）
  // ============================================================
  [
    '_phantom', 'callPhantom', '__nightmare', '__phantomas',
    '__webdriver_script_fn', '__webdriver_evaluate', '__webdriver_unwrapped',
    '__webdriver_script_func', '__driver_evaluate', '__selenium_evaluate',
    '__fxdriver_evaluate', '__driver_unwrapped', '__selenium_unwrapped',
    '__fxdriver_unwrapped', '_Selenium_IDE_Recorder', 'callSelenium', '_selenium',
    'domAutomation', 'domAutomationController', '__playwright', '__pw_manual',
    '__PW_inspect', '__pwInitScripts', 'cdc_', '$cdc_asdjflasutopfhvcZLmcfl_',
  ].forEach((k) => {
    try { delete window[k]; } catch (e) {}
  });

  // ============================================================
  // 8. navigator.connection（网络信息）
  //    incolumitas newTests 检查 connectionRTT === 0 判 FAIL；
  //    真实 4G/宽带下 rtt 应 > 0。用一个合理的 NetworkInformation mock。
  // ============================================================
  try {
    const connDesc = Object.getOwnPropertyDescriptor(Navigator.prototype, 'connection');
    if (connDesc && connDesc.configurable) {
      Object.defineProperty(Navigator.prototype, 'connection', {
        configurable: true,
        get: () => ({
          effectiveType: '4g',
          rtt: 50,
          downlink: 10,
          saveData: false,
          addEventListener: function () {},
          removeEventListener: function () {},
        }),
      });
    }
  } catch (e) {}

  // ============================================================
  // 9. WASM 兼容层
  //    四站检测脚本都会执行 WebAssembly.validate / 构造 Module / Memory。
  //    这里提供一个**合法**的最小 WASM 模块：导出 memory 与 _calculate_hash。
  //    exports 对象是冻结的，无法用 JS 覆盖导出函数 —— 因此
  //    _calculate_hash 用真实 WASM 函数实现（no-op stub，toString 为原生形式，
  //    反而比 JS 函数更像真实 wasm）。用 try/catch 包裹，任何页面都不抛错。
  // ============================================================
  try {
    const wasmBytes = new Uint8Array([
      0x00, 0x61, 0x73, 0x6d,             // \0asm
      0x01, 0x00, 0x00, 0x00,             // version 1
      0x01, 0x04, 0x01, 0x60, 0x00, 0x00, // type section: func () -> ()
      0x03, 0x02, 0x01, 0x00,             // function section: func#0 = type#0
      0x05, 0x03, 0x01, 0x00, 0x01,       // memory section: 1 page
      0x07, 0x1c, 0x02,                   // export section: 2 exports (size = 1 + 9 + 18 = 28 = 0x1c)
      0x06, 0x6d, 0x65, 0x6d, 0x6f, 0x72, 0x79, 0x02, 0x00,             // "memory" (mem#0)
      0x0f, 0x5f, 0x63, 0x61, 0x6c, 0x63, 0x75, 0x6c, 0x61, 0x74, 0x65, // "_calculate_hash"
      0x5f, 0x68, 0x61, 0x73, 0x68, 0x00, 0x00,                        // (func#0)
      0x0a, 0x04, 0x01, 0x02, 0x00, 0x0b, // code section: empty body, end
    ]);
    const wasmModule = new WebAssembly.Module(wasmBytes);
    window.__patch_wasm_module = wasmModule;
    window.__patch_wasm_instance = new WebAssembly.Instance(wasmModule);
  } catch (e) {
    // 任何情况都不允许这个补丁影响页面
  }
})();
