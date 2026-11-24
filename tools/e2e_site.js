// 多领域端到端验收：数据层（每领域 bundle 的模块/长文/字数）+ 渲染层（7 领域路由、详情页、窄屏）。
// 用法：node tools/e2e_site.js [--quick]
// --quick 只做数据层，不启动 chromium。
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const RUN = path.resolve(__dirname, '..');
const SITE = path.join(RUN, 'site');
const QUICK = process.argv.includes('--quick');

function loadJs(file) {
  const sandbox = { window: {}, console };
  vm.createContext(sandbox);
  vm.runInContext(fs.readFileSync(file, 'utf8'), sandbox);
  return sandbox.window;
}

// 懒加载拆分后：core.js + sec-*.js 在同一 sandbox 里依次执行，得到完整领域数据
function loadDomainJs(dir) {
  const sandbox = { window: {}, console };
  vm.createContext(sandbox);
  const rank = f => (f === 'core.js' ? 0 : f.startsWith('sec-') ? 1 : 2);
  const files = fs.readdirSync(dir).filter(f => f.endsWith('.js'))
    .sort((a, b) => rank(a) - rank(b) || a.localeCompare(b));
  for (const f of files) vm.runInContext(fs.readFileSync(path.join(dir, f), 'utf8'), sandbox);
  return sandbox.window;
}

function vis(html) {
  return (html || '')
    .replace(/<script[\s\S]*?<\/script>/g, '')
    .replace(/<style[\s\S]*?<\/style>/g, '')
    .replace(/<[^>]+>/g, '')
    .replace(/\s+/g, ' ')
    .trim().length;
}

function deepText(o) {
  if (typeof o === 'string') return o;
  if (Array.isArray(o)) return o.map(deepText).join(' ');
  if (o && typeof o === 'object') return Object.values(o).map(deepText).join(' ');
  return '';
}

const MIN = {
  papers: 6000, algorithms: 8000, theory: 8000, directions: 9000,
  stories: 6000, assessments: 900, book: 3000, appendix: 3000,
};
const MODS = ['papers', 'algorithms', 'theory', 'directions', 'stories', 'assessments', 'book', 'appendix'];

let fails = 0;
function bad(msg) { console.error('FAIL ' + msg); fails++; }

const manifest = loadJs(path.join(SITE, 'data', 'manifest.js')).SITE_DOMAINS || [];
const oi = process.argv.indexOf('--only');
const ONLY = oi >= 0 && process.argv[oi + 1] ? process.argv[oi + 1].split(',').filter(Boolean) : null;
if (ONLY) {
  const ids = manifest.map(d => d.id);
  for (const d of ONLY) if (!ids.includes(d)) bad('manifest 缺领域 ' + d);
} else if (manifest.length !== 1) bad('manifest 领域数=' + manifest.length + '（应为 1）');

const domains = {};
for (const d of manifest) {
  if (ONLY && !ONLY.includes(d.id)) continue;
  const dir = path.join(SITE, 'data', 'domains', d.id);
  if (!fs.existsSync(path.join(dir, 'core.js'))) { bad(d.id + ' 缺 core.js'); continue; }
  const w = loadDomainJs(dir);
  const D = (w.SITE_DATA_BY_DOMAIN || {})[d.id];
  if (!D) { bad(d.id + ' 数据未注册到 SITE_DATA_BY_DOMAIN'); continue; }
  domains[d.id] = D;
  let total = 0, pages = 0;
  for (const m of MODS) {
    const mod = D[m];
    if (!mod) { bad(d.id + ' 缺模块 ' + m); continue; }
    const items = Array.isArray(mod) ? mod
      : (mod.items || mod.papers || mod.algorithms || mod.theory ||
         mod.stories || mod.assessments || mod.sections || mod.entries || []);
    if (!items.length) { bad(d.id + '/' + m + ' 无条目'); continue; }
    let mv = 0;
    for (const it of items) {
      pages++;
      const id = it.id || it.item_id;
      if (!id) bad(d.id + '/' + m + ' 有条目缺 id');
      const t = it.title || it.name || it.question || it.q || '';
      if (!t) bad(d.id + '/' + m + '/' + id + ' 缺标题');
      const html = it.long_html || it.html || '';
      const v = vis(html);
      mv += v;
      if (v < (MIN[m] || 0)) bad(d.id + '/' + m + '/' + id + ' 可见 ' + v + ' < ' + MIN[m]);
    }
    total += mv;
  }
  // 落地页（domain/evolution/coverage/summary）在前端由结构化字段渲染（intro/scope/
  // home_figure/timeline/sections…），bundle 里没有 long_html；这里把所有字符串字段
  // 递归拼起来量可见字数，才是页面真正能读到的正文量。
  // 阈值按页面性质区分：domain 是领域首页（导语+学习路径+技术栈图+表），
  // coverage 是覆盖审计页（检索来源/缺口/局限，本身就以表格为主），都比正文页短。
  const LANDING_MIN = { domain: 1000, evolution: 1500, coverage: 300, summary: 1500 };
  for (const m of ['domain', 'evolution', 'coverage', 'summary']) {
    const v = vis(deepText(D[m] || {}));
    if (v < LANDING_MIN[m]) bad(d.id + '/' + m + ' 整页可见 ' + v + ' < ' + LANDING_MIN[m]);
    total += v; pages++;
  }
  const st = (D.domain || {}).stats || {};
  console.log(`DATA ${d.id}: pages=${pages} vis=${total} stats=${JSON.stringify(st)}`);
  if (total < 200000) bad(d.id + ' 总可见 ' + total + ' < 200000（数据未生成完？）');
}

