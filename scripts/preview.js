/**
 * 版面预览器 (Playwright) —— 把每一页「全部内容都写满」的样子截出来
 * 用法: node preview.js <board.html> <outDir>
 */
const path = require('path');
const fs = require('fs');

(async () => {
  const [htmlFile, outDir] = process.argv.slice(2);
  const { chromium } = require('playwright');

  let browser;
  for (const ch of ['chrome', null]) {
    try {
      browser = await chromium.launch({
        channel: ch,
        args: ['--force-color-profile=srgb', '--font-render-hinting=none',
               '--disable-lcd-text', '--hide-scrollbars'],
      });
      break;
    } catch (e) { /* retry with bundled */ }
  }
  if (!browser) { console.error('BROWSER_LAUNCH_FAILED'); process.exit(1); }

  const page = await browser.newPage({
    viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1,
  });
  await page.goto('file://' + path.resolve(htmlFile));
  await page.waitForTimeout(700);
  fs.mkdirSync(outDir, { recursive: true });

  const n = await page.evaluate(() => document.querySelectorAll('.slide').length);
  for (let i = 0; i < n; i++) {
    await page.evaluate((i) => {
      const S = window.__STAGE;
      const secs = [...document.querySelectorAll('.slide')];
      secs.forEach(s => { s.classList.remove('live'); s.style.transform = ''; });
      secs[i].classList.add('live');
      document.querySelectorAll('.reveal').forEach(e => {
        e.classList.toggle('on', +e.dataset.slide === i);
      });
      document.querySelectorAll('.pline').forEach(e => {
        const r = e.closest('.reveal');
        e.classList.toggle('cur', !!r && +r.dataset.slide === i);
      });
      const cm = document.getElementById('contmark');
      if (cm) cm.style.display = (S.cont && S.cont[i]) ? 'block' : 'none';
      if (S.fitH) {
        const k = Math.min(1, S.avail / Math.max(1, S.fitH[i]));
        if (k < 0.995) secs[i].style.transform = 'scale(' + k.toFixed(4) + ')';
      }
    }, i);
    await page.waitForTimeout(140);
    await page.screenshot({ path: path.join(outDir, `p${String(i).padStart(2, '0')}.png`) });
  }
  await browser.close();
  console.log('PREVIEW_DONE');
})();
