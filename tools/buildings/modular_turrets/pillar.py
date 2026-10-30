"""Missile pillar head: a thin, squeezed armored body on the common collar and bearing, launchers on its sides.

Launcher arms mount on its flank plates (x = +-FLANK). One front bay sits on the tall glacis; the flared roof cap
seats one roof weapon on its mount. World coordinates as in shell.py (yaw at z = 2.8).
The lowest arms sit high enough that a fully depressed LRM 20 clears the bearing.
"""
import math
_shape = {}
exec(compile((HERE/'hard_surface.py').read_text(encoding='utf-8'),
             'hard_surface', 'exec'), _shape)
FRONT, TOP, FLANK = 6.0, 19.8, 3.6
ARMS = {'arm-left': (-1, 13.0), 'arm-right': (1, 13.0), 'arm-left-0': (-1, 9.6), 'arm-left-1': (-1, 16.4),
        'arm-right-0': (1, 9.6), 'arm-right-1': (1, 16.4)}
LAMP = (0, -6.6, 16.8)


def shell(ref, lod):
    detail = lod == 0
    H = _shape['harden']
    # The same rotating bearing as the broad heads.
    ref.ring('Bearing shadow', [(2.75, 9.75), (3.15, 9.75)], 'black', 16 if detail else 12)
    ref.ring('Rotating bearing', [(3.05, 9.6), (3.55, 9.6), (5.7, 7.9)], 'dark', 16 if detail else 8)
    if detail:
        for i in range(8):
            a = i * math.pi / 4
            ref.radial_panel('Bearing segmented skirt', a, 5.6, 3.65, 5.5, 9.18, 7.85, .27, 'dark')
            ref.radial_panel('Bearing recessed panel', a, 3.8, 3.85, 5.25, 9.33, 8.1, .04, 'armor')
    # A broad armored foot spreads the thin body onto the bearing.
    H(ref, ref.loft('Pillar foot', [[(x, y, z) for x, y in ref.clipped(w, d, c)] for z, w, d, c in
                                    ((5.4, 11.0, 12.6, 3.0), (6.9, 7.4, 12.0, 2.0))], 'armor'), .06)
    ref.loft('Pillar core', [[(x, y, z) for x, y in ref.clipped(w, d, c)] for z, w, d, c in
                             ((6.0, 6.6, 11.8, 1.7), (18.4, 6.6, 11.4, 1.7), (19.0, 5.6, 9.6, 1.4))], 'dark')
    # Flank plates carry the launcher arms; pale covers and bolts break them up.
    for s in (-1, 1):
        H(ref, ref.block('Pillar flank armor', (s * (FLANK - .35), -.3, 12.6), (.7, 10.4, 12.0), cut=.2, bevel=0), .07)
        H(ref, ref.block('Pillar corner armor', (s * 3.05, 5.35, 11.4), (1.1, 1.4, 11.2), cut=.4, bevel=0), .06)
        ref.block('Flank service cover', (s * (FLANK + .03), -4.1, 18.0), (.1, 2.0, .9), 'pale', cut=.12, bevel=0)
        ref.block('Flank service cover', (s * (FLANK + .03), -4.1, 7.4), (.1, 2.0, .9), 'pale', cut=.12, bevel=0)
        if detail:
            for y in (-5.1, 4.5):
                for z in (7.0, 18.2):
                    _shape['stud'](ref, (s * FLANK, y, z), (s, 0, 0), .1)
            ref.block('Flank seam', (s * (FLANK + .01), -.3, 11.3), (.04, 10.6, .12), 'black', cut=0, bevel=0)
            ref.block('Flank seam', (s * (FLANK + .01), -.3, 14.7), (.04, 10.6, .12), 'black', cut=0, bevel=0)
    # Tall glacis with the front bay and auxiliary pads, a sloped brow and the armored optic.
    H(ref, ref.block('Pillar front glacis', (0, FRONT - .45, 11.4), (6.2, .9, 11.6), cut=.5, bevel=0), .06)
    ref.slab('Pillar brow', [(-3.0, FRONT, 17.2), (3.0, FRONT, 17.2), (2.4, 4.4, TOP - .4), (-2.4, 4.4, TOP - .4)], .8)
    ref.block('Optic armored brow', (0, 5.2, 18.0), (3.2, 2.2, 2.0), cut=.55, bevel=.05)
    ref.block('Optic bezel', (0, 6.42, 17.9), (2.1, .36, 1.75), 'edge', cut=.3, bevel=.025)
    ref.block('Optic black well', (0, 6.62, 17.9), (1.7, .12, 1.45), 'black', cut=.18, bevel=0)
    ref.ring('Optic lens metal ring', [(6.69, .6), (6.82, .6), (6.86, .48), (6.69, .48)], 'steel', 12 if detail else 8,
             (0, 17.9), axis='Y')
    ref.ring('Red lens', [(6.7, .46), (6.8, .46), (6.84, .39)], 'red', 12 if detail else 8, (0, 17.9), axis='Y')
    ref.bolt((0, 6.8, 17.9), 'Y', 'lens', .12)
    # The roof cap flares past the flanks so a roof weapon's mount seats on it.
    H(ref, ref.loft('Pillar roof cap', [[(x, y, z) for x, y in ref.clipped(w, d, c)] for z, w, d, c in
                                        ((18.3, 6.8, 11.2, 1.7), (18.9, 8.6, 11.8, 2.0), (TOP, 8.2, 11.0, 1.9))],
                    'armor'), .06)
    ref.block('Roof hatch seam', (0, -.6, TOP + .02), (4.9, 5.9, .06), 'black', cut=.8, bevel=0)
    ref.block('Pillar roof hatch', (0, -.6, TOP + .2), (4.6, 5.6, .4), 'pale', cut=.75, bevel=.05)
    # Rear armor with a louvred vent and the searchlight pedestal.
    H(ref, ref.block('Pillar rear armor', (0, -5.65, 12.0), (6.0, .8, 11.0), cut=.5, bevel=0), .06)
    ref.block('Searchlight rear pedestal', (LAMP[0], LAMP[1] + .2, LAMP[2] - .9), (2.2, 1.6, 1.4), cut=.3, bevel=.03)
    if detail:
        ref.block('Rear vent inset', (0, -6.07, 9.6), (4.6, .1, 2.0), 'black', cut=.3, bevel=0)
        for i in range(5):
            ref.block('Cooling louver', (-1.8 + i * .9, -6.14, 9.6), (.36, .14, 1.6), 'dark', cut=0, bevel=0)
        for x in (-2.0, 2.0):
            for y in (-2.9, 1.7):
                ref.bolt((x, y, TOP + .02))