if (QUICK) {
  console.log(fails ? `E2E-DATA FAIL ${fails}` : 'E2E-DATA PASS');
  process.exit(fails ? 1 : 0);
}

// ---------- 渲染层 ----------
const puppeteer = require('/tmp/node_modules/puppeteer-core');

function firstId(D, key, alt) {
  const mod = D[key];
  const items = Array.isArray(mod) ? mod : ((mod || {})[alt] || (mod || {}).items || []);
  return items.length ? (items[0].id || items[0].item_id) : '';
}

(async () => {
  const browser = await puppeteer.launch({
    executablePath: '/snap/bin/chromium', headless: true, pipe: true,
    args: ['--headless=new', '--no-sandbox', '--disable-gpu', '--hide-scrollbars',
           '--allow-file-access-from-files'],
    defaultViewport: { width: 1360, height: 900, deviceScaleFactor: 1 },
  });
  fs.mkdirSync(path.join(SITE, 'qa'), { recursive: true });
  const page = await browser.newPage();
  const url = (hash) => 'file://' + path.join(SITE, 'index.html') + hash;

  async function open(hash, minText, wantSvg, wantTable, shot) {
    await page.goto(url(hash), { waitUntil: 'load', timeout: 60000 });
    await new Promise(r => setTimeout(r, 900));
    const r = await page.evaluate(() => {
      const v = document.querySelector('#view') || document.body;
      const h1 = v.querySelector('h1');
      const txt = (v.innerText || '').replace(/\s+/g, ' ').trim();
      const over = [...document.querySelectorAll('body *')].filter(e => {
        // 可横向滚动的容器（演进关系图 #evo-graph、公式块 .formula）里的内容被裁切，
        // 不算页面溢出；只有真正顶破视口、且没有滚动容器的元素才算。
        for (let a = e; a && a !== document.body; a = a.parentElement) {
          const ox = getComputedStyle(a).overflowX;
          if (ox === 'auto' || ox === 'scroll' || ox === 'hidden') return false;
        }
        const b = e.getBoundingClientRect();
        return b.width > 0 && b.right > document.documentElement.clientWidth + 2;
      }).length;
      return {
        h1: h1 ? h1.textContent.trim().slice(0, 60) : '',
        len: txt.length,
        svgs: v.querySelectorAll('svg').length,
        tables: v.querySelectorAll('table').length,
        over,
        bar: document.querySelectorAll('.domain-bar a').length,
        err: /加载失败|未找到该页面|undefined/.test(txt.slice(0, 400)),
      };
    });
    if (!r.h1) bad(hash + ' 无 h1');
    if (r.len < minText) bad(hash + ' 正文 ' + r.len + ' < ' + minText);
    if (wantSvg && r.svgs < 1) bad(hash + ' 无 SVG');
    if (wantTable && r.tables < 1) bad(hash + ' 无表格');
    if (r.over > 3) bad(hash + ' 横向溢出元素 ' + r.over);
    if (r.err) bad(hash + ' 页面报错文案');
    if (shot) await page.screenshot({ path: path.join(SITE, 'qa', shot + '.png') });
    return r;
  }

  // 落地页
  const land = await open('#/', 400, false, false, 'landing');
  if (land.bar !== 1) bad('#/ 领域栏链接 ' + land.bar + ' ≠ 1');

  for (const d of manifest) {
    const D = domains[d.id];
    if (!D) continue;
    const home = await open('#/' + d.id + '/home', 800, true, true, 'home');
    if (home.bar !== 1) bad(d.id + '/home 领域栏 ' + home.bar + ' ≠ 1');
    await open('#/' + d.id + '/map', 800, true, false, 'map');
    await open('#/' + d.id + '/papers', 800, false, false, 'papers');
    const pid = firstId(D, 'papers');
    if (pid) await open('#/' + d.id + '/papers/' + pid, 3000, true, true, 'paper-detail');
    const aid = firstId(D, 'algorithms');
    if (aid) await open('#/' + d.id + '/algos/' + aid, 3000, true, true, 'algo-detail');
    const tid = firstId(D, 'theory');
    if (tid) await open('#/' + d.id + '/theory/' + tid, 3000, true, false, 'theory-detail');
    const sid = firstId(D, 'stories');
    if (sid) await open('#/' + d.id + '/story/' + sid, 3000, true, false, 'story-detail');
    // 精读课程（deepdive）的详情页是「论文」讲次，不是方向 id；用论文 id 才打得开。
    const lid = firstId(D, 'papers');
    if (lid) await open('#/' + d.id + '/deepdive/' + lid, 3000, true, true, 'deepdive');
    await open('#/' + d.id + '/book', 800, true, false, 'book');
    await open('#/' + d.id + '/appendix', 800, true, false, 'appendix');
    await open('#/' + d.id + '/exam', 800, false, false, 'exam');
    await open('#/' + d.id + '/evolution', 500, false, true, 'evolution');
    await open('#/' + d.id + '/summary', 500, false, false, 'summary');
  }

  // 单领域：无领域切换检查
  await browser.close();
  console.log(fails ? `E2E FAIL ${fails}` : 'E2E PASS');
  process.exit(fails ? 1 : 0);
})().catch(e => { console.error('E2E CRASH', e); process.exit(2); });
