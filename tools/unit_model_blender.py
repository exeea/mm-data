"""Import a deployed GLB into Blender as one flat-shaded mesh, one material per vertex colour, for review renders.

Run inside Blender only (it needs bpy); render_fallback_catalog.py uses it for its contact sheets.
"""
from math import radians

import bpy
from mathutils import Matrix, Vector
from unit_model_geometry import content_digest
from glb_geometry import read_glb


def material(rgb, cache):
    key = tuple(rgb)
    if key not in cache:
        result = bpy.data.materials.new('Unit color '+str(key))
        linear = tuple(c/12.92 if c <= .04045 else ((c+.055)/1.055)**2.4 for c in rgb)
        result.diffuse_color = (*linear, 1)
        result.use_nodes = True
        shader = result.node_tree.nodes.get('Principled BSDF')
        shader.inputs['Base Color'].default_value = (*linear, 1)
        shader.inputs['Roughness'].default_value = .8
        cache[key] = result
    return cache[key]


def import_model(path, expected, colors, turn=0, upper_body='CT', z_scale=54):
    """Import indexed colors and translated rigid nodes; use z_scale=1 for modular assets.

    A non-zero turn shows the upper body turned that many degrees to its right, as the game shows a torso twist.
    """
    if content_digest(path) != expected['sha256']:
        raise ValueError('Stale manifest for '+str(path))
    data = read_glb(path)
    parts = {}
    for mesh in data['meshes']:
        if mesh['attributes'] not in (['POSITION', 'NORMAL', 'COLOR'],
                                       ['POSITION', 'NORMAL', 'COLOR', 'TEXCOORD0']):
            raise ValueError('Unsupported review vertex format')
        stride = 12 if 'TEXCOORD0' in mesh['attributes'] else 10
        for part in mesh['parts']:
            parts[part['id']] = (mesh['vertices'], part['indices'], stride)
    vertices, faces, face_colors = [], [], []

    def visit(node, parent, pivot=None):
        if 'rotation' in node or 'scale' in node:
            raise ValueError('Review importer only supports the generated translated nodes')
        offset = parent + Vector(node.get('translation', (0, 0, 0)))
        if node['id'] == upper_body:
            pivot = offset
        for part in node.get('parts', []):
            source, indices, stride = parts[part['meshpartid']]
            for j in range(0, len(indices), 3):
                start = len(vertices)
                for index in indices[j:j+3]:
                    v = source[index*stride:index*stride+10]
                    p = Vector(v[:3])+offset
                    if pivot is not None and turn:
                        p = Matrix.Rotation(radians(-turn), 3, 'Z') @ (p-pivot)+pivot
                    vertices.append((p.x, p.y, p.z*z_scale))
                faces.append((start, start+1, start+2))
                face_colors.append(tuple(source[indices[j]*stride+6:indices[j]*stride+9]))
        for child in node.get('children', []):
            visit(child, offset, pivot)

    for node in data['nodes']:
        visit(node, Vector((0, 0, 0)))
    if len(faces) != expected['triangles']:
        raise ValueError('Triangle mismatch for '+str(path))
    mesh = bpy.data.meshes.new(data['id'])
    mesh.from_pydata(vertices, [], faces)
    slots = {}
    for color in dict.fromkeys(face_colors):
        slots[color] = len(mesh.materials)
        mesh.materials.append(material(color, colors))
    for polygon, color in zip(mesh.polygons, face_colors):
        polygon.material_index = slots[color]
        polygon.use_smooth = False
    return mesh
