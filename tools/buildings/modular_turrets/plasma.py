"""Plasma weapons (Plasma Rifle, Plasma Cannon): a coil-wound magnetic containment chamber narrowing into a flared
bell nozzle with a deep dark throat, fed by two coolant lines. They sit on the PPC capacitor housings and flanges
(ppc.py reads these tiers from its table). The chamber starts at the rear datum Y=0; plasma has no mechanical recoil.
"""
import math
# HERE, the kit folder, is set by the file that loads this one (author.py or a family module).
_ppc = {'HERE': HERE}
exec(compile((HERE/'ppc.py').read_text(encoding='utf-8'), 'ppc', 'exec'), _ppc)

# Housing and pivot as ppc.TIERS ('fin' sizes the flange); chamber radius and length, coil count, bell radius and length.
TIERS = {
    'rifle': dict(L=7.2, w=4.0, h=3.7, cy=3.5, cz=6.8, fin=1.05, chamber=1.0, chamber_len=5.6, coils=4, bell=1.35,
                  bell_len=2.2),
    'cannon': dict(L=8.4, w=4.6, h=4.1, cy=4.0, cz=6.9, fin=1.3, chamber=1.25, chamber_len=6.6, coils=5, bell=1.7,
                   bell_len=2.7),
}
_ppc['TIERS'].update(TIERS)
layout, mantlet, body = _ppc['layout'], _ppc['mantlet'], _ppc['body']


def barrel(ref, family, variant, lod):
    """Containment chamber with coil bands, neck and bell nozzle. Returns the nozzle mouth."""
    t = TIERS[variant]
    ch, n, length, bell, bl = t['chamber'], t['coils'], t['chamber_len'], t['bell'], t['bell_len']
    steps = [(0, .9 * ch, 'steel'), (.6, .9 * ch, 'steel'), (.6, ch, 'steel')]
    pitch = (length - 1.6) / n
    for k in range(n if lod == 0 else 2):
        y = 1.0 + k * (pitch if lod == 0 else (length - 1.6) / 2)
        steps += [(y, ch, 'dark'), (y, 1.17 * ch, 'edge'), (y + .38, 1.17 * ch, 'edge'), (y + .38, ch, 'steel')]
    end = length + .45 + bl
    steps += [(length, ch, 'steel'), (length, .62 * ch, 'steel'), (length + .45, .62 * ch, 'steel'),
              (end - .3, bell, 'edge'), (end, bell, 'edge'), (end, .82 * bell, 'black'), (end - .7 * bl, .3 * bell, 'black')]
    _ppc['lathe'](ref, 'Plasma containment chamber', steps, lod, 14 if lod == 0 else 8)
    if lod == 0:
        for side in (-1, 1):
            a = math.pi / 2 + side * math.pi / 4
            x, z = 1.22 * ch * math.cos(a), 1.22 * ch * math.sin(a)
            _ppc['_shape']['pipe'](ref, 'Coolant line', [(x, .3, z), (x, length - .3, z), (.75 * x, length + .2, .75 * z)],
                                   .1 * ch, lod, 'steel')
    return [(0, end, 0)]
