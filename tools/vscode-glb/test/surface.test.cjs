const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
const { readGlb, loadAsset, findRoots } = require('../src/assets.cjs');
const { editGlb, writeGlb, rebaseGlb } = require('../src/glb-edit.cjs');
const { readAttribute } = require('../src/attributes.cjs');
const { indices } = require('../src/stats.cjs');
const { preview, findEngine } = require('../src/engine.cjs');
const { png } = require('./git-fixture.cjs');
const { GlbDocument } = require('../src/document.cjs');
const { materialPreview } = require('../src/material-preview.cjs');
const output = path.resolve(__dirname, '../test-output'), root = path.resolve(__dirname, '../../..');
function fixture() {
  const image = png([255, 0, 0]), binary = Buffer.alloc(Math.ceil((236 + image.length) / 4) * 4);
  [0, 0, 0, 1, 0, 0, 1, 1, 0, 0, 1, 0].forEach((n, i) => binary.writeFloatLE(n, i * 4));
  for (let i = 0; i < 4; i++) { binary.writeFloatLE(1, 48 + i * 12 + 8); binary.writeFloatLE(1, 172 + i * 16); binary.writeFloatLE(1, 172 + i * 16 + 12); }
  [[0, 0], [65535, 0], [65535, 65535], [0, 65535]].forEach((uv, i) => uv.forEach((n, c) => binary.writeUInt16LE(n, 96 + i * 8 + c * 2)));
  [[255, 40, 20, 255], [128, 20, 10, 128], [20, 30, 255, 64], [200, 200, 200, 255]].forEach((rgb, i) => rgb.forEach((n, c) => binary.writeUInt8(n, 128 + i * 8 + c)));
  [0, 1, 2, 1, 2, 3].forEach((n, i) => binary.writeUInt16LE(n, 160 + i * 2)); image.copy(binary, 236);
  const json = { asset: { version: '2.0' }, scene: 0, scenes: [{ nodes: [0, 1] }], nodes: [{ name: 'first', mesh: 0 }, { name: 'second', mesh: 0 }],
    meshes: [{ name: 'mesh', primitives: [0, 1].map(i => ({ attributes: { POSITION: 0, NORMAL: 1, TEXCOORD_0: 2, COLOR_0: 3, TANGENT: 6 }, indices: 4 + i, material: i })) }],
    materials: ['paint', 'other'].map(name => ({ name, pbrMetallicRoughness: { baseColorTexture: { index: 0 } }, normalTexture: { index: 0 } })),
    images: [{ bufferView: 7, mimeType: 'image/png' }], textures: [{ source: 0, sampler: 0 }], samplers: [{ wrapS: 10497, wrapT: 10497, minFilter: 9987, magFilter: 9729 }],
    buffers: [{ byteLength: binary.length }], bufferViews: [[0, 48, 12], [48, 48, 12], [96, 32, 8], [128, 32, 8], [160, 6], [166, 6], [172, 64, 16], [236, image.length]].map(([byteOffset, byteLength, byteStride]) => ({ buffer: 0, byteOffset, byteLength, ...(byteStride ? { byteStride } : {}) })),
    accessors: [['VEC3', 5126, 4], ['VEC3', 5126, 4], ['VEC2', 5123, 4, true], ['VEC4', 5121, 4, true], ['SCALAR', 5123, 3], ['SCALAR', 5123, 3], ['VEC4', 5126, 4]].map(([type, componentType, count, normalized], bufferView) => ({ bufferView, type, componentType, count, ...(normalized ? { normalized } : {}) })) };
  const raw = Buffer.from(JSON.stringify(json)), text = Buffer.alloc(Math.ceil(raw.length / 4) * 4, 32); raw.copy(text);
  const bytes = Buffer.alloc(28 + text.length + binary.length); bytes.writeUInt32LE(0x46546c67); bytes.writeUInt32LE(2, 4); bytes.writeUInt32LE(bytes.length, 8); bytes.writeUInt32LE(text.length, 12); bytes.writeUInt32LE(0x4e4f534a, 16); text.copy(bytes, 20); bytes.writeUInt32LE(binary.length, 20 + text.length); bytes.writeUInt32LE(0x004e4942, 24 + text.length); binary.copy(bytes, 28 + text.length);
  return bytes;
}
const target = { node: 0, primitive: 0 }, mapping = { offset: [.25, -.5], scale: [2, .5], pivot: [.5, .5], rotation: 90 };
const selected = json => json.meshes[json.nodes[0].mesh].primitives[0];
const close = (a, b) => assert(Math.abs(a - b) < 1e-6, `${a} ≠ ${b}`);
test('UV placement bakes normalized/interleaved data, isolates instances, keeps original bytes, and resets exactly', () => {
  const bytes = fixture(), before = readGlb(bytes), edited = editGlb(bytes, { kind: 'placement', target, scope: 'surface', mapping }, 'test.glb'), after = readGlb(edited), primitive = selected(after.json);
  assert.notEqual(after.json.nodes[0].mesh, after.json.nodes[1].mesh); assert.equal(after.json.meshes[0].primitives[0].attributes.TEXCOORD_0, 2);
  assert.deepEqual(after.binary.subarray(0, before.binary.length), before.binary);
  assert.deepEqual(after.json.images, before.json.images); assert.deepEqual(after.json.materials, before.json.materials);
  assert.equal(primitive.attributes.POSITION, 0); assert.equal(primitive.attributes.NORMAL, 1); assert.equal(primitive.attributes.COLOR_0, 3); assert.equal(primitive.attributes.TANGENT, undefined);
  const uv = readAttribute(after.json, after.binary, primitive.attributes.TEXCOORD_0).values;
  close(uv[0], 1); close(uv[1], -1); close(uv[4], .5); close(uv[5], 1);
  const twice = readGlb(editGlb(edited, { kind: 'placement', target, scope: 'surface', mapping }, 'test.glb'));
  assert.deepEqual(readAttribute(twice.json, twice.binary, selected(twice.json).attributes.TEXCOORD_0).values, uv, 'Placement is absolute, not compounded on each Apply');
  const reset = readGlb(editGlb(edited, { kind: 'placement', target, scope: 'surface', reset: true }, 'test.glb'));
  assert.equal(selected(reset.json).attributes.TEXCOORD_0, 2); assert.equal(selected(reset.json).attributes.TANGENT, 6); assert.equal(selected(reset.json).extras.mmTexturePlacement, undefined);
});
test('paint matching preserves other colours, alpha, gradients, and the original paint for reset', () => {
  const bytes = fixture(), before = readGlb(bytes), action = { kind: 'vertexTint', target, scope: 'surface', mode: 'recolour', color: [0, 1, 0], match: { color: [1, 40 / 255, 20 / 255], tolerance: .01 } };
  const edited = editGlb(bytes, action, 'test.glb'), after = readGlb(edited), result = readAttribute(after.json, after.binary, selected(after.json).attributes.COLOR_0).values, original = readAttribute(before.json, before.binary, 3).values;
  close(result[0], 0); close(result[1], 1); close(result[5], 128 / 255); close(result[7], 128 / 255);
  assert.deepEqual(result.subarray(8), original.subarray(8)); assert.deepEqual(after.binary.subarray(0, before.binary.length), before.binary);
  const reset = readGlb(editGlb(edited, { kind: 'vertexTint', target, scope: 'surface', mode: 'restore' }, 'test.glb')); assert.equal(selected(reset.json).attributes.COLOR_0, 3);
  delete selected(before.json).attributes.COLOR_0;
  let blank = writeGlb(bytes, before.json);
  for (const mode of ['solid', 'white']) blank = editGlb(blank, { kind: 'vertexTint', target, scope: 'surface', mode, color: [.3, .4, .5] }, 'test.glb');
  const restored = readGlb(editGlb(blank, { kind: 'vertexTint', target, scope: 'surface', mode: 'restore' }, 'test.glb')); assert.equal(selected(restored.json).attributes.COLOR_0, undefined);
});

