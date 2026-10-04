"""Read small source sprites to record object positions for the Blender authoring tool.

No sprite is edited. These are reviewable placement measurements, not runtime
terrain rules. Runtime continues to select the source with HexTileset.
"""
import json
import math
from pathlib import Path
from PIL import Image

from audit_board_tiles import declarations, OUT, TILES


def components(image, predicate, diagonal=False):
    pixels = image.load()
    remaining = {(x, y) for y in range(image.height) for x in range(image.width)
                 if predicate(*pixels[x, y])}
    result = []
    while remaining:
        start = min(remaining)
        remaining.remove(start)
        group, pending = [start], [start]
        while pending:
            x, y = pending.pop()
            steps = ((1, 0), (-1, 0), (0, 1), (0, -1))
            if diagonal: steps += ((1, 1), (1, -1), (-1, 1), (-1, -1))
            for dx, dy in steps:
                neighbor = x + dx, y + dy
                if neighbor in remaining:
                    remaining.remove(neighbor)
                    pending.append(neighbor)
                    group.append(neighbor)
        result.append(group)
    return result


def center(group):
    return [round(sum(p[0] for p in group)/len(group)-42, 2),
            round(36-sum(p[1] for p in group)/len(group), 2)]


def containers_overlap(first, second):
    """Separating axes for the exported 13.55 x 6.1 boxes, including ribs and door bars."""
    for box in (first, second):
        a = math.radians(box[2])
        for axis in ((math.cos(a), math.sin(a)), (-math.sin(a), math.cos(a))):
            distance = abs((first[0]-second[0])*axis[0]+(first[1]-second[1])*axis[1])
            radii = []
            for item in (first, second):
                b = math.radians(item[2])
                radii.append(6.8*abs(math.cos(b)*axis[0]+math.sin(b)*axis[1])
                             + 3.1*abs(-math.sin(b)*axis[0]+math.cos(b)*axis[1]))
            if distance >= sum(radii): return False
    return True


