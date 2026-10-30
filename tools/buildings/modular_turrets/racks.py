"""Launcher racks: tube pitch, columns per tube count and launcher length for every missile kind.

The launcher body (weapon_shapes.missile) and its external mounts (pod_mounts) read the same rack, so a cassette
always fits its yoke or arm. A roof yoke is the cassette plus 2.45 wide and its socket 8.2, so no rack exceeds 5.75.
"""
RACKS = {
    'lrm': dict(cell=1.0, cols={5: 3, 10: 5, 15: 5, 20: 5}, length=8.4),
    'srm': dict(cell=1.45, cols={2: 1, 4: 2, 6: 3}, length=9.0),
    # Multi-missile launchers fire both SRM and LRM rounds: tubes between the two.
    'mml': dict(cell=1.22, cols={3: 3, 5: 3, 7: 4, 9: 3}, length=8.8),
    # Medium-range missiles: many small unguided tubes in deep cassettes.
    'mrm': dict(cell=.72, cols={10: 5, 20: 5, 30: 6, 40: 7}, length=8.0),
    'atm': dict(cell=1.25, cols={3: 3, 6: 3, 9: 3, 12: 4}, length=8.6),
    # 'Mech mortars: short, wide tubes.
    'mortar': dict(cell=1.6, cols={1: 1, 2: 2, 4: 2, 8: 3}, length=5.6),
    # Artillery missiles: Arrow IV's four large tubes, one Thunderbolt rail.
    'arrow': dict(cell=1.8, cols={4: 2}, length=9.4),
    'thunderbolt': dict(cell=2.5, cols={1: 1}, length=10.2),
}


def dimensions(kind, count):
    """Width and length of the launcher cassette."""
    rack = RACKS[kind]
    return rack['cols'][count] * rack['cell'] + .65, rack['length']


def name(kind, count):
    """Module name: single-size racks drop the tube count."""
    return {'arrow': 'arrow-iv', 'thunderbolt': 'thunderbolt'}.get(kind, f'{kind}-{count}')
