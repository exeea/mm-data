const fs = require('node:fs/promises');
const path = require('node:path');
const { resolveLocal, materialSpec } = require('./assets.cjs');

async function readLibrary(roots, io = fs) {
  if (!roots.root) return { entries: [], error: 'Choose an mm-data checkout in Settings to load the material palette.' };
  const file = path.join(roots.textures, 'materials.json');
  const catalog = JSON.parse(await io.readFile(file, 'utf8'));
  const entries = [], seen = new Set();
  for (const [category, items] of [['loose', Object.entries(catalog.loose || {})], ['constrained', (catalog.constrained || []).map(id => [id, {}])]]) {
    for (const [id, details] of items) {
      if (typeof id !== 'string' || /[\\:%?#\x00]/.test(id) || id.split('/').some(part => !part || part === '.' || part === '..')) throw Error('Invalid material path in materials.json');
      if (seen.has(id)) throw Error(`Duplicate material in materials.json: ${id}`);
      seen.add(id);
      entries.push({ id, name: id.split('/').at(-1), folder: id.includes('/') ? id.slice(0, id.lastIndexOf('/')) : '', category, pixels: details?.pixels, metres: details?.metres });
    }
  }
  return { file, entries: entries.sort((a, b) => a.id.localeCompare(b.id)) };
}

async function libraryMaterial(entry, roots, urlFor = p => p, io = fs) {
  const dependencies = new Set();
  const file = await resolveLocal(roots.textures, entry.id + '.tres', [roots.textures], dependencies, io);
  const spec = await materialSpec(file, roots, (p, stamp) => p.endsWith('_albedo.png') ? urlFor(p, stamp) : '', dependencies, io);
  if (spec.maps.albedo?.file !== path.join(roots.textures, entry.id + '_albedo.png')) throw Error('Material must use its adjacent _albedo.png for engine lookup');
  return { ...entry, spec, dependencies: [...dependencies] };
}
module.exports = { readLibrary, libraryMaterial };
