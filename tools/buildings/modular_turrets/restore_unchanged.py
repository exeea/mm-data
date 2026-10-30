"""Restores rebuilt turret assets that did not really change, so a Blender rebuild leaves no noise in git.

Blender rewrites every GLB on each run, a float ULP apart in bevelled parts. Run after author.py:
    python restore_unchanged.py
Each modified .glb/.json in the asset folder is compared with its git index version (the commit, or what is staged):
same structure, integers equal, floats within TOLERANCE and names equal but for Blender's numeric suffixes. An unchanged
file gets those bytes back; the rest are listed as real changes.
"""
import json
import re
import struct
import subprocess
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
ASSETS = 'data/models/buildings/turrets/modular'
TOLERANCE = 1e-4
TYPES = {5120: np.int8, 5121: np.uint8, 5122: np.int16, 5123: np.uint16, 5125: np.uint32, 5126: np.float32}
WIDTH = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}


def plain(name):
    """A Blender object name without its numeric suffix ('module.246'), which shifts with build order."""
    return re.sub(r'\.\d+$', '', name)


def same(a, b):
    if isinstance(a, dict) and isinstance(b, dict):
        a = {plain(key): value for key, value in a.items()}
        b = {plain(key): value for key, value in b.items()}
        return a.keys() == b.keys() and all(same(a[key], b[key]) for key in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(same(x, y) for x, y in zip(a, b))
    if isinstance(a, float) or isinstance(b, float):
        return isinstance(a, (int, float)) and isinstance(b, (int, float)) and abs(a - b) <= TOLERANCE
    if isinstance(a, str) and isinstance(b, str):
        return plain(a) == plain(b)
    return a == b


def chunks(raw):
    size = struct.unpack_from('<I', raw, 12)[0]
    return json.loads(raw[20:20 + size]), raw[28 + size:]


def accessor(doc, binary, index):
    a = doc['accessors'][index]
    view = doc['bufferViews'][a['bufferView']]
    dtype = np.dtype(TYPES[a['componentType']])
    count = a['count'] * WIDTH[a['type']]
    stride = view.get('byteStride')
    start = view.get('byteOffset', 0) + a.get('byteOffset', 0)
    if stride and stride != dtype.itemsize * WIDTH[a['type']]:
        rows = [np.frombuffer(binary, dtype, WIDTH[a['type']], start + i * stride) for i in range(a['count'])]
        return np.concatenate(rows)
    return np.frombuffer(binary, dtype, count, start)


def same_glb(old, new):
    old_doc, old_bin = chunks(old)
    new_doc, new_bin = chunks(new)
    # Byte layout may shift with float formatting; the accessors' contents decide.
    for doc in (old_doc, new_doc):
        doc.pop('bufferViews', None)
        doc.pop('buffers', None)
    if not same({k: v for k, v in old_doc.items() if k != 'accessors'}, {k: v for k, v in new_doc.items() if k != 'accessors'}):
        return False
    old_doc, _ = chunks(old)
    new_doc, _ = chunks(new)
    if len(old_doc['accessors']) != len(new_doc['accessors']):
        return False
    for index, (a, b) in enumerate(zip(old_doc['accessors'], new_doc['accessors'])):
        if (a['componentType'], a['type'], a['count']) != (b['componentType'], b['type'], b['count']):
            return False
        x, y = accessor(old_doc, old_bin, index), accessor(new_doc, new_bin, index)
        if a['componentType'] == 5126:
            if not np.allclose(x, y, rtol=0, atol=TOLERANCE):
                return False
        elif not np.array_equal(x, y):
            return False
    return True


def main():
    changed = subprocess.run(['git', '-C', str(ROOT), 'diff', '--name-only', '--', ASSETS],
                             capture_output=True, text=True, check=True).stdout.split()
    restored, real = [], []
    for name in changed:
        path = ROOT / name
        if not path.is_file() or path.suffix not in ('.glb', '.json'):
            real.append(name)
            continue
        old = subprocess.run(['git', '-C', str(ROOT), 'show', ':' + name], capture_output=True, check=True).stdout
        new = path.read_bytes()
        equal = same_glb(old, new) if path.suffix == '.glb' else same(json.loads(old), json.loads(new))
        (restored if equal else real).append(name)
    if restored:
        subprocess.run(['git', '-C', str(ROOT), 'checkout', '--', *restored], check=True)
    print(f'Restored {len(restored)} unchanged files; {len(real)} really changed:')
    for name in real:
        print('  ' + name)


if __name__ == '__main__':
    main()
