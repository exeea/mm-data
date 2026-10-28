const fs = require('node:fs/promises');
const path = require('node:path');
const { execFile } = require('node:child_process');
const { promisify } = require('node:util');
const { inside } = require('./assets.cjs');
const execute = promisify(execFile);
const key = file => process.platform === 'win32' ? path.resolve(file).toLowerCase() : path.resolve(file);

// Capture blob IDs once per load. Staging during image loading cannot mix two versions, and no Git state is written.
async function gitSource(file, requestedRef, git = 'git') {
  let directory = path.dirname(file);
  while (!(await fs.stat(directory).catch(() => null))?.isDirectory()) {
    const parent = path.dirname(directory); if (parent === directory) throw Error('Cannot locate this GLB’s checkout'); directory = parent;
  }
  const run = async (args, cwd = directory) => (await execute(git, ['-C', cwd, ...args], { encoding: 'buffer', maxBuffer: 256 * 1024 * 1024, windowsHide: true })).stdout;
  const root = (await run(['rev-parse', '--show-toplevel'])).toString('utf8').trim();
  if (!inside(root, file)) throw Error('Git GLB leaves its checkout');
  let ref = requestedRef;
  if (ref === '~') ref = (await run(['diff', '--cached', '--name-only', '-z', '--', file])).length ? '' : 'HEAD';
  if (/^~[123]$/.test(ref)) ref = ':' + ref[1];
  const index = ref === '' || /^:[123]$/.test(ref), stage = ref === '' ? '0' : ref.slice(1);
  const tree = index ? null : (await run(['rev-parse', '--verify', '--end-of-options', ref + '^{tree}'])).toString('utf8').trim();
  const listing = (await run(index ? ['ls-files', '--stage', '-z'] : ['ls-tree', '-r', '-z', tree], root)).toString('utf8');
  const entries = new Map(), blobs = new Map();
  for (const line of listing.split('\0').filter(Boolean)) {
    const match = line.match(index ? /^(\d{6}) ([a-f0-9]+) ([0-3])\t([\s\S]+)$/ : /^(\d{6}) blob ([a-f0-9]+)\t([\s\S]+)$/);
    if (!match || index && match[3] !== stage && !(stage !== '0' && match[3] === '0')) continue;
    const absolute = path.resolve(root, match[index ? 4 : 3]);
    if (inside(root, absolute)) entries.set(key(absolute), { file: absolute, mode: match[1], object: match[2] });
  }
  const entry = file => {
    const item = entries.get(key(file));
    if (!item) throw Error(`Not present in ${index ? 'the Git index' : 'Git ' + ref}: ${path.relative(root, file)}`);
    if (!/^100/.test(item.mode)) throw Error(`Git dependency is not a regular file: ${file}`);
    return item;
  };
  const readFile = async (file, encoding) => {
    const item = entry(file);
    if (!blobs.has(item.object)) blobs.set(item.object, run(['cat-file', 'blob', item.object], root));
    const bytes = await blobs.get(item.object); return encoding ? bytes.toString(encoding) : bytes;
  };
  const io = {
    readFile,
    stat: async file => ({ size: (await readFile(file)).length, mtimeMs: 0, isFile: () => true }),
    realpath: async file => {
      const name = key(file);
      if (entries.has(name)) entry(file);
      else if (!inside(root, file) || ![...entries.keys()].some(p => p.startsWith(name + path.sep))) throw Error(`Missing Git folder: ${file}`);
      return path.resolve(file);
    },
    readdir: async directory => [...entries.values()].filter(item => key(path.dirname(item.file)) === key(directory))
      .map(item => ({ name: path.basename(item.file), isFile: () => /^100/.test(item.mode) }))
  };
  const indexPath = path.resolve(root, (await run(['rev-parse', '--git-path', 'index'], root)).toString('utf8').trim());
  return { io, ref: index ? ref : tree, label: ref === '' ? 'Staged' : /^:[123]$/.test(ref) ? `Merge stage ${stage}` : `Git ${ref}`, indexPath,
    urlFor: async file => `data:${({ '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.webp': 'image/webp' })[path.extname(file).toLowerCase()] || 'application/octet-stream'};base64,${(await readFile(file)).toString('base64')}` };
}
module.exports = { gitSource };
