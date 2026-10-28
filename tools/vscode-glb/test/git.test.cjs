const { test } = require('node:test');
const assert = require('node:assert/strict');
const path = require('node:path');
const fs = require('node:fs/promises');
const { gitFixture, png } = require('./git-fixture.cjs');
const { gitSource } = require('../src/git-source.cjs');
const { findRoots, loadAsset } = require('../src/assets.cjs');
test('HEAD, staged and working GLBs keep their own meshes, maps, materials and descriptors', async t => {
  const fixture = await gitFixture(path.join(__dirname, '../test-output')); t.after(fixture.dispose);
  for (const [ref, size, roughness, colour] of [['HEAD', 10, .2, [255, 0, 0]], ['', 20, .4, [0, 0, 255]], [null, 30, .8, [0, 255, 0]]]) {
    const snapshot = ref === null ? null : await gitSource(fixture.file, ref);
    const roots = await findRoots(fixture.file, '', [], snapshot?.io);
    const asset = await loadAsset(fixture.file, roots, snapshot?.urlFor, '', snapshot?.io);
    assert.equal(asset.metadata.nodes[0].scale[0], size);
    assert.equal(asset.surfaces[0].managed.roughness, roughness);
    assert.equal(asset.descriptors[0].data.revisionSize, size);
    if (snapshot) assert.equal(asset.document.images[0].uri, `data:image/png;base64,${png(colour).toString('base64')}`);
  }
  const pinned = await gitSource(fixture.file, '');
  assert.equal((await gitSource(fixture.file, '~')).label, 'Staged', 'Working-tree diff originals use the staged version when present');
  await fixture.git('add', '.');
  const asset = await loadAsset(fixture.file, await findRoots(fixture.file, '', [], pinned.io), pinned.urlFor, '', pinned.io);
  assert.equal(asset.metadata.nodes[0].scale[0], 20, 'A load uses one index snapshot even if staging changes midway');
  assert.equal(asset.surfaces[0].managed.roughness, .4);
  await fs.rm(fixture.file);
  const deleted = await gitSource(fixture.file, '');
  assert((await deleted.io.readFile(fixture.file)).length > 0, 'A deleted working file remains viewable from the index');
  await assert.rejects(deleted.io.readFile(path.join(fixture.textures, 'missing.png')), /Not present/, 'Missing staged maps must not fall back to working files');
});
