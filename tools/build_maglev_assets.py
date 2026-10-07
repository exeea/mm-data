"""Export shared maglev pieces and preserve old scenery IDs as compositions.

Run with Blender's --background --factory-startup --python option. This focused
build preserves the existing complete GLBs as compatibility/reference assets;
the renderer already prefers layouts.json whenever an ID has a composition.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_scenery_assets import BOARD, Mesh, build_mesh, export_mesh, maglev_vehicle


def build():
    shared = {}
    layouts = {}
    for family, count in (('track', 3), ('station', 3), ('train', 6)):
        for number in range(1, count + 1):
            name = f'fluff/maglev{family}{number}.gif'
            mesh = build_mesh(name, {}, shared)
            assert not mesh.vertices, 'Maglev layouts must contain only shared pieces'
            layouts['scenery/' + Path(name).with_suffix('').as_posix()] = mesh.components
    # A complete vehicle is also usable without a track or parked road traffic.
    vehicle = Mesh(shared)
    maglev_vehicle(vehicle)
    layouts['scenery/components/maglev-train'] = vehicle.components
    for asset, mesh in shared.items():
        export_mesh(asset, mesh)
    path = BOARD / 'scenery/layouts.json'
    catalog = json.loads(path.read_text(encoding='utf-8'))
    catalog.update(layouts)
    path.write_bytes((json.dumps(catalog, indent=2) + '\n').encode('utf-8'))
    print(json.dumps({'maglev_layouts': len(layouts), 'shared_meshes': len(shared),
                      'components': sum(len(parts) for parts in layouts.values())}))


if __name__ == '__main__':
    build()
