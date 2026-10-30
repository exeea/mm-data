"""Gauss rifles (light, standard, heavy): a barrel threaded through massive octagonal accelerator coils, held by top
and bottom rails, with a plain flared muzzle; no brake, no fume extractor, since nothing burns.

A Gauss rifle outweighs an autocannon of its bulk and reaches much further (MegaMek: Gauss 15 t, 7 slots, 22 hexes;
AC/10 12 t, 7 slots, 15 hexes; AC/20 14 t, 10 slots, 9 hexes). Each tier therefore takes an autocannon-sized bore on a
long barrel. The Light Gauss reaches furthest of all (25 hexes); the Heavy Gauss, heaviest and shortest-ranged,
carries the biggest coils on a shorter barrel. Its capacitors, not its inert slugs, explode when hit: exposed
receivers are the PPC's armored capacitor housing, and a front bay keeps the autocannon's cast mantlet. The barrel starts at the rear datum Y=0.
"""
import math
# HERE, the kit folder, is set by the file that loads this one (author.py or a family module).
_ac, _ppc = {'HERE': HERE}, {'HERE': HERE}
exec(compile((HERE/'ballistic.py').read_text(encoding='utf-8'), 'ballistic', 'exec'), _ac)
exec(compile((HERE/'ppc.py').read_text(encoding='utf-8'), 'ppc', 'exec'), _ppc)

# Receiver and pivot as ballistic.CALIBRES; barrel length and tube radius, coil radius, count and length.
TIERS = {
    'light': dict(L=11.0, w=4.2, h=3.8, cy=4.5, cz=6.8, barrel=25.0, r=.72, jacket=1.3, coil=1.4, coils=8, coil_len=1.0),
    'standard': dict(L=12.0, w=4.8, h=4.4, cy=4.9, cz=6.9, barrel=23.0, r=.95, jacket=1.65, coil=1.8, coils=8,
                     coil_len=1.2),
    'heavy': dict(L=12.5, w=5.2, h=4.6, cy=4.9, cz=6.95, barrel=19.0, r=1.2, jacket=1.8, coil=2.2, coils=6,
                  coil_len=1.45),
}
# A capacitor bank lower than the PPC's keeps the taller receivers within the 11-high roof sockets.
CAPACITOR_BOX = .9


def register(tiers):
    """The autocannon layout and mantlet, and the PPC capacitor housing, read these tiers."""
    _ac['CALIBRES'].update(tiers)
    _ppc['TIERS'].update({name: dict(tier, box=CAPACITOR_BOX) for name, tier in tiers.items()})


register(TIERS)
layout, mantlet = _ac['layout'], _ac['mantlet']
body = _ppc['body']


def coils(ref, first, last, radius, count, length, lod, sides=8):
    """Accelerator coils of `sides` flats spread from first to last, studded on their side flats; LOD1 keeps every
    other one. Returns the flats' distance from the axis."""
    pitch = (last - first - length) / max(1, count - 1)
    flat = radius * math.cos(math.pi / sides)
    for k in range(0, count, 1 if lod == 0 else 2):
        y = first + k * pitch
        _ac['_shape']['harden'](ref, ref.ring('Accelerator coil', [(y, .82 * radius), (y + .1, radius),
                                                                    (y + length - .1, radius), (y + length, .82 * radius)],
                                              'dark', sides, (0, 0), axis='Y', phase=math.pi / sides), .04)
        if lod == 0:
            for side in (-1, 1):
                _ac['_shape']['stud'](ref, (side * flat, y + length / 2, 0), (side, 0, 0), .08 * radius)
    return flat


def barrel(ref, family, variant, lod):
    """Breech sleeve, coil-wrapped barrel between two rails and a flared muzzle. Returns the muzzle tip."""
    t = TIERS[variant]
    j, r, coil, length = t['jacket'], t['r'], t['coil'], t['barrel']
    muzzle = 1.45 * r
    _ac['lathe'](ref, 'Gauss barrel', [(0, .9 * j, 'steel'), (1.2, .9 * j, 'steel'), (1.2, j, 'edge'), (1.6, j, 'dark'),
                                       (1.6, r, 'steel'), (length - .7, r, 'steel'), (length - .7, muzzle, 'edge'),
                                       (length, muzzle, 'steel'), (length, .55 * r, 'black'), (length - .8, .55 * r, 'black')],
                 lod)
    coils(ref, 2.4, length - 1.9, coil, t['coils'], t['coil_len'], lod)
    # Rails run through every coil from the breech sleeve to the muzzle collar.
    for angle in (math.pi / 2, -math.pi / 2):
        _ac['_shape']['radial_bar'](ref, 'Accelerator rail', angle, .32 * r / coil, .9 * r, 1.08 * coil, 1.4, length - .7,
                                    'edge')
    return [(0, length, 0)]
