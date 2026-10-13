/**
 * 封面截图器 (Playwright)
 * 用法: node cover.js <cover.html> <out.png> <width> <height>
 * 依赖 cover.html 里的 .cover 铺满整个视口(100vw x 100vh)
 */
const path = require('path');

(async () => {
  const [htmlFile, outPng, w, h] = process.argv.slice(2);
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
    } catch (e) { /* retry with bundled chromium */ }
  }
  if (!browser) { console.error('BROWSER_LAUNCH_FAILED'); process.exit(1); }

  const page = await browser.newPage({
    viewport: { width: +w, height: +h }, deviceScaleFactor: 1,
  });
  await page.goto('file://' + path.resolve(htmlFile));
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(700);
  await page.screenshot({ path: outPng });
  await browser.close();
  console.log('COVER_OK');
})();
