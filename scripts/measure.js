/**
 * 版面测量器 (Playwright)
 * 用法: node measure.js <board.html> <out.json>
 * 输出: [{avail, h, bh:[每个内容块的真实高度]}, ...]  下标 = slide 序号
 *
 * 测量时把每页单独置为 live、把所有 reveal 块强制显示,
 * 于是拿到的是这一页「全部内容都写满」时的真实高度。
 */
const path = require('path');
const fs = require('fs');

(async () => {
  const [htmlFile, outFile] = process.argv.slice(2);
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
    viewport: { width: 1920, height: 1080 },
    deviceScaleFactor: 1,
  });
  await page.goto('file://' + path.resolve(htmlFile));
  await page.waitForTimeout(600);

  const data = await page.evaluate(() => {
    const stage = document.querySelector('.stage');
    const avail = stage.clientHeight - 58;
    const secs = [...document.querySelectorAll('.slide')];
    document.body.classList.add('meas');
    const out = secs.map(sec => {
      secs.forEach(s => s.classList.remove('live'));
      sec.classList.add('live');
      sec.querySelectorAll('.reveal').forEach(e => e.classList.add('on'));
      const col = sec.querySelector('.passage-text')
               || sec.querySelector('.blindtext')
               || sec.querySelector('.passage-pic')
               || sec;
      const kids = [...col.children];
      const bh = kids.map(k => Math.round(k.getBoundingClientRect().height));
      const h = sec.scrollHeight;
      sec.classList.remove('live');
      sec.querySelectorAll('.reveal').forEach(e => e.classList.remove('on'));
      return { avail: avail, h: h, bh: bh };
    });
    document.body.classList.remove('meas');
    return out;
  });

  fs.writeFileSync(outFile, JSON.stringify(data));
  await browser.close();
  console.log('MEASURED');
})();
