const vscode = require('vscode');
const assert = require('node:assert/strict');
const path = require('node:path');
const fs = require('node:fs/promises');
const { chromium } = require('playwright-core');
const { gitFixture } = require('./git-fixture.cjs');
const root = path.resolve(__dirname, '..'), models = path.resolve(root, '../../data/models');
function triangle(size) {
  const document = { asset: { version: '2.0' }, scene: 0, scenes: [{ nodes: [0] }], nodes: [{ name: 'test-lod0', children: [1] }, { name: 'triangle', mesh: 0 }], meshes: [{ primitives: [{ attributes: { POSITION: 0 } }] }], buffers: [{ byteLength: 36 }], bufferViews: [{ buffer: 0, byteLength: 36 }], accessors: [{ bufferView: 0, componentType: 5126, count: 3, type: 'VEC3', min: [0, 0, 0], max: [size, size, 0] }] };
  const raw = JSON.stringify(document), json = Buffer.from(raw.padEnd(Math.ceil(raw.length / 4) * 4));
  const file = Buffer.alloc(28 + json.length + 36); file.writeUInt32LE(0x46546c67); file.writeUInt32LE(2, 4); file.writeUInt32LE(file.length, 8); file.writeUInt32LE(json.length, 12); file.writeUInt32LE(0x4e4f534a, 16); json.copy(file, 20); file.writeUInt32LE(36, 20 + json.length); file.writeUInt32LE(0x004e4942, 24 + json.length);
  [0, 0, 0, size, 0, 0, 0, size, 0].forEach((value, i) => file.writeFloatLE(value, 28 + json.length + i * 4)); return file;
}
exports.run = async () => {
  const extension = vscode.extensions.getExtension('megamek-local.megamek-glb-viewer'); assert(extension); await extension.activate();
  assert((await vscode.commands.getCommands()).includes('megamekGlb.open'));
  await vscode.commands.executeCommand('workbench.action.closeAllEditors');
  await vscode.commands.executeCommand('vscode.openWith', vscode.Uri.file(path.join(models, 'buildings/walls/medium/straight.glb')), 'megamek.glb');
  assert(vscode.window.tabGroups.all.flatMap(group => group.tabs).some(tab => tab.input instanceof vscode.TabInputCustom && tab.input.viewType === 'megamek.glb'));
  const browser = await chromium.connectOverCDP(`http://127.0.0.1:${process.env.MM_CDP_PORT}`);
  const fixture = path.join(root, 'test-output/reload-fixture.glb');
  let frame, window, comparison;
  async function findEditor(name, revision) {
    frame = null;
    const until = Date.now() + 45000;
    while (!frame && Date.now() < until) {
      for (const page of browser.contexts().flatMap(c => c.pages())) {
        for (const candidate of page.frames()) {
          try {
            if (await candidate.locator('#filename').count() && (await candidate.locator('#filename').textContent()) === name && (!revision || await candidate.locator('#revision').textContent() === revision) && (await candidate.locator('#status').textContent()).startsWith('Authored GLB')) {
              // A restored editor can still be detaching while the new custom editor opens.
              await candidate.waitForTimeout(300);
              if (candidate.isDetached()) continue;
              frame = candidate; window = page; break;
            }
          } catch { /* Frame is navigating. */ }
        }
        if (frame) break;
      }
      if (!frame) await new Promise(resolve => setTimeout(resolve, 200));
    }
    assert(frame, 'Custom editor webview must exist');
  }
  try {
    await findEditor('straight.glb');
    await frame.waitForFunction(() => document.getElementById('status').textContent.startsWith('Authored GLB'), null, { timeout: 45000 });
    assert.equal(await frame.locator('#filename').textContent(), 'straight.glb');
    assert(await frame.locator('#lodStats tbody tr').count() >= 1);
    await frame.locator('[data-tab="materials"]').click(); assert(await frame.locator('#materialList option').count() > 0);
    await window.screenshot({ path: path.join(root, 'test-output/vscode-webview.png') });
    await frame.locator('[data-tab="test"]').click(); await frame.locator('[data-preset="straight"]').click(); await frame.locator('#test').click();
    await frame.waitForFunction(() => /^(PASS|FAIL):/.test(document.getElementById('engineStatus').textContent), null, { timeout: 45000 });
    assert.match(await frame.locator('#engineStatus').textContent(), /^PASS:/);
    await window.screenshot({ path: path.join(root, 'test-output/vscode-engine-test.png') });
    await fs.writeFile(fixture, triangle(10));
    await vscode.commands.executeCommand('vscode.openWith', vscode.Uri.file(fixture), 'megamek.glb');
    await findEditor('reload-fixture.glb');
    await fs.writeFile(fixture, 'incomplete save');
    await frame.waitForFunction(() => document.getElementById('status').textContent === 'Load failed', null, { timeout: 15000 });
    await fs.writeFile(fixture, triangle(20));
    await frame.waitForFunction(() => document.getElementById('status').textContent.includes('20.0'), null, { timeout: 15000 });
    assert.match(await frame.locator('#status').textContent(), /^Authored GLB/);
    comparison = await gitFixture(path.join(root, 'test-output'));
    await vscode.commands.executeCommand('workbench.action.closeAllEditors');
    const workingUri = vscode.Uri.file(comparison.file), stagedUri = workingUri.with({ scheme: 'git', query: JSON.stringify({ path: comparison.file, ref: '' }) });
    await vscode.commands.executeCommand('vscode.openWith', workingUri, 'megamek.glb'); await findEditor('review.glb', 'Working copy'); const working = frame;
    await vscode.commands.executeCommand('vscode.openWith', stagedUri, 'megamek.glb', { viewColumn: vscode.ViewColumn.Beside }); await findEditor('review.glb', 'Staged'); const staged = frame;
    assert.match(await working.locator('#status').textContent(), /30\.0/); assert.match(await staged.locator('#status').textContent(), /20\.0/);
    for (const [editor, roughness] of [[working, .8], [staged, .4]]) {
      await editor.locator('[data-tab="materials"]').click(); assert.match(await editor.locator('#materialDetail pre').textContent(), new RegExp('"roughness": ' + roughness));
      await editor.locator('[data-tab="view"]').click();
    }
    await working.locator('#lod').selectOption('1'); await staged.waitForFunction(() => document.getElementById('lod').value === '1');
    assert.match(await working.locator('#status').textContent(), /15\.0/); assert.match(await staged.locator('#status').textContent(), /10\.0/);
    await staged.locator('#wire').check(); await working.waitForFunction(() => document.getElementById('wire').checked);
    await staged.locator('#variant').selectOption('snow');
    for (const editor of [working, staged]) await editor.waitForFunction(() => document.getElementById('variant').value === 'snow' && document.getElementById('overlay').textContent === '');
    await comparison.git('add', '.');
    await staged.waitForFunction(() => document.getElementById('status').textContent.includes('15.0'), null, { timeout: 30000 });
    await staged.locator('[data-tab="materials"]').click(); assert.match(await staged.locator('#materialDetail pre').textContent(), /"roughness": 0.8/);
    await working.locator('#inspectorToggle').click(); await staged.locator('#inspectorToggle').click();
    await window.screenshot({ path: path.join(root, 'test-output/vscode-staged-comparison.png') });
    console.log('VS Code PASS: registered editor, real webview/CSP, materials, engine assembly, file watching/recovery, staged versus working geometry/materials, linked LOD/settings and index refresh.');
  } finally { await browser.close(); await vscode.commands.executeCommand('workbench.action.closeAllEditors'); await fs.rm(fixture, { force: true }); await comparison?.dispose(); }
};
