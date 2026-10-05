"""Inventory the 3D board's actual include graph and every source-image variant.

This reads tileset declarations; it does not reimplement HexTileset's matching.
Runtime coverage is checked separately through BoardArtwork in the Java tests.
"""
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TILES = ROOT / 'data/models/board/tileset'
OUT = ROOT / 'tools/board-models/scenery'

DECORATIVE = {'fluff', 'ground_fluff', 'road_fluff', 'water_fluff', 'fortified',
              'geyser', 'solaris_elevator', 'industrial_elevator', 'rubble'}


def classify(row):
    source = row['image']
    types = {t.split(':')[0] for t in row['terrain'].split(';') if t}
    asset = 'scenery/' + str(Path(source).with_suffix('')).replace('\\', '/') if source else ''
    structure = 'buildings/' + str(Path(source).with_suffix('')).replace('\\', '/') if source else ''
    decorative = bool(types & DECORATIVE) or 'road_trees' in source
    levels = {t.split(':')[0]: t.split(':')[1] for t in row['terrain'].split(';') if ':' in t}
    native = ('rough' in types or levels.get('fluff') == '12' and 'woods' in types
              or 'Transitions/' in source or levels.get('road_fluff') == '1' and 'road' in types)
    if not source or source.endswith('/blank.png'):
        return 'blank', 'intentionally transparent', False, ''
    if {'building', 'fuel_tank', 'heavy_industrial'} & types and (ROOT/'data/models/board'/(structure+'.glb')).is_file():
        return 'existing-model', 'existing structure GLB selected by original artwork', False, structure
    if native:
        return 'native', 'existing terrain geometry/material or vegetation', False, ''
    if (ROOT/'data/models/board'/(asset+'.glb')).is_file():
        return 'new-model', 'authored volume replacing the selected image layer', True, asset
    if 'road' in types and 'road_fluff' in types and levels.get('road') in ('1', '2', '3', '4'):
        return 'native-road', 'shared road geometry/material replaces painted road-fluff surface', True, ''
    if decorative or source.startswith('Structured_Pavement/'):
        return 'decal', 'original selected alpha artwork on the finished surface', True, ''
    if types & {'sky', 'space', 'screen', 'deployment_zone', 'impassable', 'bldg_base_collapsed', 'metal_deposit'}:
        return 'marker/background', 'existing tactical/background representation; not physical scenery', False, ''
    return 'native', 'existing terrain, road, bridge, liquid, vegetation or effect path', False, ''


def family(row):
    source = row['image']
    for part in ('SMV_Seaport', 'SMV_LandingPads', 'SMV_GroundSymbols', 'SMV_Letters', 'SMV_Fluff', 'Structured_Pavement'):
        if part in source: return part
    if source.startswith('fluff/'):
        return 'fluff/' + re.sub(r'[_\d]+[ab]?$', '', Path(source).stem)
    if 'road_trees' in source: return 'roads / roadside trees'
    if '/orbitalguns/' in source:return 'orbital guns'
    if 'rubble' in source and 'path' in source:return 'rubble / cleared paths'
    if 'road_fluff' in row['terrain']: return 'roads / decorative surface variants'
    if 'hq_fluff/rail' in source:return 'rail / track markings'
    if source.startswith('runway/'):return 'runway / markings'
    return row['terrain'].split(';')[0].split(':')[0] or 'base materials'


def declarations(root=TILES, entry='saxarba.tileset'):
    rows, visited = [], set()

    def scan(name):
        if name in visited:
            return
        visited.add(name)
        for number, line in enumerate((root / name).read_text(encoding='utf-8-sig', errors='replace').splitlines(), 1):
            text = line.strip()
            quoted = re.findall(r'"([^"]*)"', text)
            if text.startswith('include ') and quoted:
                scan(quoted[0])
            elif text.startswith(('base ', 'super ', 'ortho ')) and len(quoted) >= 3:
                kind, elevation = text.split()[:2]
                for image in quoted[2].split(';'):
                    rows.append(dict(file=name, line=number, kind=kind, elevation=elevation,
                                     terrain=quoted[0], theme=quoted[1], image=image,
                                     exists=(root / re.sub(r'\([^)]*\)$', '', image)).is_file()))

    scan(entry)
    return rows, sorted(visited)


