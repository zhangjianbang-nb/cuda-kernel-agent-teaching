// Targeted screenshots for the 工匠笔记 fix (story) and book lead block.
const path = require('path');
const fs = require('fs');
const puppeteer = require('/tmp/node_modules/puppeteer-core');
const SITE = path.resolve(__dirname, '..', 'site');
const QA = path.join(SITE, 'qa');

(async () => {
  const browser = await puppeteer.launch({
    executablePath: '/snap/bin/chromium', headless: true, pipe: true,
    args: ['--headless=new', '--no-sandbox', '--disable-gpu', '--hide-scrollbars',
           '--allow-file-access-from-files'],
    defaultViewport: { width: 1360, height: 900, deviceScaleFactor: 1 },
  });
  const page = await browser.newPage();
  const url = h => 'file://' + path.join(SITE, 'index.html') + h;

  await page.goto(url('#/cuda/story/story-benchmark-republic'), { waitUntil: 'load', timeout: 60000 });
  await new Promise(r => setTimeout(r, 1200));
  const dbg = await page.evaluate(() => {
    const v = document.querySelector('#view');
    return {h1: (v && v.querySelector('h1') || {}).textContent, h3: [...document.querySelectorAll('#view h3')].map(e => e.textContent.trim().slice(0,30)).slice(0,14), txt: (v && v.innerText || '').slice(0,160)};
  });
  console.log(JSON.stringify(dbg));
  const y = await page.evaluate(() => {
    const h = [...document.querySelectorAll('#view h3')].find(e => e.textContent.includes('工匠笔记'));
    if (!h) return -1;
    const r = h.getBoundingClientRect();
    return window.scrollY + r.top - 90;
  });
  console.log('notes y', y);
  if (y >= 0) { await page.evaluate(v => window.scrollTo(0, v), y); await new Promise(r => setTimeout(r, 500)); }
  await page.screenshot({ path: path.join(QA, 'fix-story-notes.png') });

  await page.goto(url('#/cuda/book'), { waitUntil: 'load', timeout: 60000 });
  await new Promise(r => setTimeout(r, 1200));
  await page.screenshot({ path: path.join(QA, 'fix-book-top.png') });

  await browser.close();
  console.log('shots done');
})();
