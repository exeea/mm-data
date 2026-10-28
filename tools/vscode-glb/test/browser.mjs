import { chromium } from '@playwright/test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import http from 'node:http';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const { html } = require('../src/html.cjs'), { loadAsset, findRoots } = require('../src/assets.cjs'), { findEngine, preview } = require('../src/engine.cjs');
const { depthFixture } = require('./depth-fixture.cjs');
const { gitFixture } = require('./git-fixture.cjs'), { gitSource } = require('../src/git-source.cjs');
const extension = path.resolve(import.meta.dirname, '..'), dataRoot = path.resolve(extension, '../..');
const output = path.join(extension, 'test-output'); await fs.mkdir(output, { recursive: true });
let origin, current = 'buildings/walls/medium/straight.glb', variant = '', page, generation = 0, peer, relay = false, comparison;
const resources = new Map(), errors = [], consoleErrors = [];
const server = http.createServer(async (req, res) => {
  try {
    const url = new URL(req.url, origin);
    if (url.pathname === '/favicon.ico') { res.statusCode = 204; return res.end(); }
    if (url.pathname === '/') { res.setHeader('Content-Type', 'text/html'); return res.end(html({ cspSource: origin, nonce: 'browser-test', script: `${origin}/viewer.js`, style: `${origin}/viewer.css` })); }
    const file = url.pathname === '/viewer.js' ? path.join(extension, 'dist/viewer.js') : url.pathname === '/viewer.css' ? path.join(extension, 'dist/viewer.css') : resources.get(url.pathname);
    if (!file) { res.statusCode = 404; return res.end(); }
    res.setHeader('Content-Type', file.endsWith('.js') ? 'text/javascript' : file.endsWith('.css') ? 'text/css' : file.endsWith('.jpg') ? 'image/jpeg' : 'image/png'); res.setHeader('Cache-Control', 'no-store'); res.end(await fs.readFile(file));
  } catch (error) { res.statusCode = 500; res.end(error.message); }
});
await new Promise(resolve => server.listen(0, '127.0.0.1', resolve)); origin = `http://127.0.0.1:${server.address().port}`;
const engine = await findEngine('', dataRoot);
async function deliver() {
  const file = path.join(dataRoot, 'data/models', current), roots = await findRoots(file);
  const asset = await loadAsset(file, roots, p => { const key = `/asset/${resources.size}`; resources.set(key, p); return origin + key; }, variant);
  await page.evaluate(message => window.postMessage(message, '*'), { type: 'asset', asset, generation: ++generation, variant, engine, trusted: true });
  return asset;
}
const browser = await chromium.launch({ channel: 'msedge', headless: true, args: ['--disable-gpu-sandbox'] });
function mockApi() {
  let state;
  window.__MM_TEST__ = { count: 0, failures: [], sent: 0, api: {
    postMessage: m => {
      if (m.type === 'screenshot') window.__MM_TEST__.screenshot = m.data;
      if (m.type === 'viewState') { window.__MM_TEST__.shared = m.state; window.__MM_TEST__.sharedAt = Date.now(); window.__MM_TEST__.sent++; }
      return window.mmMessage(m);
    }, getState: () => state, setState: v => state = v
  }, loaded() { this.count++; }, failed(error) { this.failures.push(error); } };
}
try {
  page = await browser.newPage({ viewport: { width: 1280, height: 850 } });
  page.on('pageerror', error => errors.push(error.message)); page.on('console', message => { if (message.type() === 'error' && !message.text().includes('favicon')) consoleErrors.push(message.text()); });
  await page.exposeFunction('mmMessage', async message => {
    try {
      if (message.type === 'viewState' && relay) await peer.evaluate(state => window.postMessage({ type: 'linkedView', state }, '*'), message.state);
      if (['ready', 'reload'].includes(message.type)) await deliver();
      if (message.type === 'variant') { variant = message.value; await deliver(); }
      if (message.type === 'test') {
        await page.evaluate(() => window.postMessage({ type: 'engineBusy', message: 'Testing…' }, '*'));
        const result = await preview(engine, { ...message.settings, model: path.join(dataRoot, 'data/models', current), modelsRoot: path.join(dataRoot, 'data/models') });
        await page.evaluate(msg => { window.postMessage(msg, '*'); window.postMessage({ type: 'engineIdle' }, '*'); }, { type: 'assembly', kind: message.settings.kind, result });
      }
      if (message.type === 'screenshot') await fs.writeFile(path.join(output, 'exported-preview.png'), Buffer.from(message.data.split(',')[1], 'base64'));
    } catch (error) { errors.push(error.message); }
  });
  await page.addInitScript(mockApi);
  async function ready(expected) { await page.waitForFunction(n => window.__MM_TEST__.count >= n || window.__MM_TEST__.failures.length, expected, { timeout: 45000 }); assert.deepEqual(await page.evaluate(() => window.__MM_TEST__.failures), []); }
  await page.goto(origin); await ready(1);
  assert(await page.locator('#lodStats tbody tr').count() >= 1);
  await page.locator('[data-tab="test"]').click(); await page.locator('#height').fill('3'); await page.locator('[data-preset="straight"]').click(); await page.locator('[data-reach="S"]').fill('1'); await page.locator('#rotation').selectOption('2'); await page.locator('#test').click();
  await page.waitForFunction(() => document.getElementById('engineStatus').textContent.startsWith('PASS:'), null, { timeout: 45000 });
  assert.equal(await page.evaluate(() => window.__MM_TEST__.stats.assembled), true);
  await page.evaluate(() => window.postMessage({ type: 'linkedView', state: window.__MM_TEST__.shared }, '*'));
  await page.evaluate(() => new Promise(requestAnimationFrame));
  assert.equal(await page.evaluate(() => window.__MM_TEST__.stats.assembled), true, 'Linked camera/display settings must not discard a local engine assembly');
  await page.screenshot({ path: path.join(output, 'wall-assembled.png') });
  await page.locator('#authored').click(); assert.equal(await page.evaluate(() => window.__MM_TEST__.stats.assembled), false);
  await page.locator('[data-tab="view"]').click(); await page.locator('#projection').selectOption('ortho'); await page.locator('[data-camera="top"]').click(); await page.locator('#wire').check(); await page.locator('#wire').uncheck();
  await page.locator('#shading').selectOption('normal'); await page.locator('#shading').selectOption('uv'); await page.locator('#shading').selectOption('pbr');
  await page.locator('#projection').selectOption('perspective'); await page.locator('[data-camera="iso"]').click();
  for (const name of ['board/scenery/military/cargo-crate.glb', 'board/scenery/vehicles/car.glb', 'board/vegetation/pine.glb', 'board/scenery/military/fortification.glb']) {
    current = name; variant = ''; const count = await page.evaluate(() => window.__MM_TEST__.count); const asset = await deliver(); await ready(count + 1); await page.locator('#fit').click();
    if (name.includes('cargo-crate')) {
      await page.locator('#label').fill('MM'); await page.locator('#bounds').check(); await page.locator('#measure').click();
      await page.locator('#canvas').click({ position: { x: 430, y: 380 } }); await page.locator('#canvas').click({ position: { x: 520, y: 400 } });
      assert.match(await page.locator('#measurement').textContent(), /model units/);
      await page.locator('#screenshot').click();
    }
    if (name.includes('/car.')) { const picker = page.locator('#colours input[type=color]').first(); await picker.fill('#00ff88'); assert.equal(await picker.inputValue(), '#00ff88'); }
    if (name.includes('/pine.')) { const n = await page.evaluate(() => window.__MM_TEST__.count); await page.locator('#variant').selectOption('snow'); await ready(n + 1); }
    if (name.includes('fortification')) await page.locator('#helpers').check();
    assert(asset.statistics.rows.every(r => Number.isFinite(r.vertices) && Number.isFinite(r.triangles)));
    await page.screenshot({ path: path.join(output, path.basename(name, '.glb') + '.png') });
    await page.locator('[data-tab="materials"]').click(); assert(await page.locator('#materialList option').count() > 0); await page.locator('[data-tab="view"]').click();
  }
  await page.setViewportSize({ width: 640, height: 720 }); await page.screenshot({ path: path.join(output, 'narrow-viewer.png') });
  assert.equal(await page.locator('body').evaluate(el => el.scrollWidth <= innerWidth), true);
  await page.setViewportSize({ width: 1280, height: 850 });
  const fixture = path.join(output, 'depth-fixture.glb'); await fs.writeFile(fixture, depthFixture());
  const depth = await loadAsset(fixture, await findRoots(fixture));
  const count = await page.evaluate(() => window.__MM_TEST__.count);
  await page.evaluate(message => window.postMessage(message, '*'), { type: 'asset', asset: depth, generation: ++generation, trusted: true }); await ready(count + 1);
  for (const id of ['grid', 'helpers', 'bounds', 'bloom']) await page.locator('#' + id).uncheck();
  for (const projection of ['perspective', 'ortho']) {
    await page.locator('#projection').selectOption(projection); await page.locator('[data-camera="iso"]').click();
    for (const view of ['fitted', 'orbit', 'zoom out', 'zoom in']) {
      const rect = await page.locator('#canvas').boundingBox(), x = rect.x + rect.width / 2, y = rect.y + rect.height / 2;
      if (view === 'orbit') { await page.mouse.move(x, y); await page.mouse.down(); await page.mouse.move(x + 85, y, { steps: 8 }); await page.mouse.up(); }
      if (view.startsWith('zoom')) { await page.mouse.move(x, y); await page.mouse.wheel(0, view === 'zoom out' ? 400 : -800); }
      await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
      await page.evaluate(() => { window.__MM_TEST__.screenshot = null; }); await page.locator('#screenshot').click();
      const pixels = await page.evaluate(async () => {
        const image = new Image(); image.src = window.__MM_TEST__.screenshot; await image.decode(); const canvas = document.createElement('canvas'); canvas.width = image.width; canvas.height = image.height;
        const context = canvas.getContext('2d'); context.drawImage(image, 0, 0); const values = context.getImageData(0, 0, canvas.width, canvas.height).data;
        // Tone mapping mixes colour channels, so detect dominant colours rather than exact RGB.
        let red = 0, green = 0; for (let i = 0; i < values.length; i += 4) { if (values[i] > 80 && values[i] > values[i + 1] * 1.25) red++; if (values[i + 1] > 80 && values[i + 1] > values[i] * 1.25) green++; }
        return { red, green };
      });
      console.log(`Depth precision (${projection}, ${view}): ${JSON.stringify(pixels)}`);
      assert(pixels.green > 1000, 'The front surface must be visible');
      // A thin exposed rim is valid because the planes have slightly different projected edges.
      assert(pixels.red < (pixels.green + pixels.red) * .001 + 5, 'The rear surface must not bleed through a nearer surface');
    }
  }
  await fs.rm(fixture);
  comparison = await gitFixture(output);
  const snapshot = await gitSource(comparison.file, '');
  const staged = await loadAsset(comparison.file, await findRoots(comparison.file, '', [], snapshot.io), snapshot.urlFor, '', snapshot.io); staged.revision = 'Staged';
  const working = await loadAsset(comparison.file, await findRoots(comparison.file), p => { const key = `/asset/${resources.size}`; resources.set(key, p); return origin + key; }); working.revision = 'Working copy';
  const beforeComparison = await page.evaluate(() => window.__MM_TEST__.count);
  await page.evaluate(message => window.postMessage(message, '*'), { type: 'asset', asset: working, generation: ++generation, trusted: true }); await ready(beforeComparison + 1);
  peer = await browser.newPage({ viewport: { width: 1280, height: 850 } }); peer.on('pageerror', error => errors.push(error.message));
  await peer.exposeFunction('mmMessage', async message => {
    if (message.type === 'ready') await peer.evaluate(asset => window.postMessage({ type: 'asset', asset, generation: 1, trusted: true, revision: true }, '*'), staged);
    if (message.type === 'viewState' && relay) await page.evaluate(state => window.postMessage({ type: 'linkedView', state }, '*'), message.state);
  });
  await peer.addInitScript(mockApi); await peer.goto(origin);
  await peer.waitForFunction(() => window.__MM_TEST__.count === 1 || window.__MM_TEST__.failures.length); assert.deepEqual(await peer.evaluate(() => window.__MM_TEST__.failures), []);
  relay = true;
  await page.locator('#projection').selectOption('perspective'); await page.locator('#lod').selectOption('1');
  await peer.waitForFunction(() => document.getElementById('lod').value === '1');
  assert.match(await page.locator('#status').textContent(), /15\.0/); assert.match(await peer.locator('#status').textContent(), /10\.0/);
  await page.locator('#wire').check(); await peer.waitForFunction(() => document.getElementById('wire').checked);
  await peer.locator('#shading').selectOption('normal'); await page.waitForFunction(() => document.getElementById('shading').value === 'normal');
  async function sameCamera(source, target) {
    await source.waitForFunction(() => Date.now() - window.__MM_TEST__.sharedAt > 180);
    const pose = await source.evaluate(() => window.__MM_TEST__.shared.camera);
    await target.waitForFunction(expected => {
      const actual = window.__MM_TEST__.api.getState().camera;
      return actual && ['position', 'target'].every(key => actual[key].every((n, i) => Math.abs(n - expected[key][i]) < 1e-6)) && Math.abs(actual.zoom - expected.zoom) < 1e-6;
    }, pose);
  }
  const viewport = await page.locator('#canvas').boundingBox(), cx = viewport.x + viewport.width / 2, cy = viewport.y + viewport.height / 2;
  await page.mouse.move(cx, cy); await page.mouse.down(); await page.mouse.move(cx + 120, cy + 25, { steps: 10 }); await page.mouse.up(); await sameCamera(page, peer);
  await page.mouse.move(cx, cy); await page.mouse.down({ button: 'right' }); await page.mouse.move(cx + 35, cy - 20, { steps: 6 }); await page.mouse.up({ button: 'right' }); await sameCamera(page, peer);
  const peerViewport = await peer.locator('#canvas').boundingBox(); await peer.mouse.move(peerViewport.x + peerViewport.width / 2, peerViewport.y + peerViewport.height / 2); await peer.mouse.wheel(0, 300); await sameCamera(peer, page);
  await peer.locator('#projection').selectOption('ortho'); await page.waitForFunction(() => document.getElementById('projection').value === 'ortho'); await sameCamera(peer, page);
  await peer.locator('#syncViews').uncheck(); await page.locator('#wire').uncheck(); await page.waitForTimeout(150); assert.equal(await peer.locator('#wire').isChecked(), true);
  await peer.locator('#syncViews').check(); await page.waitForFunction(() => document.getElementById('wire').checked);
  await sameCamera(peer, page); const sent = await page.evaluate(() => window.__MM_TEST__.sent); await page.waitForTimeout(250); assert.equal(await page.evaluate(() => window.__MM_TEST__.sent), sent, 'Linked updates must not echo forever');
  await page.screenshot({ path: path.join(output, 'working-comparison.png') }); await peer.screenshot({ path: path.join(output, 'staged-comparison.png') });
  await peer.setViewportSize({ width: 420, height: 720 }); await peer.locator('#inspectorToggle').click();
  assert.equal(await peer.locator('#inspector').isVisible(), false, 'The inspector must not cover toolbar controls in a narrow comparison pane');
  assert.equal(await peer.locator('body').evaluate(el => el.scrollWidth <= innerWidth), true);
  await peer.screenshot({ path: path.join(output, 'narrow-comparison.png') });
  assert.deepEqual(errors, []); assert.deepEqual(consoleErrors, []);
  console.log('Browser PASS: asset features, surface depth, distinct Git versions, linked LOD/display controls, bidirectional camera orbit/zoom/projection, unlink/relink and no feedback loop.');
} finally { relay = false; await browser.close(); await new Promise(resolve => server.close(resolve)); await comparison?.dispose(); }
