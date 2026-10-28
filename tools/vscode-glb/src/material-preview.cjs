const { readGlb } = require('./assets.cjs');
const { readAttribute } = require('./attributes.cjs');
const { editTargets } = require('./glb-edit.cjs');
const { textureSlots } = require('./surface-edit.cjs');

// Preview the same validated bytes that Ctrl+S saves, without reloading textures or the scene.
function materialPreview(bytes, edit, asset) {
  const { json, binary } = readGlb(bytes);
  const old = asset.metadata.meshes[asset.metadata.nodes[edit.target.node].mesh].primitives[edit.target.primitive];
  const source = asset.surfaces[old.material];
  const surfaces = (json.materials || []).map((gltf, index) => ({ ...(asset.surfaces[index] || source), index, name: gltf.name || `Material ${index}`, gltf }));
  const updates = editTargets(json, edit).map(target => {
    const primitive = json.meshes[json.nodes[target.node].mesh].primitives[target.primitive];
    const update = { ...target, material: primitive.material };
    if (edit.kind === 'placement') {
      const data = readAttribute(json, binary, primitive.attributes.TEXCOORD_0);
      const values = new Float32Array(data.values);
      update.uv = Buffer.from(values.buffer).toString('base64');
    }
    if (edit.kind === 'vertexTint') {
      const index = primitive.attributes.COLOR_0;
      const data = index === undefined ? null : readAttribute(json, binary, index);
      update.color = data && { width: data.width, data: Buffer.from(new Float32Array(data.values).buffer).toString('base64') };
    }
    if (edit.kind === 'sampling') {
      const texture = json.textures[textureSlots(json.materials[primitive.material])[0].index];
      update.sampling = json.samplers[texture.sampler];
    }
    return update;
  });
  return { metadata: json, surfaces, updates };
}
module.exports = { materialPreview };
