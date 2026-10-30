"""Hyper-assault Gauss rifles (HAG/20, /30, /40): four barrels in a square block, as the Meks draw them, threaded
through square accelerator coils between two rails, each with its own muzzle collar. They fire rapid streams of
smaller slugs (MegaMek: 10, 13 and 16 t, 6, 8 and 10 slots, 24 hexes), so the barrels are long and the receivers
grow from the Light Gauss's to the Gauss's. The capacitor housing and mantlet are gauss.py's.
The barrels start at the rear datum Y=0 and belong to the recoil joint.
"""
import math
# HERE, the kit folder, is set by the file that loads this one (author.py or a family module).
_gauss = {'HERE': HERE}
exec(compile((HERE/'gauss.py').read_text(encoding='utf-8'), 'gauss', 'exec'), _gauss)

# Receiver and pivot as ballistic.CALIBRES (named apart from its AC/20); barrel length, tube radius and spacing, coil
# count and length.
TIERS = {
    'hag-20': dict(L=11.0, w=4.4, h=3.9, cy=4.6, cz=6.8, barrel=21.0, tube=.34, pitch=.95, jacket=1.4, coils=6, coil_len=.8),
    'hag-30': dict(L=11.5, w=4.6, h=4.1, cy=4.8, cz=6.9, barrel=21.5, tube=.4, pitch=1.1, jacket=1.55, coils=7, coil_len=.9),
    'hag-40': dict(L=12.0, w=4.8, h=4.4, cy=4.9, cz=6.9, barrel=22.0, tube=.46, pitch=1.25, jacket=1.7, coils=7,
                   coil_len=1.0),
}
_gauss['register'](TIERS)
# The barrel cluster turns about its axis while firing (author.py gives it a spin joint).
SPIN = True
layout, mantlet, body = _gauss['layout'], _gauss['mantlet'], _gauss['body']
_shape = _gauss['_ac']['_shape']


def barrel(ref, family, variant, lod):
    """Square breech block, four collared barrels, square coils and rails. Returns the four muzzles."""
    t = TIERS[variant]
    j, tube, half, length = t['jacket'], t['tube'], t['pitch'] / 2, t['barrel']
    square = math.pi / 4
    ref.ring('HAG breech block', [(0, .9 * j), (1.6, .9 * j), (1.6, .7 * j)], 'steel', 4, (0, 0), axis='Y', phase=square,
             bands=['steel', 'dark'])
    tips = []
    for x in (-half, half):
        for z in (half, -half):
            ref.ring('HAG barrel', [(1.2, tube), (length - .6, tube), (length - .6, 1.25 * tube), (length, 1.25 * tube),
                                    (length, .6 * tube)], 'steel', 8 if lod == 0 else 6, (x, z), axis='Y',
                     bands=['steel', 'edge', 'edge', 'steel'])
            tips.append((x, length, z))
    radius = (half + tube + .18) / math.cos(square)
    flat = _gauss['coils'](ref, 2.4, length - 1.9, radius, t['coils'], t['coil_len'], lod, sides=4)
    # Rails run between the barrel pairs, above and below, from the breech block to the muzzle collars.
    for angle in (math.pi / 2, -math.pi / 2):
        _shape['radial_bar'](ref, 'Accelerator rail', angle, .1 / (flat + .15), .1, flat + .15, 1.4, length - .6, 'edge')
    return tips
