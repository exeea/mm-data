// Decode authored vertex attributes without changing their shared/interleaved source buffers.
const components = { 5120: [1, 'readInt8', 127], 5121: [1, 'readUInt8', 255], 5122: [2, 'readInt16LE', 32767], 5123: [2, 'readUInt16LE', 65535], 5125: [4, 'readUInt32LE', 4294967295], 5126: [4, 'readFloatLE', 1] };
function readAttribute(json, binary, index) {
  const accessor = json.accessors?.[index], width = { SCALAR: 1, VEC2: 2, VEC3: 3, VEC4: 4 }[accessor?.type];
  if (!accessor || !width || !components[accessor.componentType] || !Number.isSafeInteger(accessor.count) || accessor.count < 0 || accessor.count > 50_000_000) throw Error('Unsupported vertex accessor');
  const read = (viewIndex, offset, count, size, type, normalized = false) => {
    const view = json.bufferViews?.[viewIndex], format = components[type];
    if (!view || view.buffer !== 0 || !binary || json.buffers?.[0]?.uri || view.extensions?.EXT_meshopt_compression || !format) throw Error('Material placement requires uncompressed vertex data embedded in the GLB');
    const [bytes, method, maximum] = format, stride = view.byteStride || bytes * size, start = (view.byteOffset || 0) + offset;
    if (!Number.isSafeInteger(offset) || offset < 0 || !Number.isSafeInteger(start) || start < 0 || stride < bytes * size || count && (offset + (count - 1) * stride + bytes * size > view.byteLength || start + (count - 1) * stride + bytes * size > binary.length)) throw Error('Vertex accessor exceeds its buffer');
    const values = type === 5125 && !normalized ? new Float64Array(count * size) : new Float32Array(count * size);
    for (let i = 0; i < count; i++) for (let c = 0; c < size; c++) {
      let value = binary[method](start + i * stride + c * bytes);
      if (normalized && type !== 5126) value = Math.max(-1, value / maximum);
      if (!Number.isFinite(value)) throw Error('Non-finite vertex data');
      values[i * size + c] = value;
    }
    return values;
  };
  const values = accessor.bufferView === undefined ? new Float32Array(accessor.count * width) : read(accessor.bufferView, accessor.byteOffset || 0, accessor.count, width, accessor.componentType, accessor.normalized);
  if (accessor.sparse) {
    const sparse = accessor.sparse;
    if (!Number.isSafeInteger(sparse.count) || sparse.count < 0 || sparse.count > accessor.count || ![5121, 5123, 5125].includes(sparse.indices.componentType)) throw Error('Invalid sparse vertex accessor');
    const targets = read(sparse.indices.bufferView, sparse.indices.byteOffset || 0, sparse.count, 1, sparse.indices.componentType);
    const replacements = read(sparse.values.bufferView, sparse.values.byteOffset || 0, sparse.count, width, accessor.componentType, accessor.normalized);
    for (let i = 0; i < sparse.count; i++) { if (targets[i] >= accessor.count) throw Error('Sparse vertex outside accessor'); values.set(replacements.subarray(i * width, (i + 1) * width), targets[i] * width); }
  }
  return { values, width, count: accessor.count };
}

function attributeWriter(json, binary) {
  const chunks = [binary], cache = new Map(); let length = binary.length;
  return {
    append(data, cacheKey) {
      if (cache.has(cacheKey)) return cache.get(cacheKey);
      const { values, width, count } = data, buffer = Buffer.alloc(values.length * 4), min = Array(width).fill(Infinity), max = Array(width).fill(-Infinity);
      values.forEach((value, i) => { if (!Number.isFinite(Math.fround(value))) throw Error('Material adjustment exceeds the UV/colour range'); buffer.writeFloatLE(value, i * 4); min[i % width] = Math.min(min[i % width], value); max[i % width] = Math.max(max[i % width], value); });
      const padding = (4 - length % 4) % 4; if (padding) { chunks.push(Buffer.alloc(padding)); length += padding; }
      const view = json.bufferViews.length; json.bufferViews.push({ buffer: 0, byteOffset: length, byteLength: buffer.length, target: 34962 }); chunks.push(buffer); length += buffer.length;
      const index = json.accessors.length; json.accessors.push({ bufferView: view, componentType: 5126, count, type: `VEC${width}`, ...(count ? { min, max } : {}) });
      cache.set(cacheKey, index); return index;
    },
    finish() { if (chunks.length > 1) json.buffers[0].byteLength = length; return Buffer.concat(chunks); }
  };
}
module.exports = { readAttribute, attributeWriter };
