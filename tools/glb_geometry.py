"""Shared GLB writer for the rigid unit and terrain kits. No Blender dependency.

Authoring uses MegaMek's Z-up coordinates and display-space colors. Files use
glTF's Y-up coordinates and linear colors; the runtime importer reverses both.
The small reader is for our offline review tools and migration parity checks.
"""
import json
import math
import struct
from pathlib import Path


STRIDES = {'POSITION': 3, 'NORMAL': 3, 'COLOR': 4, 'TEXCOORD0': 2}
SEMANTICS = {'POSITION': 'POSITION', 'NORMAL': 'NORMAL', 'COLOR': 'COLOR_0', 'TEXCOORD0': 'TEXCOORD_0'}


def linear(value):
    return value / 12.92 if value <= .04045 else ((value + .055) / 1.055) ** 2.4


def display(value):
    return value * 12.92 if value <= .0031308 else 1.055 * value ** (1 / 2.4) - .055


def y_up(value):
    return [value[0], value[2], -value[1]]


def z_up(value):
    return [value[0], -value[2], value[1]]


def write_glb(path, model=None, *, levels=None, embedded_images=None):
    """Export existing rigid authoring arrays, preserving node/part/material IDs."""
    document = {'asset': {'version': '2.0', 'generator': 'MegaMek rigid mesh exporter'},
                'scene': 0, 'scenes': [{'nodes': []}], 'nodes': [], 'meshes': [],
                'materials': [], 'accessors': [], 'bufferViews': [], 'buffers': []}
    binary = bytearray()

    def accessor(values, size, component=5126, target=34962):
        while len(binary) % 4:
            binary.append(0)
        offset = len(binary)
        code = {5126: 'f', 5123: 'H', 5125: 'I'}[component]
        binary.extend(struct.pack('<' + code * len(values), *values))
        view = len(document['bufferViews'])
        document['bufferViews'].append({'buffer': 0, 'byteOffset': offset,
                                       'byteLength': len(binary) - offset, 'target': target})
        item = {'bufferView': view, 'componentType': component, 'count': len(values) // size,
                'type': {1: 'SCALAR', 2: 'VEC2', 3: 'VEC3', 4: 'VEC4'}[size]}
        if component == 5126:
            item['min'] = [min(values[i::size]) for i in range(size)]
            item['max'] = [max(values[i::size]) for i in range(size)]
        document['accessors'].append(item)
        return len(document['accessors']) - 1

    material_ids = {}
    material_sources = {}
    def emit(model):
        for material in model['materials']:
            if material['id'] in material_ids:
                if material != material_sources[material['id']]:
                    raise ValueError('Conflicting material between LODs: '+material['id'])
                continue
            material_sources[material['id']] = material
            material_ids[material['id']] = len(document['materials'])
            color = material.get('diffuse', [1, 1, 1])
            document['materials'].append({'name': material['id'], 'pbrMetallicRoughness': {
                'baseColorFactor': [*(linear(c) for c in color[:3]), material.get('opacity', 1)],
                'metallicFactor': 0, 'roughnessFactor': 1}})
            textures = material.get('textures', [])
            if textures:
                if len(textures) != 1 or textures[0]['type'] != 'DIFFUSE':
                    raise ValueError('Expected a single diffuse texture')
                index = len(document.setdefault('images', []))
                texture = textures[0]
                filename = texture['filename']
                encoded_image = texture.get('data', (embedded_images or {}).get(filename))
                if encoded_image is None:
                    document['images'].append({'uri': filename})
                else:
                    while len(binary) % 4:
                        binary.append(0)
                    view = len(document['bufferViews'])
                    document['bufferViews'].append({'buffer': 0, 'byteOffset': len(binary), 'byteLength': len(encoded_image)})
                    binary.extend(encoded_image)
                    mime = 'image/png' if encoded_image.startswith(b'\x89PNG') else 'image/jpeg'
                    document['images'].append({'name': filename, 'bufferView': view, 'mimeType': mime})
                sampler = {'wrapS': texture.get('wrapS', 10497), 'wrapT': texture.get('wrapT', 10497),
                           'minFilter': texture.get('minFilter', 9987), 'magFilter': texture.get('magFilter', 9729)}
                samplers = document.setdefault('samplers', [])
                if sampler not in samplers:
                    samplers.append(sampler)
                document.setdefault('textures', []).append({'source': index, 'sampler': samplers.index(sampler)})
                document['materials'][-1]['pbrMetallicRoughness']['baseColorTexture'] = {'index': index}

        parts = {}
        for mesh in model['meshes']:
            stride = sum(STRIDES[name] for name in mesh['attributes'])
            count = len(mesh['vertices']) // stride
            if not count:
                continue
            attributes, offset = {}, 0
            for name in mesh['attributes']:
                size = STRIDES[name]
                values = []
                for index in range(count):
                    value = mesh['vertices'][index * stride + offset:index * stride + offset + size]
                    if name in ('POSITION', 'NORMAL'):
                        value = y_up(value)
                    elif name == 'COLOR':
                        value = [*(linear(c) for c in value[:3]), value[3]]
                    if not all(math.isfinite(c) for c in value):
                        raise ValueError('Non-finite vertex')
                    values.extend(value)
                attributes[SEMANTICS[name]] = accessor(values, size)
                offset += size
            for part in mesh['parts']:
                if part['type'] != 'TRIANGLES' or len(part['indices']) % 3:
                    raise ValueError('Expected triangle parts')
                if not part['indices'] or min(part['indices']) < 0 or max(part['indices']) >= count:
                    raise ValueError('Invalid vertex index')
                indices = accessor(part['indices'], 1, 5123 if count <= 65535 else 5125, 34963)
                parts[part['id']] = {'attributes': attributes, 'indices': indices, 'mode': 4,
                                     'extras': {'mmPart': part['id']}}

        def node(source):
            index = len(document['nodes'])
            entry = {'name': source['id']}
            document['nodes'].append(entry)
            if 'translation' in source:
                entry['translation'] = y_up(source['translation'])
            if 'rotation' in source:
                entry['rotation'] = [*y_up(source['rotation'][:3]), source['rotation'][3]]
            if 'scale' in source:
                x, y, z = source['scale']
                entry['scale'] = [x, z, y]
            if source.get('parts'):
                primitives = [{**parts[p['meshpartid']], 'material': material_ids[p['materialid']]}
                              for p in source['parts']]
                entry['mesh'] = len(document['meshes'])
                document['meshes'].append({'name': source['id'], 'primitives': primitives})
            if source.get('children'):
                entry['children'] = [node(child) for child in source['children']]
            return index

        return [node(n) for n in model['nodes']]

    if levels is None:
        document['scenes'][0]['nodes'] = emit(model)
    else:
        if 0 not in levels or not set(levels) <= {0, 1, 2}:
            raise ValueError('LOD0 is required; supported levels are 0, 1, 2')
        for level, geometry in sorted(levels.items()):
            children = emit(geometry)
            index = len(document['nodes'])
            document['nodes'].append({'name': f'{Path(path).stem}-lod{level}', 'children': children})
            document['scenes'][0]['nodes'].append(index)
    if binary:
        document['buffers'] = [{'byteLength': len(binary)}]
    # Empty formation references have a rig but no geometry or binary chunk.
    document = {key: value for key, value in document.items() if value != []}
    encoded = json.dumps(document, separators=(',', ':'), allow_nan=False).encode('utf-8')
    encoded += b' ' * (-len(encoded) % 4)
    binary += b'\0' * (-len(binary) % 4)
    data = struct.pack('<III', 0x46546c67, 2, 20 + len(encoded) + (8 + len(binary) if binary else 0))
    data += struct.pack('<II', len(encoded), 0x4e4f534a) + encoded
    if binary:
        data += struct.pack('<II', len(binary), 0x004e4942) + binary
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def read_glb(path, level=0):
    """Read our uncompressed rigid exports into the existing review representation."""
    raw = Path(path).read_bytes()
    magic, version, length = struct.unpack_from('<III', raw)
    if (magic, version, length) != (0x46546c67, 2, len(raw)):
        raise ValueError('Invalid GLB header')
    json_length, json_type = struct.unpack_from('<II', raw, 12)
    if json_type != 0x4e4f534a:
        raise ValueError('Expected GLB JSON')
    document = json.loads(raw[20:20 + json_length])
    binary = b''
    if 20 + json_length < len(raw):
        binary_length, binary_type = struct.unpack_from('<II', raw, 20 + json_length)
        if binary_type != 0x004e4942:
            raise ValueError('Expected GLB binary buffer')
        binary = raw[28 + json_length:28 + json_length + binary_length]

    def values(index):
        item = document['accessors'][index]
        view = document['bufferViews'][item['bufferView']]
        size = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4}[item['type']]
        code = {5126: 'f', 5123: 'H', 5125: 'I'}[item['componentType']]
        stride = view.get('byteStride', struct.calcsize('<' + code) * size)
        offset = view.get('byteOffset', 0) + item.get('byteOffset', 0)
        return [list(struct.unpack_from('<' + code * size, binary, offset + i * stride))
                for i in range(item['count'])]

    roots = document['scenes'][document.get('scene', 0)]['nodes']
    groups = {document['nodes'][i]['name']: i for i in roots}
    name = f'{Path(path).stem}-lod{level}'
    if any(key.startswith(Path(path).stem + '-lod') and 'mesh' not in document['nodes'][index]
           for key, index in groups.items()):
        if name not in groups:
            raise ValueError(f'Missing {name}')
        roots = document['nodes'][groups[name]]['children']
    used = set()
    def visit(index):
        node = document['nodes'][index]
        if 'mesh' in node:
            used.add(node['mesh'])
        for child in node.get('children', []):
            visit(child)
    for index in roots:
        visit(index)

    vertices, parts, layouts, mesh_parts = [], [], {}, {}

    for mesh_index in sorted(used):
        mesh = document['meshes'][mesh_index]
        references = []
        for part_index, primitive in enumerate(mesh['primitives']):
            attrs = primitive['attributes']
            layout = tuple(sorted(attrs.items()))
            if layout not in layouts:
                layouts[layout] = len(vertices) // 12
                position, normals = values(attrs['POSITION']), values(attrs['NORMAL'])
                colors = values(attrs['COLOR_0']) if 'COLOR_0' in attrs else [[1, 1, 1, 1]] * len(position)
                uvs = values(attrs['TEXCOORD_0']) if 'TEXCOORD_0' in attrs else [[0, 0]] * len(position)
                for p, n, c, uv in zip(position, normals, colors, uvs):
                    vertices.extend([*z_up(p), *z_up(n), *(display(v) for v in c[:3]), c[3], *uv])
            part_id = primitive.get('extras', {}).get('mmPart', f'{mesh_index}-{part_index}')
            indices = [i[0] + layouts[layout] for i in values(primitive['indices'])]
            parts.append({'id': part_id, 'type': 'TRIANGLES', 'indices': indices})
            references.append({'meshpartid': part_id, 'materialid': document['materials'][primitive['material']]['name']})
        mesh_parts[mesh_index] = references

    def node(index):
        source = document['nodes'][index]
        result = {'id': source['name'], 'translation': z_up(source.get('translation', [0, 0, 0])),
                  'parts': mesh_parts[source['mesh']] if 'mesh' in source else [],
                  'children': [node(i) for i in source.get('children', [])]}
        if 'rotation' in source:
            result['rotation'] = [*z_up(source['rotation'][:3]), source['rotation'][3]]
        if 'scale' in source:
            x, y, z = source['scale']
            result['scale'] = [x, z, y]
        return result

    def material(source):
        pbr = source['pbrMetallicRoughness']
        result = {'id': source['name'], 'diffuse': [display(v) for v in pbr['baseColorFactor'][:3]]}
        if 'baseColorTexture' in pbr:
            texture = document['textures'][pbr['baseColorTexture']['index']]
            image = document['images'][texture['source']]
            entry = {'id': source['name'], 'type': 'DIFFUSE', 'filename': image.get('uri', image.get('name'))}
            if 'bufferView' in image:
                view = document['bufferViews'][image['bufferView']]
                offset = view.get('byteOffset', 0)
                entry['data'] = bytes(binary[offset:offset + view['byteLength']])
            if 'sampler' in texture:
                entry.update(document['samplers'][texture['sampler']])
            result['textures'] = [entry]
        return result

    return {'id': Path(path).stem,
            'meshes': [{'attributes': list(STRIDES), 'vertices': vertices, 'parts': parts}] if vertices else [],
            'nodes': [node(i) for i in roots],
            'materials': [material(m) for m in document.get('materials', [])]}
