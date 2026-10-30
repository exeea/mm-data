"""Flamers (light, heavy): a pressurised fuel cylinder behind a long nozzle with a flared tip and a pilot igniter.
Both stay within the head's low auxiliary pads. On the roof they ride the machine gun's receiver
(exposed_weapons.py). The cylinder starts at the rear datum Y=0; flamers have no mechanical recoil.
"""
# HERE, the kit folder, is set by the file that loads this one (author.py or a family module).
_ex = {'HERE': HERE}
exec(compile((HERE/'exposed_weapons.py').read_text(encoding='utf-8'), 'exposed_weapons', 'exec'), _ex)

SCALE = {'light': 1.0, 'heavy': 1.2}


def layout(family, variant):
    return _ex['layout']('machine-gun', variant)


def body(ref, family, variant, lod):
    return _ex['body'](ref, 'machine-gun', variant, lod)


def lathe(ref, name, steps, lod):
    return ref.ring(name, [(y, r) for y, r, _ in steps], steps[0][2], 12 if lod == 0 else 6, (0, 0), axis='Y',
                    bands=[m for _, _, m in steps[:-1]])


def scaled(ref, variant, start):
    for obj in ref.PARTS[start:]:
        for v in obj.data.vertices:
            v.co *= SCALE[variant]
    return ref.PARTS[start:]


def barrel(ref, family, variant, lod):
    """Fuel cylinder with straps, nozzle, igniter and its feed line. Returns the nozzle tip."""
    start = len(ref.PARTS)
    lathe(ref, 'Flamer projector', [(0, .46, 'steel'), (.25, .52, 'edge'), (.4, .52, 'dark'), (1.5, .52, 'edge'),
                                    (1.65, .4, 'steel'), (1.65, .27, 'steel'), (3.6, .25, 'steel'), (3.6, .34, 'edge'),
                                    (4.1, .44, 'edge'), (4.1, .29, 'black'), (3.75, .2, 'black')], lod)
    # The pilot igniter rides on top, fed by the line along the nozzle.
    ref.block('Pilot igniter', (0, 3.35, .32), (.2, .5, .18), 'dark', cut=.05, bevel=0)
    if lod == 0:
        for y in (.7, 1.15):
            lathe(ref, 'Cylinder strap', [(y, .5, 'steel'), (y, .56, 'steel'), (y + .12, .56, 'steel'),
                                          (y + .12, .5, 'steel')], lod)
        ref.block('Feed valve', (0, 1.72, .33), (.3, .3, .24), 'steel', cut=.06, bevel=0)
        ref.ring('Fuel feed line', [(1.8, .07), (3.1, .07)], 'black', 6, (0, .33), axis='Y')
    scaled(ref, variant, start)
    return [(0, 4.1 * SCALE[variant], 0)]


def mantlet(ref, family, variant, lod):
    """Front pad installation: a small armored collar around the cylinder root."""
    start = len(ref.PARTS)
    lathe(ref, 'Projector collar', [(0, .56, 'dark'), (.25, .56, 'armor'), (.25, .46, 'armor')], lod)
    return scaled(ref, variant, start)