test('live paint keeps authored matches across gestures, save/reopen, black/white and other paint groups', async t => {
  await fs.mkdir(output, { recursive: true }); const dir = await fs.mkdtemp(path.join(output, 'live-paint-'));
  t.after(async () => { assert.equal(path.dirname(dir), output); await fs.rm(dir, { recursive: true, force: true }); });
  const file = path.join(dir, 'paint.glb'), bytes = fixture(), before = readGlb(bytes);
  await fs.writeFile(file, bytes);
  let model = new GlbDocument(file, bytes);
  const action = { kind: 'vertexTint', target, scope: 'surface', mode: 'recolour', color: [0, 1, 0], match: { color: [1, 40 / 255, 20 / 255], tolerance: .01 } };
  let started = 0, event;
  for (let i = 1; i <= 40; i++) {
    action.color = [0, i / 40, 0];
    const result = model.edit(action, { group: 'paint' });
    if (result.started) { started++; event = result.change; }
  }
  assert.equal(started, 1); assert.deepEqual(event.before, bytes);
  assert.deepEqual(model.bytes, editGlb(bytes, action, file), 'Continuous preview stores only the final colour attribute');
  const colors = () => { const { json, binary } = readGlb(model.bytes); return readAttribute(json, binary, selected(json).attributes.COLOR_0).values; };
  const original = readAttribute(before.json, before.binary, 3).values;
  // Widen then narrow within one adjustment: previously matched vertices must revert.
  model.edit({ ...action, match: { ...action.match, tolerance: 2 } }, { group: 'paint' });
  model.edit(action, { group: 'paint' }); assert.deepEqual(colors().subarray(8), original.subarray(8));
  const valid = model.bytes;
  assert.throws(() => model.edit({ ...action, match: { color: [1, 1, 1], tolerance: 0 } }, { group: 'paint' }), /No vertex colours match/);
  assert.strictEqual(model.bytes, valid);
  const asset = { metadata: before.json, surfaces: before.json.materials.map((gltf, index) => ({ gltf, index })) };
  const update = materialPreview(model.bytes, action, asset);
  assert.equal(update.updates.length, 1); assert.equal(update.updates[0].color.width, 4);
  assert.deepEqual(Buffer.from(update.updates[0].color.data, 'base64'), Buffer.from(colors().buffer));
  await model.save(); assert.deepEqual(await fs.readFile(file), valid);
  model = new GlbDocument(file, await fs.readFile(file));
  for (const mode of ['solid', 'white', 'recolour']) {
    model.edit({ ...action, mode, color: [0, 0, 0] }, { group: mode });
  }
  model.endEdit(); model.edit({ ...action, color: [0, 0, 1] }, { group: 'blue' });
  close(colors()[2], 1); close(colors()[6], 128 / 255); close(colors()[7], 128 / 255);
  const blueGroup = { ...action, color: [1, 1, 0], match: { color: [20 / 255, 30 / 255, 1], tolerance: .01 } };
  model.edit(blueGroup, { group: 'second-group' });
  const otherPaint = colors().slice(8);
  model.edit(action, { group: 'first-group-again' });
  assert.deepEqual(colors().subarray(8), otherPaint, 'Changing one authored paint must preserve edits to another');
  close(colors()[1], 1); close(colors()[5], 128 / 255);
  for (const i of [3, 7, 11, 15]) close(colors()[i], original[i]);
  assert.equal(readGlb(model.bytes).json.nodes[1].mesh, before.json.nodes[1].mesh);
  model.edit({ ...action, mode: 'restore' }); assert.equal(selected(readGlb(model.bytes).json).attributes.COLOR_0, 3);
});
test('sampling changes follow every material map without leaking through shared texture/sampler records', () => {
  const bytes = fixture(), before = readGlb(bytes), edited = editGlb(bytes, { kind: 'sampling', target, scope: 'surface', sampling: { wrapS: 33648, wrapT: 33071, minFilter: 9728, magFilter: 9728 } }, 'test.glb'), after = readGlb(edited);
  const material = after.json.materials[selected(after.json).material], index = material.pbrMetallicRoughness.baseColorTexture.index;
  assert.equal(index, material.normalTexture.index); assert.notEqual(index, 0); assert.equal(after.json.samplers[after.json.textures[index].sampler].wrapS, 33648);
  assert.deepEqual(after.json.textures[0], before.json.textures[0]); assert.deepEqual(after.json.samplers[0], before.json.samplers[0]); assert.deepEqual(after.binary, before.binary);
  const defaults = { kind: 'sampling', target, scope: 'surface', sampling: before.json.samplers[0] };
  assert.strictEqual(editGlb(bytes, defaults, 'test.glb'), bytes, 'Unchanged sampling must not clone a material');
  const model = new GlbDocument('test.glb', bytes), action = { ...defaults, sampling: { wrapS: 33648, wrapT: 33071, minFilter: 9728, magFilter: 9728 } };
  let events = 0;
  for (const minFilter of [9984, 9985, 9986, 9987, 9728, 9729]) {
    action.sampling.minFilter = minFilter;
    if (model.edit(action, { group: 'sampling' }).started) events++;
  }
  assert.equal(events, 1); assert.deepEqual(model.bytes, editGlb(bytes, action, 'test.glb'), 'Live sampler changes retain only the current adjustment');
  const asset = { metadata: before.json, surfaces: before.json.materials.map((gltf, index) => ({ gltf, index })) };
  const update = materialPreview(model.bytes, action, asset);
  assert.equal(update.updates.length, 1); assert.deepEqual(update.updates[0].sampling, action.sampling);
  const allAction = { ...action, scope: 'material' }, allBytes = editGlb(bytes, allAction, 'test.glb'), all = readGlb(allBytes);
  assert.deepEqual(all.json.nodes, before.json.nodes); assert.equal(all.json.materials.length, before.json.materials.length);
  assert.deepEqual(all.json.images, before.json.images); assert.deepEqual(all.binary, before.binary, 'Embedded texture bytes remain unchanged');
  const allUpdates = materialPreview(allBytes, allAction, asset).updates;
  assert.equal(allUpdates.length, 2); for (const item of allUpdates) assert.deepEqual(item.sampling, action.sampling);
  const valid = model.bytes;
  assert.throws(() => model.edit({ ...action, sampling: { ...action.sampling, magFilter: 9987 } }, { group: 'sampling' }), /Invalid texture sampling/);
  assert.strictEqual(model.bytes, valid);
  assert.throws(() => editGlb(bytes, { kind: 'placement', target, scope: 'surface', mapping: { ...mapping, scale: [0, 1] } }, 'test.glb'), /scale/);
  const json = before.json; json.materials[0].pbrMetallicRoughness.baseColorTexture.extensions = { KHR_texture_transform: { offset: [.2, .1] } };
  assert.throws(() => editGlb(writeGlb(bytes, json), { kind: 'placement', target, scope: 'surface', mapping }, 'test.glb'), /Bake texture transforms/);
});
test('sparse attributes and whole-material placement retain counts and shared-node identity', () => {
  const bytes = fixture(), before = readGlb(bytes), uv = before.json.accessors[2];
  delete uv.bufferView; delete uv.normalized; uv.componentType = 5126;
  uv.sparse = { count: 3, indices: { bufferView: 4, componentType: 5123 }, values: { bufferView: 6 } };
  const decoded = readAttribute(before.json, before.binary, 2); assert.equal(decoded.values.length, 8); close(decoded.values[0], 1); close(decoded.values[6], 0);
  const after = readGlb(editGlb(bytes, { kind: 'placement', target, scope: 'material', mapping }, 'test.glb'));
  assert.equal(after.json.nodes[0].mesh, after.json.nodes[1].mesh); assert.equal(after.json.meshes.length, 1);
  assert.equal(selected(after.json).attributes.POSITION, selected(readGlb(bytes).json).attributes.POSITION);
});
test('edited fuel-tank UVs and selectively recoloured paint save, reopen, and load through the real engine', async t => {
  const file = path.join(root, 'data/models/buildings/fuel_tanks/fuel_tank_light.glb'), original = await fs.readFile(file), before = readGlb(original);
  const ni = before.json.nodes.findIndex(n => before.json.meshes?.[n.mesh]?.primitives.some(p => before.json.materials[p.material].name === 'paint'));
  const pi = before.json.meshes[before.json.nodes[ni].mesh].primitives.findIndex(p => before.json.materials[p.material].name === 'paint'), target = { node: ni, primitive: pi };
  let bytes = editGlb(original, { kind: 'placement', target, scope: 'surface', mapping }, file);
  const linear = n => n <= .04045 ? n / 12.92 : ((n + .055) / 1.055) ** 2.4;
  bytes = editGlb(bytes, { kind: 'vertexTint', target, scope: 'material', mode: 'recolour', color: [.02, .2, .8], match: { color: [.87, .29, .24].map(linear), tolerance: .15 } }, file);
  const after = readGlb(bytes), p = after.json.meshes[after.json.nodes[ni].mesh].primitives[pi], old = before.json.meshes[before.json.nodes[ni].mesh].primitives[pi];
  assert.equal(p.attributes.POSITION, old.attributes.POSITION); assert.equal(p.indices, old.indices); assert.deepEqual(after.binary.subarray(0, before.binary.length), before.binary);
  const colors = readAttribute(after.json, after.binary, p.attributes.COLOR_0), oldColors = readAttribute(before.json, before.binary, old.attributes.COLOR_0), used = indices(before.json, before.binary, old.indices);
  assert(used.some(i => Math.abs(colors.values[i * 4] - oldColors.values[i * 4]) > .1)); assert(used.some(i => colors.values[i * 4] === oldColors.values[i * 4]));
  const paintParts = before.json.nodes.flatMap((node, ni) => (before.json.meshes?.[node.mesh]?.primitives || []).flatMap((part, pi) => part.material === old.material ? [{ before: part, after: after.json.meshes[after.json.nodes[ni].mesh].primitives[pi] }] : []));
  assert(paintParts.some(part => part.before.attributes.COLOR_0 === part.after.attributes.COLOR_0), 'Parts without matching paint remain untouched');
  assert(paintParts.filter(part => part.before.attributes.COLOR_0 !== part.after.attributes.COLOR_0).length > 1, 'Matching paint updates across LODs and parts');
  await fs.mkdir(output, { recursive: true }); const dir = await fs.mkdtemp(path.join(output, 'placement-')); t.after(async () => { assert.equal(path.dirname(dir), output); await fs.rm(dir, { recursive: true, force: true }); });
  const saved = path.join(dir, 'fuel-tank.glb'); await fs.writeFile(saved, rebaseGlb(bytes, file, saved));
  const loaded = await loadAsset(saved, await findRoots(saved, root)); assert.equal(loaded.statistics.rows[0].triangles, (await loadAsset(file, await findRoots(file))).statistics.rows[0].triangles);
  const engine = await findEngine('', root); assert(engine, 'Engine integration needs the sibling MegaMek checkout');
  const result = await preview(engine, { model: saved, modelsRoot: path.join(root, 'data/models'), kind: 'RIGID', lod: 0, height: 1, reach: [0, 0, 0, 0, 0, 0], rotation: 0, seed: 0 }); assert(result.ok);
});
