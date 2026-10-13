/**
 * 板书帧渲染器 (Playwright)
 * 用法: node shot.js <plan.json> <html> <outDir>
 * plan.json: [{ out:"f00000.png", step:3, t:1.0, shadow:[idx, time] }]
 */
const path = require('path');
const fs = require('fs');

(async () => {
  const [planFile, htmlFile, outDir] = process.argv.slice(2);
  const plan = JSON.parse(fs.readFileSync(planFile, 'utf8'));
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
  await page.waitForTimeout(500);

  for (let i = 0; i < plan.length; i++) {
    const p = plan[i];
    await page.evaluate(([g, t]) => window.setStep(g, t), [p.step, p.t]);
    if (p.shadow) {
      await page.evaluate(([z, t]) => window.setShadow(z, t), p.shadow);
    }
    await page.waitForTimeout(p.settle || 26);
    await page.screenshot({ path: path.join(outDir, p.out) });
    if (i % 10 === 0 || i === plan.length - 1) {
      process.stdout.write(`\r  frame ${i + 1}/${plan.length}   `);
    }
  }
  process.stdout.write('\n');
  await browser.close();
  console.log('DONE');
})();