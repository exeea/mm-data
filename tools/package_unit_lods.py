"""Package rigid unit levels into one GLB per component, keeping one descriptor for its rig."""
import hashlib
import json
import re
from pathlib import Path

from glb_geometry import read_glb, write_glb


def package_unit_lods(output, assets):
    output = Path(output)
    descriptors = {path: json.loads(path.read_text(encoding='utf-8')) for path in output.rglob('*.json')
                   if path.name != 'manifest.json'}
    groups = {}
    for path, descriptor in descriptors.items():
        if 'mesh' not in descriptor:
            continue
        mesh = path.parent / descriptor['mesh']
        match = re.fullmatch(r'(.+)-lod([012])\.glb', mesh.name)
        if match:
            groups.setdefault(mesh.with_name(match[1]+'.glb'), {})[int(match[2])] = mesh
    replacements = {}
    for file, levels in groups.items():
        if 0 not in levels:
            raise ValueError(f'{file}: missing LOD0')
        write_glb(file, levels={level: read_glb(path) for level, path in levels.items()})
        key = file.relative_to(output).with_suffix('').as_posix()
        stats = assets.get(key)
        if stats is not None:
            stats['lods'] = []
            for level, path in sorted(levels.items()):
                detail = stats if level == 0 else assets.pop(key+f'-lod{level}')
                stats['lods'].append({'node': file.stem+f'-lod{level}',
                                      'triangles': detail['triangles'], 'vertices': detail['vertices']})
            stats['sha256'] = hashlib.sha256(file.read_bytes()).hexdigest()
        replacements.update({path: file for path in levels.values()})
    for path, descriptor in descriptors.items():
        if re.search(r'-lod[12]$', path.stem) and path.with_suffix('.glb') in replacements:
            path.unlink()
            continue
        changed = False
        if 'mesh' in descriptor:
            mesh = path.parent / descriptor['mesh']
            if mesh in replacements:
                descriptor['mesh'] = replacements[mesh].name
                changed = True
        for field in ('bodyLod1', 'trooperLod1'):
            if field in descriptor:
                # Only remove links to components just folded into this package.
                other = output / descriptor[field].removeprefix('units/modular/')
                if other.with_suffix('.glb') in replacements:
                    del descriptor[field]
                    changed = True
        if changed:
            path.write_text(json.dumps(descriptor, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    for path in replacements:
        path.unlink()
