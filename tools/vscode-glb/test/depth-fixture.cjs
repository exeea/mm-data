// Two planes only .01 units apart: both must remain distinct at a normal board-asset scale.
// Draw the rear red plane after the front green one to expose quantized depth ties.
function depthFixture() {
  const values = [];
  for (const y of [.01, 0]) values.push(-50, y, -50, -50, y, 50, 50, y, 50, -50, y, -50, 50, y, 50, 50, y, -50);
  const binary = Buffer.alloc(values.length * 4); values.forEach((v, i) => binary.writeFloatLE(v, i * 4));
  const document = { asset: { version: '2.0' }, extensionsUsed: ['KHR_materials_unlit'], scene: 0, scenes: [{ nodes: [0] }],
    nodes: [{ name: 'depth-lod0', children: [1, 2] }, { name: 'front', mesh: 0 }, { name: 'rear', mesh: 1 }],
    meshes: [0, 1].map(i => ({ primitives: [{ attributes: { POSITION: i }, material: i }] })),
    materials: [[0, 1, 0, 1], [1, 0, 0, 1]].map(color => ({ pbrMetallicRoughness: { baseColorFactor: color }, extensions: { KHR_materials_unlit: {} } })),
    buffers: [{ byteLength: binary.length }], bufferViews: [0, 1].map(i => ({ buffer: 0, byteOffset: i * 72, byteLength: 72 })),
    accessors: [.01, 0].map((y, i) => ({ bufferView: i, componentType: 5126, count: 6, type: 'VEC3', min: [-50, y, -50], max: [50, y, 50] })) };
  const raw = JSON.stringify(document), json = Buffer.from(raw.padEnd(Math.ceil(raw.length / 4) * 4));
  const file = Buffer.alloc(28 + json.length + binary.length); file.writeUInt32LE(0x46546c67); file.writeUInt32LE(2, 4); file.writeUInt32LE(file.length, 8); file.writeUInt32LE(json.length, 12); file.writeUInt32LE(0x4e4f534a, 16); json.copy(file, 20); file.writeUInt32LE(binary.length, 20 + json.length); file.writeUInt32LE(0x004e4942, 24 + json.length); binary.copy(file, 28 + json.length);
  return file;
}
module.exports = { depthFixture };
