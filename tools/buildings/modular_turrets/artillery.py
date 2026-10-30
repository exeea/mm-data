"""Tube artillery: Thumper, Sniper and Long Tom howitzers and their direct-fire cannons (light, standard, heavy).

A long howitzer barrel (breech jacket, tapered tube, fume extractor, double-baffle muzzle brake) on the autocannon
receivers and mantlets: ballistic.py reads these tiers from its calibre table. The barrel starts at
the rear datum Y=0 and belongs to the recoil joint.
"""
import math
# HERE, the kit folder, is set by the file that loads this one (author.py or a family module).
_ac = {'HERE': HERE}
exec(compile((HERE/'ballistic.py').read_text(encoding='utf-8'), 'ballistic', 'exec'), _ac)

# As ballistic.CALIBRES (receiver, pivot, barrel and brake), plus the fume extractor's length.
TIERS = {
    'light': dict(L=11.0, w=4.4, h=4.0, cy=4.8, cz=6.9, barrel=24.0, r=.74, jacket=1.3, brake=1.32, bore=.5,
                  brake_len=3.2, extractor=1.8),
    'standard': dict(L=11.6, w=4.6, h=4.2, cy=4.9, cz=6.9, barrel=27.0, r=.86, jacket=1.5, brake=1.55, bore=.6,
                     brake_len=3.6, extractor=2.1),
    'heavy': dict(L=12.0, w=4.8, h=4.4, cy=4.9, cz=6.9, barrel=31.0, r=1.0, jacket=1.75, brake=1.8, bore=.72,
                  brake_len=4.0, extractor=2.4),
}
_ac['CALIBRES'].update(TIERS)
layout, mantlet, body = _ac['layout'], _ac['mantlet'], _ac['body']


def barrel(ref, family, variant, lod):
    """Breech jacket, long tapered tube, fume extractor and double-baffle brake. Returns the muzzle tip."""
    c = TIERS[variant]
    j, r, rb, bore, length, e = c['jacket'], c['r'], c['brake'], c['bore'], c['barrel'], c['extractor']
    jacket_end = .9 + .2 * length
    start = length - c['brake_len']
    ye = jacket_end + .45 * (start - jacket_end)
    if lod:
        _ac['lathe'](ref, 'Howitzer barrel', [(0, j, 'edge'), (jacket_end - .4, j, 'steel'), (jacket_end, 1.1 * r, 'steel'),
                                              (ye, 1.02 * r, 'steel'), (ye, 1.5 * r, 'edge'), (ye + e, 1.5 * r, 'steel'),
                                              (ye + e, .98 * r, 'steel'), (start, .92 * r, 'steel'), (start, rb, 'black'),
                                              (length - .4, rb, 'edge'), (length, .92 * rb, 'steel'), (length, bore, 'black'),
                                              (length - .6, bore, 'black')], lod)
        return [(0, length, 0)]
    # Two baffle chambers open to the sides; a ring between them carries the second baffle.
    mid = start + .5 + (c['brake_len'] - .95) / 2
    steps = [(0, .9 * j, 'steel'), (.9, .9 * j, 'steel'), (.9, j, 'edge'), (1.4, j, 'dark'), (1.4, 1.06 * j, 'edge'),
             (1.75, 1.06 * j, 'dark'), (1.75, j, 'dark'), (jacket_end - .9, j, 'edge'), (jacket_end - .9, 1.06 * j, 'edge'),
             (jacket_end - .55, 1.06 * j, 'dark'), (jacket_end - .55, j, 'steel'), (jacket_end, 1.12 * r, 'steel'),
             (ye, 1.04 * r, 'steel'), (ye + .3, 1.5 * r, 'edge'), (ye + .3 + e, 1.5 * r, 'steel'), (ye + .6 + e, .98 * r, 'steel'),
             (start - .3, .92 * r, 'steel'), (start, .9 * rb, 'steel'), (start + .15, rb, 'edge'), (start + .5, rb, 'edge'),
             (start + .5, .7 * rb, 'black'), (mid - .2, .7 * rb, 'edge'), (mid - .2, rb, 'edge'), (mid + .2, rb, 'edge'),
             (mid + .2, .7 * rb, 'black'), (length - .45, .7 * rb, 'edge'), (length - .45, rb, 'edge'),
             (length - .08, rb, 'steel'), (length, .92 * rb, 'steel'), (length, bore, 'black'), (length - 1.0, bore, 'black')]
    _ac['lathe'](ref, 'Howitzer barrel', steps, lod)
    for y0, y1 in ((start + .5, mid - .2), (mid + .2, length - .45)):
        _ac['slots'](ref, 'Brake baffle cheek', y0, y1, .7 * rb, rb, 2, .5)
    _ac['recoil_clamp'](ref, c, lod)
    # Evacuator fill ports on the fume extractor.
    for k in range(4):
        a = k * math.pi / 2 + math.pi / 4
        _ac['_shape']['stud'](ref, (1.5 * r * math.cos(a), ye + .3 + e / 2, 1.5 * r * math.sin(a)),
                              (math.cos(a), 0, math.sin(a)), .09 * r)
    return [(0, length, 0)]
