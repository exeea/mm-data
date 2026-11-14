"""The lunar habitat kit's far round roof fittings, in its pieces GLB (data/models/buildings/lunar_habitat).

    python tools/buildings/lunar_habitat_far.py

The kit itself is its JSON (HabitatKit); its pieces GLB holds the modelled pieces, a node per piece and level of detail.
This rewrites the far level (lod1) of every round piece: a stack of upright regular prisms with their tops (the vent
drum, the round hatch), drawn far as prisms of SIDES faces round the near ones, so the far shape encloses the near one.
Their materials, vertex shading (darker at a prism's foot) and texture mapping are the near level's. Every other node,
and the near level, is kept as it is.
"""
import math
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
from glb_geometry import read_glb, write_glb  # noqa: E402

GLB = TOOLS.parent / 'data/models/buildings/lunar_habitat/lunar_habitat-pieces.glb'
SIDES = 8  # A far prism's faces: at most 1.08 of its near radius out, under half a pixel where the level starts.
ROUND = 10  # A part with more side faces than this is round.
SIDE_REPEAT, UP_REPEAT = 12.0, 36.0  # Board units a texture repeat along a side face and up it (as near).
TOP_U, TOP_V = 12 * math.sqrt(3), 18.0  # ... across a top, along x and y (as near).


def prism(part):
    """A part's upright regular prism with a top, from its triangles: (radius, bottom, top, colours), else None."""
    sides, tops, radius, zs = 0, 0, 0.0, set()
    for triangle in part:
        normal_z = triangle[0][5]
        if abs(normal_z - 1) < 1e-4:
            tops += 1
        elif abs(normal_z) < 1e-4:
            sides += 1
        else:
            return None
        for vertex in triangle:
            radius = max(radius, math.hypot(vertex[0], vertex[1]))
            zs.add(round(vertex[2], 5))
    faces = sides // 2
    if faces <= ROUND or len(zs) != 2 or tops != faces - 2:
        return None
    foot = [v for t in part for v in t if abs(v[5]) < 1e-4 and abs(v[2] - min(zs)) < 1e-5]
    head = [v for t in part for v in t if abs(v[2] - max(zs)) < 1e-5]
    return radius, min(zs), max(zs), foot[0][6:10], head[0][6:10]


def far_prism(radius, bottom, top, foot, head):
    """SIDES side faces round a near prism of this radius and its top: triangles of 12-float vertices."""
    out = radius / math.cos(math.pi / SIDES)
    corners = [(out * math.cos(2 * math.pi * (k + .5) / SIDES), out * math.sin(2 * math.pi * (k + .5) / SIDES))
               for k in range(SIDES)]
    triangles = []
    for k in range(SIDES):
        (ax, ay), (bx, by) = corners[k], corners[(k + 1) % SIDES]
        angle = 2 * math.pi * (k + 1) / SIDES
        normal = (math.cos(angle), math.sin(angle), 0.0)
        length = math.hypot(bx - ax, by - ay) / SIDE_REPEAT
        a0 = [ax, ay, bottom, *normal, *foot, 0.0, -bottom / UP_REPEAT]
        b0 = [bx, by, bottom, *normal, *foot, length, -bottom / UP_REPEAT]
        b1 = [bx, by, top, *normal, *head, length, -top / UP_REPEAT]
        a1 = [ax, ay, top, *normal, *head, 0.0, -top / UP_REPEAT]
        triangles += [[a0, b0, b1], [a0, b1, a1]]
    cap = [[x, y, top, 0.0, 0.0, 1.0, *head, x / TOP_U, -y / TOP_V] for x, y in corners]
    triangles += [[cap[0], cap[k], cap[k + 1]] for k in range(1, SIDES - 1)]
    return triangles


def triangles(model, node):
    """A node's parts as (material, triangles of 12-float vertices)."""
    vertices = model['meshes'][0]['vertices']
    parts = {part['id']: part for part in model['meshes'][0]['parts']}
    result = []
    for reference in node['parts']:
        indices = parts[reference['meshpartid']]['indices']
        result.append((reference['materialid'], [[vertices[i * 12:i * 12 + 12] for i in indices[t:t + 3]]
                                                 for t in range(0, len(indices), 3)]))
    return result


def model(nodes, materials, extras, name):
    """A level's model from nodes of (id, translation, [(material, triangles)])."""
    vertices, parts, entries = [], [], []
    for node_id, translation, surfaces in nodes:
        references = []
        for material, triangle_list in surfaces:
            first = len(vertices) // 12
            for triangle in triangle_list:
                for vertex in triangle:
                    vertices.extend(vertex)
            part_id = f'{node_id}/{material}'
            parts.append({'id': part_id, 'type': 'TRIANGLES',
                          'indices': list(range(first, first + 3 * len(triangle_list)))})
            references.append({'meshpartid': part_id, 'materialid': material})
        entries.append({'id': node_id, 'translation': translation, 'parts': references, 'children': []})
    return {'id': name, 'extras': extras, 'materials': materials, 'nodes': entries,
            'meshes': [{'attributes': ['POSITION', 'NORMAL', 'COLOR', 'TEXCOORD0'], 'vertices': vertices, 'parts': parts}]}


def main():
    near = read_glb(GLB, 0, linear_colors=True)
    far = read_glb(GLB, 1, linear_colors=True)
    by_name = {node['id'].rsplit('-lod', 1)[0]: node for node in near['nodes']}
    nodes = []
    for node in far['nodes']:
        surfaces = triangles(far, node)
        stacks = [(material, prism(part)) for material, part in triangles(near, by_name[node['id'].rsplit('-lod', 1)[0]])]
        if stacks and all(shape for _, shape in stacks):
            before = sum(len(part) for _, part in surfaces)
            surfaces = [(material, far_prism(*shape)) for material, shape in stacks]
            print(f'{node["id"]}: {before} -> {sum(len(part) for _, part in surfaces)} triangles')
        nodes.append((node['id'], node['translation'], surfaces))
    write_glb(GLB, levels={0: near, 1: model(nodes, far['materials'], far['extras'], far['id'])}, linear_colors=True)


if __name__ == '__main__':
    main()
