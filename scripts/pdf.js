// 用系统 Chrome 把卡片页 HTML 打成 A4 PDF
// 用法: node pdf.js <cards.html> <out.pdf>
const { chromium } = require('playwright');

(async () => {
  const [htmlPath, outPdf] = process.argv.slice(2);
  const browser = await chromium.launch({ channel: 'chrome' });
  const page = await browser.newPage();
  await page.goto('file://' + htmlPath, { waitUntil: 'load' });
  await page.emulateMedia({ media: 'print' });
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(500);
  const n = await page.$$eval('.page', els => els.length);
  await page.pdf({
    path: outPdf,
    printBackground: true,
    preferCSSPageSize: true,
    margin: { top: '0', right: '0', bottom: '0', left: '0' }
  });
  await browser.close();
  console.log('PDF_OK ' + n + ' pages');
})();
