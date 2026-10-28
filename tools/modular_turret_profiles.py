"""Optional authored turret profiles in the shared, canonical equipment catalogue.

The Mek weapon rule book (unit-models/weapons.json) classifies each weapon; this table only names the turret module
for each rule, so turrets and Meks never disagree about what a weapon is. Sizes come from the rack: autocannons and
rotary cannons take their calibre tier, launchers the smallest authored rack holding their tubes. Infantry weapons
and other unsupported equipment deliberately retain their existing model and emitters.
"""
from pathlib import Path

from unit_weapon_shapes import rule_for

PREFIX = 'buildings/turrets/modular/'
# Launcher racks and their authored tube counts are the turret kit's own table.
RACKS = {}
exec(compile((Path(__file__).resolve().parent/'buildings/modular_turrets/racks.py').read_text(encoding='utf-8'),
             'racks', 'exec'), RACKS)
# Mek rule id -> turret module, or a rack kind from racks.py.
MODULES = {
    'machine-gun': 'machine-gun', 'machine-gun-light': 'machine-gun', 'machine-gun-heavy': 'machine-gun',
    'ams': 'machine-gun', 'ballistic-small': 'machine-gun',
    'autocannon-2': 'autocannon', 'autocannon-5': 'autocannon', 'autocannon-10': 'autocannon',
    'autocannon-20': 'autocannon', 'rotary-2': 'rotary', 'rotary-5': 'rotary', 'rotary-10': 'rotary',
    'rotary-20': 'rotary',
    'artillery-thumper': 'artillery-light', 'artillery-sniper': 'artillery', 'artillery-long-tom': 'artillery-heavy',
    'gauss-small': 'gauss-light', 'gauss-light': 'gauss-light', 'gauss': 'gauss', 'gauss-heavy': 'gauss-heavy',
    'hag-20': 'hag-20', 'hag-30': 'hag-30', 'hag-40': 'hag-40',
    'laser-ams': 'laser-small', 'laser-small': 'laser-small', 'laser-medium': 'laser-medium',
    'laser-large': 'laser-large', 'blazer-light': 'laser-medium', 'blazer': 'laser-large',
    # Chemical lasers of every size and other energy weapons show the medium laser; TAG and C3 masters a small lens.
    'energy': 'laser-medium', 'chemical-laser-small': 'laser-medium', 'chemical-laser-medium': 'laser-medium',
    'chemical-laser-large': 'laser-medium', 'tag-light': 'laser-small', 'tag': 'laser-small',
    'ppc-light': 'ppc-light', 'ppc-snub': 'ppc-light', 'ppc': 'ppc',
    'ppc-heavy': 'ppc-heavy', 'tsemp': 'ppc-heavy',
    'plasma-rifle': 'plasma-rifle', 'plasma-cannon': 'plasma-cannon',
    'flamer': 'flamer', 'flamer-er': 'flamer', 'flamer-heavy': 'flamer-heavy',
    'lrm': 'lrm', 'rocket-launcher': 'lrm', 'srm': 'srm', 'narc': 'srm', 'mml': 'mml', 'mrm': 'mrm', 'atm': 'atm',
    'mortar': 'mortar', 'arrow-iv': 'arrow', 'arrow-iv-clan': 'arrow', 'arrow-iv-bomb': 'arrow',
    'cruise-missile': 'arrow', 'thunderbolt-5': 'thunderbolt', 'thunderbolt-10': 'thunderbolt',
    'thunderbolt-15': 'thunderbolt', 'thunderbolt-20': 'thunderbolt',
}
LAUNCHERS = {RACKS['name'](kind, count) for kind, rack in RACKS['RACKS'].items() for count in rack['cols']}


def module_for(item):
    rule = rule_for(dict(item, location='mount', rear=False))
    module = MODULES.get(rule['id']) if rule else None
    rack = item.get('rackSize', 0)
    if module == 'autocannon':
        # Rack size is the calibre: AC/2, AC/5, AC/10 and AC/20 barrels, nearest tier for the others.
        return 'autocannon-' + ('2' if rack <= 3 else '5' if rack <= 6 else '10' if rack <= 12 else '20')
    if module == 'rotary':
        return 'rotary-' + ('2' if rack <= 3 else '5')
    if module in RACKS['RACKS']:
        # The smallest authored rack holding all tubes, else the largest.
        counts = sorted(RACKS['RACKS'][module]['cols'])
        return RACKS['name'](module, next((count for count in counts if rack <= count), counts[-1]))
    return module


def profiles_for(item):
    carried = 'F_INFANTRY' in item.get('flags', ())
    module = module_for(item) if item['policy'] == 'WEAPON' and not carried else None
    if not module:
        return {}
    launcher = module in LAUNCHERS
    profiles = {'turret': PREFIX + module + '.json',
                'turret-compact': PREFIX + ('autocannon-compact' if module.startswith('autocannon') else module) + '.json'}
    # One weapon module in every installation: the front bay, the roof mounts and, a launcher, the side arms.
    profiles['turret-exposed'] = PREFIX + module + '.json'
    if launcher:
        profiles['turret-arm'] = PREFIX + module + '.json'
    return profiles


def add_profiles(catalog, mappings):
    for item in catalog['equipment']:
        entry = mappings.get(item['internalName'])
        profiles = profiles_for(item)
        if entry is not None and (profiles or 'profiles' in entry):
            # Regenerated turret profiles replace earlier ones; the Mek profiles stay.
            kept = {role: asset for role, asset in entry.get('profiles', {}).items() if not role.startswith('turret')}
            entry['profiles'] = {**kept, **profiles}


if __name__ == '__main__':
    import json
    root = Path(__file__).resolve().parent.parent
    source = json.loads((root/'.work/modular-models/equipment.json').read_text(encoding='utf-8'))
    path = root/'data/models/units/modular/equipment.json'
    target = json.loads(path.read_text(encoding='utf-8'))
    add_profiles(source, target['equipment'])
    path.write_text(json.dumps(target, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    print('Authored turret profiles:', sum('turret' in x.get('profiles', {}) for x in target['equipment'].values()))