def main():
    rows, _ = declarations()
    layouts = {}
    for name in sorted({r['image'] for r in rows if r['image']}):
        trees = ('road_trees' in name or '/SMV_Fluff/' in name or name.startswith(('fluff/suburb', 'fluff/pool'))) and 'Landscape' not in name
        port = '/SMV_Seaport/' in name
        pillars = name.startswith('fluff/pillars')
        cars = name.startswith('fluff/cars')
        if not trees and not port and not pillars and not cars:
            continue
        image = Image.open(TILES/name).convert('RGBA')
        layout = {}
        if pillars:
            layout['pillars'] = [center(group) for group in components(image, lambda r, g, b, a: a > 128)
                                 if len(group) > 10]
        if cars:
            n = int(Path(name).stem.split('_')[1][0])
            road_angle = math.radians(-60 if n in (1, 4) else 60 if n in (2, 5, 7) else 0)
            # Paint colours separate bodies from road pixels, glazing and cast shadows.
            body = components(image, lambda r, g, b, a: a > 128 and max(r, g, b) > 65
                              and max(r, g, b)-min(r, g, b) > 40, diagonal=True)
            neutral = components(image, lambda r, g, b, a: a > 128 and min(r, g, b) > 110
                                 and max(r, g, b)-min(r, g, b) < 22, diagonal=True)
            vehicles = []
            for group in body + neutral:
                if not 5 <= len(group) <= 90: continue
                x, y = center(group)
                across = x*math.cos(road_angle)+y*math.sin(road_angle)
                if not 6 < abs(across) < 23: continue
                color = [round(sum(image.getpixel(p)[k] for p in group)/len(group)/255, 3) for k in range(3)]
                duplicate = next((v for v in vehicles if (x-v[0])**2+(y-v[1])**2 < 81
                                  and sum((color[k]-v[3][k])**2 for k in range(3)) < .10), None)
                if duplicate:
                    duplicate[0] = round((duplicate[0]+x)/2, 2)
                    duplicate[1] = round((duplicate[1]+y)/2, 2)
                    continue
                angle = 30 if n in (1, 4) else -30 if n in (2, 5) else 60 if n == 7 else 0 if n == 8 else 90
                if Path(name).stem == 'cars_2b': angle = 60
                if Path(name).stem == 'cars_3b': angle = 0
                vehicles.append([x, y, angle, color])
            layout['cars'] = vehicles
        if trees:
            groups = components(image, lambda r, g, b, a: a > 128 and g > r*1.10 and g > b*1.25 and 25 < g < 165)
            layout['trees'] = [center(group) for group in groups if len(group) > 16]
            if 'Table' in name:
                layout['tables'] = [center(group) for group in components(image,
                                    lambda r, g, b, a: a > 128 and min(r, g, b) > 180
                                    and max(r, g, b)-min(r, g, b) < 20) if len(group) >= 4]
        if port:
            # Separating by hue preserves differently painted adjacent containers.
            palettes = (
                lambda r, g, b: r > g*1.25 and r > b*1.18,
                lambda r, g, b: b > r*1.17 and b > g*1.04,
                lambda r, g, b: g > r*1.12 and g > b*1.10,
                lambda r, g, b: r > b*1.3 and g > b*1.18 and abs(r-g) < 55,
                lambda r, g, b: max(r, g, b)-min(r, g, b) < 19,
            )
            candidates = []
            for predicate in palettes:
                for group in components(image, lambda r, g, b, a: a > 200 and max(r, g, b) > 40
                                        and not (r > 170 and g > 145 and b < 90) and predicate(r, g, b)):
                    if len(group) < 22:
                        continue
                    x, y = center(group)
                    colors = [image.getpixel(p)[:3] for p in group]
                    color = [round(sum(c[k] for c in colors)/len(colors)/255, 3) for k in range(3)]
                    # A merged same-colour run is split into standard 20-foot boxes.
                    angle = 90
                    if '-20Footer-2-' in name: angle = 30
                    if '-20Footer-3-' in name: angle = -30
                    if '-20Footer-4-' in name: angle = 0
                    a = math.radians(angle)
                    projected = [(px-42)*math.cos(a)+(36-py)*math.sin(a) for px, py in group]
                    across = [-(px-42)*math.sin(a)+(36-py)*math.cos(a) for px, py in group]
                    span = max(projected)-min(projected)
                    # Crane cabins and broad shadows are not container roofs.
                    if max(across)-min(across) > 8 or span < 6: continue
                    count = max(1, round(span/14))
                    for i in range(count):
                        along = (i-(count-1)/2)*13.7
                        candidates.append((len(group)/count, [round(x+along*math.cos(a), 2),
                                                             round(y+along*math.sin(a), 2), angle, color]))
            yellow = components(image, lambda r, g, b, a: a > 128 and r > 165 and g > 145 and b < 85,
                                diagonal=True)
            boxes = []
            if 'CraneTip' not in name:
                # The spreader obscures/splits its gray roof in the source. Measure that
                # complete footprint first, before accepting partially visible neighbors.
                angle = 30 if '-20Footer-2-' in name else -30 if '-20Footer-3-' in name else 0 if '-20Footer-4-' in name else 90
                a = math.radians(angle)
                for group in yellow:
                    if not 35 <= len(group) <= 80: continue
                    along = [(px-42)*math.cos(a)+(36-py)*math.sin(a) for px,py in group]
                    across = [-(px-42)*math.sin(a)+(36-py)*math.cos(a) for px,py in group]
                    u,v = (min(along)+max(along))/2,(min(across)+max(across))/2
                    boxes.append([round(u*math.cos(a)-v*math.sin(a),2),
                                  round(u*math.sin(a)+v*math.cos(a),2),angle,[.46,.47,.47]])
                if len(boxes)!=1: raise ValueError('Expected one measured lifting frame: '+name)
            layout['grabbers'] = list(range(len(boxes)))
            # Hue masks overlap for brown/yellow paint and often find both a lit roof and its side.
            # Retain the best supported physical footprint once. No two exported boxes may intersect.
            for _, candidate in sorted(candidates, key=lambda value: -value[0]):
                if not any(containers_overlap(candidate, other) for other in boxes): boxes.append(candidate)
            layout['container_candidates_removed'] = len(candidates)-len(boxes)+len(layout['grabbers'])
            layout['containers'] = boxes
            # The large yellow portal points toward the adjacent boom tile. Container-row
            # orientation is independent of this direction. Use the actual hex lattice so
            # separately exported base/tip sections meet at exactly the same coordinates.
            directions = ((0, 72), (63, 36), (63, -36), (0, -72), (-63, -36), (-63, 36))
            if 'CraneTip' in name:
                direction = int(Path(name).stem[-2:])-1
            elif 'GantryCrane' in name:
                portal = center(max(yellow, key=len))
                direction = max(range(6), key=lambda i: sum(a*b for a,b in zip(portal,directions[i]))
                                / math.hypot(*directions[i]))
            else:
                direction = None
            if direction is not None:
                dx, dy = directions[direction]
                layout['crane'] = {'direction':direction+1, 'neighbor':[dx,dy],
                                   'angle':math.degrees(math.atan2(-dx,dy)),
                                   'half_span':math.hypot(dx,dy)/2, 'tip':'CraneTip' in name}
        layouts[name] = layout
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT/'layouts.json').write_text(json.dumps(layouts, indent=2)+'\n')
    print(json.dumps({'layouts': len(layouts), 'trees': sum(len(v.get('trees', [])) for v in layouts.values()),
                      'containers': sum(len(v.get('containers', [])) for v in layouts.values()),
                      'overlapping_container_candidates_removed': sum(v.get('container_candidates_removed', 0) for v in layouts.values())}))


if __name__ == '__main__':
    main()