def main():
    rows, includes = declarations()
    OUT.mkdir(parents=True, exist_ok=True)
    for row in rows:
        after, reason, missing, model = classify(row)
        row.update(implementation=after, reason=reason, missing_before=missing, family=family(row), model=model)
    (OUT / 'tile-inventory.json').write_text(json.dumps(dict(includes=includes, tiles=rows), indent=2) + '\n')
    gaps = [r for r in rows if r['missing_before']]
    (OUT / 'missing-before.json').write_text(json.dumps(gaps, indent=2) + '\n')
    summary = {}
    for row in rows:
        category = row['implementation']
        summary.setdefault(category, set()).add(row['image'])
    groups = {}
    for row in gaps:
        value = groups.setdefault(row['family'], dict(images=set(), modes=set()))
        value['images'].add(row['image']); value['modes'].add(row['implementation'])
    report = ['# Board tile coverage audit', '',
              'Runtime scope: `data/models/board/tileset/saxarba.tileset` and its complete include graph. '
              'The 3D board always uses this tileset, independently of the Swing tileset preference.', '',
              f'- {len(includes)} included files; {len(rows)} image alternatives across declarations; '
              f'{len(set(r["image"] for r in rows) - {""})} nonempty image references.',
              f'- {len({r["image"] for r in gaps})} previously unsupported source images: '
              f'{len(summary.get("new-model", []))} authored scenery models, '
              f'{len(summary.get("decal", []))} decal images and {len(summary.get("native-road", []))} native-road variants.',
              '- `tile-inventory.json` enumerates every declaration, variant, theme, source line, implementation and model path.',
              '- `missing-before.json` enumerates the affected declarations, including every rotation and shuffled image alternative.',
              '- Declaration inventory is not a replacement tileset matcher. Tests capture selected layers through HexTileset.', '',
              '| Previously missing family | Unique images | Implementation |', '| --- | ---: | --- |']
    for name, group in sorted(groups.items()):
        report.append(f'| {name} | {len(group["images"])} | {", ".join(sorted(group["modes"]))} |')
    report += ['', 'Counts describe visual coverage, not art equivalence: existing native ground, roads, woods and '
               'buildings use their existing 3D materials and geometry. Blank wildcard rules intentionally draw nothing.', '',
               'Decals preserve exact source art. Authored scenery preserves object family/orientation and uses simplified '
               'static meshes; it does not add game terrain or moving trains, animals or machinery. Geyser water, '
               'steam and lava animate in the shared board renderer; eruption state remains owned by the game.', '',
               'Parking-road sprites provide only cars and street furniture as meshes; their routes use the shared road engine. '
               'Pools use continuous closed rims and one shared static water texture through the ordinary model pass. '
               'Geometry checks are recorded in `geometry-check.json`.', '',
               'The nine legacy Swing tilesets are inventoried separately in `legacy-tilesets.json`; their artwork is '
               'not an additional selectable 3D tileset. Their board terrain still resolves through the active Saxarba rules.', '']
    (OUT/'coverage.md').write_text('\n'.join(report))
    legacy = {}
    for entry in sorted((ROOT/'data/images/hexes').glob('*.tileset')):
        try:
            other, files = declarations(entry.parent, entry.name)
            legacy[entry.name] = dict(includes=files, tiles=other)
        except FileNotFoundError as error:
            legacy[entry.name] = dict(error=str(error))
    (OUT/'legacy-tilesets.json').write_text(json.dumps(legacy, indent=2)+'\n')
    print(json.dumps({'coverage': {k:len(v) for k,v in summary.items()},
                      'previously_missing_images':len({r['image'] for r in gaps}),
                      'legacy_tilesets':{k:len(v.get('tiles',[])) for k,v in legacy.items()}}))
    decorative = [r for r in rows if re.search(r'(^|;)(fluff|road_fluff|ground_fluff|water_fluff|pavement|rubble|fortified|geyser|rapids|solaris_elevator):', r['terrain'])]
    grouped = {}
    for row in decorative:
        key = row['file']
        value = grouped.setdefault(key, dict(rules=set(), images=set(), examples=[]))
        value['rules'].add(row['terrain'])
        value['images'].add(row['image'])
        if len(value['examples']) < 4:
            value['examples'].append((row['terrain'], row['image']))
    print(json.dumps(dict(includes=len(includes), rows=len(rows), images=len({r['image'] for r in rows}),
                         missing=sorted({r['image'] for r in rows if not r['exists']}),
                         decorative={k: dict(rules=len(v['rules']), images=len(v['images']), examples=v['examples'])
                                     for k, v in grouped.items()}), indent=2))

    if '--contacts' in __import__('sys').argv:
        from PIL import Image, ImageDraw
        categories = {
            'standard': lambda r: r['image'].startswith('fluff/'),
            'seaport': lambda r: 'SMV_Seaport/' in r['image'],
            'gardens': lambda r: 'SMV_Fluff/' in r['image'],
            'roads': lambda r: any(s in r['image'] for s in ('road_trees', 'roadH', 'quay_fluff')),
            'misc': lambda r: any(s in r['terrain'] for s in ('geyser:', 'fortified:', 'solaris_elevator:', 'rubble:')),
            'rail': lambda r: 'StandardRailMaglev' in r['file'],
            'landing': lambda r: 'SMV_LandingPads' in r['file'],
        }
        for category, predicate in categories.items():
            chosen = list({r['image']: r for r in rows if predicate(r) and r['image']}.values())
            for page in range((len(chosen) + 47) // 48):
                subset = chosen[page * 48: (page + 1) * 48]
                sheet = Image.new('RGB', (6 * 182, ((len(subset) + 5) // 6) * 182), '#44484e')
                draw = ImageDraw.Draw(sheet)
                for n, row in enumerate(subset):
                    im = Image.open(TILES / row['image']).convert('RGBA')
                    im.thumbnail((168, 136))
                    if im.width == 84:
                        im = im.resize((168, 144), Image.Resampling.NEAREST)
                    x, y = (n % 6) * 182, (n // 6) * 182
                    sheet.paste(im, (x, y), im)
                    draw.text((x, y + 145), row['terrain'][:29], fill='white')
                    draw.text((x, y + 158), Path(row['image']).stem[-27:], fill='white')
                sheet.save(OUT / f'contact-{category}-{page + 1}.png')


if __name__ == '__main__':
    main()
