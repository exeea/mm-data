const { readAttribute, attributeWriter } = require('./attributes.cjs');
const { indices } = require('./stats.cjs');

function textureSlots(material) {
  return [material.pbrMetallicRoughness?.baseColorTexture, material.pbrMetallicRoughness?.metallicRoughnessTexture, material.normalTexture, material.occlusionTexture, material.emissiveTexture].filter(Boolean);
}
function sampling(json, material, value) {
  if (!value || Object.keys(value).some(key => !['wrapS', 'wrapT', 'minFilter', 'magFilter'].includes(key)) || ![33071, 33648, 10497].includes(value.wrapS) || ![33071, 33648, 10497].includes(value.wrapT) || ![9728, 9729, 9984, 9985, 9986, 9987].includes(value.minFilter) || ![9728, 9729].includes(value.magFilter)) throw Error('Invalid texture sampling settings');
  const slots = textureSlots(material); if (!slots.length) throw Error('This material has no textures to adjust');
  const samplers = json.samplers ||= [], textures = json.textures || [], replacements = new Map();
  for (const slot of slots) {
    const original = textures[slot.index]; if (!original) throw Error('Invalid material texture');
    if (!replacements.has(slot.index)) {
      const next = { ...samplers[original.sampler], ...value }; let sampler = samplers.findIndex(item => JSON.stringify(item) === JSON.stringify(next));
      if (sampler < 0) { sampler = samplers.length; samplers.push(next); }
      const texture = { ...original, sampler }; let index = textures.findIndex(item => JSON.stringify(item) === JSON.stringify(texture));
      if (index < 0) { index = textures.length; textures.push(texture); } replacements.set(slot.index, index);
    }
    slot.index = replacements.get(slot.index);
  }
}
function usedVertices(json, binary, primitive, count) {
  const used = primitive.indices === undefined ? Array.from({ length: count }, (_, i) => i) : [...new Set(indices(json, binary, primitive.indices))];
  if (used.some(i => i >= count)) throw Error('Vertex index outside attribute'); return used;
}
function mapping(value) {
  for (const key of ['offset', 'scale', 'pivot']) if (!Array.isArray(value?.[key]) || value[key].length !== 2 || !value[key].every(n => typeof n === 'number' && Number.isFinite(n) && Math.abs(n) <= 100000)) throw Error(`Invalid UV ${key}`);
  if (value.scale.some(n => Math.abs(n) < .00001) || !Number.isFinite(value.rotation) || Math.abs(value.rotation) > 36000) throw Error('UV scale must be non-zero and rotation finite');
  return { offset: value.offset, scale: value.scale, pivot: value.pivot, rotation: value.rotation };
}
function editAttributes(json, binary, targets, edit) {
  if (!binary || !json.buffers?.[0] || json.buffers[0].uri) throw Error('Material placement requires embedded GLB vertex data');
  const writer = attributeWriter(json, binary), visited = new Set();
  let painted = false;
  for (const { node, primitive: pi } of targets) {
    const mesh = json.nodes[node].mesh, key = `${mesh}:${pi}`; if (visited.has(key)) continue; visited.add(key);
    const primitive = json.meshes[mesh].primitives[pi], material = json.materials?.[primitive.material] || {}, attributes = primitive.attributes;
    if (primitive.extensions?.KHR_draco_mesh_compression) throw Error('Decompress this surface in Blender before editing UVs or vertex paint');
    const count = json.accessors[attributes.POSITION]?.count;
    if (edit.kind === 'placement') {
      if (material.extras?.mmLabel) throw Error('Label atlas UVs are controlled by the label tool');
      for (const slot of textureSlots(material)) if (slot.texCoord > 0 || slot.extensions?.KHR_texture_transform) throw Error('Bake texture transforms and extra UV sets in Blender before editing placement');
      const previous = primitive.extras?.mmTexturePlacement;
      const source = previous?.source ?? attributes.TEXCOORD_0, tangent = previous ? previous.tangent : attributes.TANGENT;
      if (!Number.isInteger(source)) throw Error('This surface has no UVs. Unwrap it in Blender first.');
      const data = readAttribute(json, binary, source);
      if (data.width !== 2 || data.count !== count) throw Error('UVs must match the surface vertices');
      if (edit.reset) {
        attributes.TEXCOORD_0 = source;
        if (Number.isInteger(tangent)) attributes.TANGENT = tangent;
        if (primitive.extras) delete primitive.extras.mmTexturePlacement;
        continue;
      }
      let value = mapping(edit.mapping);
      if (edit.fit) {
        const min = [Infinity, Infinity], max = [-Infinity, -Infinity];
        for (const i of usedVertices(json, binary, primitive, count)) for (let c = 0; c < 2; c++) { min[c] = Math.min(min[c], data.values[i * 2 + c]); max[c] = Math.max(max[c], data.values[i * 2 + c]); }
        if (!min.every(Number.isFinite)) throw Error('Surface has no UV vertices');
        const scale = max.map((n, c) => n - min[c] > 1e-8 ? 1 / (n - min[c]) : 1);
        value = mapping({ offset: min.map((n, c) => -n * scale[c]), scale, pivot: [0, 0], rotation: 0 });
      }
      const radians = value.rotation * Math.PI / 180, cos = Math.cos(radians), sin = Math.sin(radians);
      for (let i = 0; i < count; i++) {
        const u = (data.values[i * 2] - value.pivot[0]) * value.scale[0], v = (data.values[i * 2 + 1] - value.pivot[1]) * value.scale[1];
        data.values[i * 2] = cos * u - sin * v + value.pivot[0] + value.offset[0]; data.values[i * 2 + 1] = sin * u + cos * v + value.pivot[1] + value.offset[1];
      }
      attributes.TEXCOORD_0 = writer.append(data, `uv:${source}:${JSON.stringify(value)}`);
      // Tangents derived from the previous UVs are stale; loaders derive the new basis from the baked UVs.
      delete attributes.TANGENT;
      (primitive.extras ||= {}).mmTexturePlacement = { source, ...(tangent === undefined ? {} : { tangent }), ...value };
    } else if (edit.kind === 'vertexTint') {
      const original = primitive.extras?.mmVertexPaint ? primitive.extras.mmVertexPaint.source : attributes.COLOR_0 ?? null;
      if (edit.mode === 'restore') {
        if (primitive.extras?.mmVertexPaint) { const source = primitive.extras.mmVertexPaint.source; if (source === null) delete attributes.COLOR_0; else attributes.COLOR_0 = source; delete primitive.extras.mmVertexPaint; }
        continue;
      }
      if (!['recolour', 'solid', 'white'].includes(edit.mode) || !Array.isArray(edit.color) || edit.color.length !== 3 || !edit.color.every(n => typeof n === 'number' && Number.isFinite(n) && n >= 0 && n <= 1)) throw Error('Invalid vertex paint');
      const match = edit.match;
      if (match && (!Array.isArray(match.color) || match.color.length !== 3 || !match.color.every(n => Number.isFinite(n) && n >= 0 && n <= 1) || !Number.isFinite(match.tolerance) || match.tolerance < 0 || match.tolerance > 2)) throw Error('Invalid paint colour match');
      const source = attributes.COLOR_0, data = source === undefined ? { width: 4, count, values: new Float32Array(count * 4).fill(1) } : readAttribute(json, binary, source);
      if (![3, 4].includes(data.width) || data.count !== count) throw Error('Vertex colours must match the surface vertices');
      // Match and shade from the authored paint, so changing its hue never loses the selected group.
      // Write into the current colours to retain edits to other authored groups.
      const reference = original === source ? data : original === null ? { width: 4, count, values: new Float32Array(count * 4).fill(1) } : readAttribute(json, binary, original);
      if (![3, 4].includes(reference.width) || reference.count !== count) throw Error('Original vertex colours must match the surface vertices');
      const unit = rgb => { const peak = Math.max(...rgb, .000001); return rgb.map(n => n / peak); }, wanted = match && unit(match.color);
      const used = usedVertices(json, binary, primitive, count).filter(i => !wanted || Math.hypot(...unit(Array.from(reference.values.subarray(i * reference.width, i * reference.width + 3))).map((n, c) => n - wanted[c])) <= match.tolerance);
      if (!used.length) continue;
      painted = true;
      const peak = used.reduce((n, i) => Math.max(n, ...reference.values.subarray(i * reference.width, i * reference.width + 3)), .000001);
      for (const i of used) {
        const shade = edit.mode === 'recolour' ? Math.max(...reference.values.subarray(i * reference.width, i * reference.width + 3)) / peak : 1;
        for (let c = 0; c < 3; c++) data.values[i * data.width + c] = edit.mode === 'white' ? 1 : edit.color[c] * shade;
      }
      attributes.COLOR_0 = writer.append(data, `paint:${mesh}:${pi}`); (primitive.extras ||= {}).mmVertexPaint = { source: original };
    }
  }
  if (edit.kind === 'vertexTint' && edit.mode !== 'restore' && !painted) throw Error('No vertex colours match. Increase the tolerance or choose another paint swatch.');
  return writer.finish();
}
module.exports = { editAttributes, sampling, textureSlots };
