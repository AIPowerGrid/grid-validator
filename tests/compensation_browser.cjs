// SPDX-FileCopyrightText: 2026 AI Power Grid
// SPDX-License-Identifier: AGPL-3.0-or-later

// Run with Playwright installed outside the dependency-light validator package.
const assert = require('node:assert/strict');
const {spawn} = require('node:child_process');
const {mkdtempSync} = require('node:fs');
const {tmpdir} = require('node:os');
const {join} = require('node:path');
const {createInterface} = require('node:readline');
const {chromium} = require('playwright');

async function main() {
  const child = spawn(process.env.VALIDATOR_TEST_PYTHON || 'python3', ['-m','tests.compensation_app_fixture'], {stdio:['pipe','pipe','pipe']});
  const lines = [], waiting = [];
  const reader = createInterface({input:child.stdout});
  reader.on('line', line => waiting.length ? waiting.shift()(line) : lines.push(line));
  const next = () => lines.length ? Promise.resolve(lines.shift()) : new Promise(resolve => waiting.push(resolve));
  const limit = (promise) => Promise.race([promise, new Promise((_,reject) => {
    const timer = setTimeout(() => reject(new Error('fixture timeout')), 15000); timer.unref();
  })]);
  const command = async value => { child.stdin.write(value+'\n'); return JSON.parse(await limit(next())); };
  let browser;
  try {
    const url = await limit(next());
    assert.match(url,/^http:\/\/127\.0\.0\.1:[0-9]+\/#/);
    browser = await chromium.launch({headless:true});
    const page = await browser.newPage({viewport:{width:1280,height:900}});
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(url);
    await page.locator('#comp-refresh:not([disabled])').waitFor();
    assert.equal((await command('status')).calls,0);
    await page.click('#comp-refresh');
    await page.getByRole('button',{name:'Set payout wallet',exact:true}).waitFor();
    await page.getByRole('button',{name:'Set payout wallet',exact:true}).click();
    await page.locator('#comp-open:visible').waitFor();
    assert.equal((await command('status')).signed,0);
    await command('approve');
    await page.locator('#comp-confirm:visible').waitFor({timeout:15000});
    await page.click('#comp-confirm');
    await page.locator('#comp-consent[open]').waitFor();
    assert.match(await page.locator('#comp-consent-amount').innerText(),/100\.000000000000000001 AIPG/);
    await page.keyboard.press('Escape');
    assert.equal((await command('status')).signed,0);
    await page.click('#comp-confirm');
    await page.reload();
    await page.locator('#comp-confirm:visible').waitFor();
    assert.equal(await page.locator('#comp-consent').evaluate(e=>e.open),false);
    assert.equal((await command('status')).signed,0);
    const output = mkdtempSync(join(tmpdir(),'aipg-validator-compensation-ui-'));
    for (const width of [320,390,1280]) {
      await page.setViewportSize({width,height:900});
      await page.click('#comp-confirm');
      await page.locator('#comp-consent[open]').waitFor();
      assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth <= innerWidth),true);
      const bounds = await page.locator('#comp-consent').boundingBox();
      assert(bounds.x >= 0 && bounds.x + bounds.width <= width);
      await page.screenshot({path:join(output,`consent-${width}.png`),fullPage:true});
      await page.keyboard.press('Escape');
    }
    await page.click('#comp-confirm');
    await page.getByRole('button',{name:'Confirm destination',exact:true}).click();
    await page.locator('#comp-request-status').filter({hasText:'Awaiting maintainer review'}).waitFor();
    assert.equal((await command('status')).signed,1);
    await page.reload();
    await page.locator('#comp-request-status').filter({hasText:'Awaiting maintainer review'}).waitFor();
    assert.equal((await command('status')).signed,1);
    await command('outage');
    await page.click('#comp-refresh');
    await page.locator('#comp-error:visible').waitFor();
    assert.equal(await page.locator('#comp-confirm').isVisible(),false);
    assert.equal((await command('status')).signed,1);
    assert.deepEqual(errors,[]);
    console.log(JSON.stringify({passed:true,viewports:[320,390,1280],signatures:1,screenshots:output}));
  } finally {
    if (browser) await browser.close();
    child.stdin.end('quit\n');
    await limit(new Promise(resolve => child.exitCode !== null ? resolve() : child.once('exit',resolve))).catch(()=>child.kill('SIGKILL'));
    reader.close();
  }
}
main().catch(error=>{console.error(error.message);process.exitCode=1;});
