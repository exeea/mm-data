"""PPCs: a long radiator-finned accelerator ending in a bulb nose, behind a boxy capacitor housing.

Light, standard and heavy tiers share one design (concepts/concept-ppc.png). The barrel assembly starts at the
rear datum Y=0: bolted octagonal collars, the fin stack and the nose. The exposed housing is authored around the
barrel axis (Z=0); the shared roof posts hold it by its trunnion bosses.
PPCs have no mechanical recoil.
"""
import math
# HERE, the kit folder, is set by the file that loads this one (author.py or a family module).
_shape = {}
exec(compile((HERE/'hard_surface.py').read_text(encoding='utf-8'), 'hard_surface', 'exec'), _shape)

# Housing length/width/height, trunnion pivot, fin count and pitch, fin and core radii, nose and collar lengths.
TIERS = {
    'light': dict(L=6.6, w=3.6, h=3.4, cy=3.2, cz=6.8, fins=13, pitch=.42, fin=.95, core=.55, nose=2.0, collar=1.0),
    'standard': dict(L=7.8, w=4.2, h=3.9, cy=3.7, cz=6.8, fins=19, pitch=.42, fin=1.15, core=.68, nose=2.6, collar=1.2),
    'heavy': dict(L=9.0, w=4.8, h=4.2, cy=4.3, cz=6.9, fins=21, pitch=.46, fin=1.45, core=.88, nose=3.1, collar=1.4),
}


def layout(family, variant):
    t = TIERS[variant]
    return t['w'], t['L'], t['cy'], t['cz']


def lathe(ref, name, steps, lod, segments=None):
    """steps: (y, radius, material of the span to the next step); one closed turned part with material bands."""
    return ref.ring(name, [(y, r) for y, r, _ in steps], steps[0][2], segments or (12 if lod == 0 else 8), (0, 0),
                    axis='Y', bands=[m for _, _, m in steps[:-1]])


def barrel(ref, family, variant, lod):
    """Octagonal collars, radiator fin stack and the bulb nose with its stepped tip. Returns the aperture."""
    t = TIERS[variant]; R, core, c, n = t['fin'], t['core'], t['collar'], t['nose']
    _shape['harden'](ref, _shape['shell'](ref, 'Accelerator collar', [
        (0, 2.6 * R, 2.6 * R, .75 * R, 0), (.5 * c, 2.6 * R, 2.6 * R, .75 * R, 0),
        (.5 * c + .02, 2.2 * R, 2.2 * R, .62 * R, 0), (c, 2.2 * R, 2.2 * R, .62 * R, 0)], 'armor'), .05)
    if lod == 0:
        for i in range(8):
            a = (i + .5) * math.pi / 4
            _shape['stud'](ref, (1.2 * R * math.cos(a), .5 * c, 1.2 * R * math.sin(a)), (0, 1, 0), .07 * R)
    fins = t['fins'] * t['pitch']; front = c + fins
    if lod == 0:
        # Thin steel radiator fins on a dark core, with a short gap behind the nose.
        steps = [(c - .1, core, 'dark')]
        for i in range(t['fins']):
            y = c + i * t['pitch'] + .12
            steps += [(y, core, 'steel'), (y, R, 'edge'), (y + .45 * t['pitch'], R, 'steel'),
                      (y + .45 * t['pitch'], core, 'dark')]
    else:
        steps = [(c - .1, .94 * R, 'steel'), (c + .3 * fins, .94 * R, 'black'), (c + .38 * fins, .94 * R, 'steel'),
                 (c + .62 * fins, .94 * R, 'black'), (c + .7 * fins, .94 * R, 'steel')]
    # Many thin fins cost little at ten sides; the nose stays round.
    steps += [(front, core if lod == 0 else .94 * R, 'dark')]
    lathe(ref, 'Accelerator fin stack', steps, lod, 10 if lod == 0 else 8)
    if lod == 0:
        steps = [(front - .05, core, 'steel'), (front + .1, .95 * R, 'steel'), (front + .15 * n, .98 * R, 'steel'),
                 (front + .45 * n, .8 * R, 'steel'), (front + .7 * n, .52 * R, 'steel'), (front + .82 * n, .38 * R, 'edge'),
                 (front + .82 * n, .3 * R, 'edge'), (front + .92 * n, .3 * R, 'edge'), (front + .92 * n, .37 * R, 'edge'),
                 (front + n, .37 * R, 'edge'), (front + n, .2 * R, 'black'), (front + n - .35, .2 * R, 'black')]
    else:
        steps = [(front - .05, .94 * R, 'steel'), (front + .15 * n, .98 * R, 'steel'), (front + .7 * n, .52 * R, 'steel'),
                 (front + .82 * n, .36 * R, 'edge'), (front + n, .36 * R, 'edge'), (front + n, .2 * R, 'black')]
    lathe(ref, 'Accelerator nose', steps, lod, 14 if lod == 0 else 8)
    return [(0, front + n, 0)]


def mantlet(ref, family, variant, lod):
    """Front-bay installation: a bolted flange holds the collars against the bay face."""
    t = TIERS[variant]; R = t['fin']; start = len(ref.PARTS)
    _shape['harden'](ref, _shape['shell'](ref, 'Accelerator flange', [(-.0, 3.0 * R, 2.8 * R, .8 * R, 0),
                                                                     (.25, 3.0 * R, 2.8 * R, .8 * R, 0)], 'dark'), .04)
    return ref.PARTS[start:]


def slots(ref, x, y, z, length, height, sign):
    """Three diagonal vent slots on a side face facing +X or -X."""
    for k in (-1, 0, 1):
        cy = y + k * length * .3
        corners = [(-.08 * length, -.4 * height), (.08 * length, -.4 * height), (.2 * length, .4 * height),
                   (.04 * length, .4 * height)]
        points = [(x, cy + u, z + v) for u, v in corners]
        obj = ref.mesh_obj('Diagonal vent slot', points, [(0, 1, 2, 3)], 'black')
        if obj.data.polygons[0].normal.x * sign < 0:
            obj.data.polygons[0].flip()


def body(ref, family, variant, lod):
    """Capacitor housing around the barrel axis: a lower body, and a raised capacitor box above it."""
    t = TIERS[variant]
    L, w, h, cy = t['L'], t['w'], t['h'], t['cy']
    start = len(ref.PARTS); s = h / 4; H = _shape['harden']; top = h / 2
    H(ref, _shape['shell'](ref, 'Capacitor housing', [(0, w * .86, h * .84, .45 * s, 0), (.4, w - .12, h - .12, .5 * s, 0),
                                                     (L - .5, w - .12, h - .12, .5 * s, 0),
                                                     (L - .05, w * .84, h * .8, .42 * s, 0)], 'armor'), .05)
    # The raised capacitor box carries the vents and the top plate. Housings borrowed
    # by taller receivers may lower it (`box`, in quarters of the housing height) to stay within the roof sockets.
    box_h, box_end = t.get('box', 1.35) * s, .62 * L
    H(ref, _shape['shell'](ref, 'Capacitor box', [(.15, w * .9, box_h * .8, .22 * s, top + box_h * .4),
                                                  (.55, w * .96, box_h, .26 * s, top + box_h * .5 - .05),
                                                  (box_end - .4, w * .96, box_h, .26 * s, top + box_h * .5 - .05),
                                                  (box_end, w * .86, box_h * .8, .22 * s, top + box_h * .4)], 'armor'), .06)
    plate_z = top + box_h - .05
    ref.block('Capacitor top plate', (0, .5 * box_end, plate_z + .06), (w * .62, .55 * box_end, .12), 'pale',
              cut=.2, bevel=.03)
    H(ref, _shape['shell'](ref, 'Housing front deck', [(box_end - .3, w * .86, .45, .14 * s, top + .12),
                                                       (L - .45, w * .86, .45, .14 * s, top + .12),
                                                       (L - .1, w * .72, .3, .1 * s, top + .05)], 'armor'), .04)
    x = w / 2 * .96 + .02
    for sign in (-1, 1):
        # Diagonal-slot vent panels on both box sides.
        _shape['side_panel'](ref, 'Vent panel', sign * x, [(.6, top + .25 * box_h), (box_end - .6, top + .25 * box_h),
                                                          (box_end - .6, top + .8 * box_h), (.6, top + .8 * box_h)],
                             .1, 'dark')
        slots(ref, sign * (x + .051), .5 * box_end, top + .52 * box_h, box_end - 1.4, .5 * box_h, sign)
    if lod == 0:
        for dx in (-.24, .24):
            for dy in (.32, .68):
                _shape['stud'](ref, (dx * w, dy * box_end, plate_z + .12), (0, 0, 1), .06 * s)
        if variant == 'heavy':
            # The heavy housing's X-marked capacitor hatch.
            for angle in (.6, -.6):
                ref.block('Hatch cross groove', (0, .5 * box_end, plate_z + .125), (.12, .5 * box_end, .02), 'black',
                          cut=0, bevel=0, angle=angle)
        # Port panel and a junction box with its cable, ahead of the trunnion.
        ref.block('Port panel', (w * .22, .8 * L, top + .4), (w * .3, .14 * L, .14), 'dark', cut=.06, bevel=0)
        for i in range(3):
            _shape['stud'](ref, (w * (.12 + .1 * i), .8 * L, top + .47), (0, 0, 1), .09 * s, 'black')
        ref.block('Junction box', (w / 2 + .04, L - .7, -top * .4), (.2, .7, h * .3), 'dark', cut=.06, bevel=0)
        _shape['hose'](ref, 'Junction cable', [(w / 2 + .05, L - .55, -top * .62), (w * .4, L + .1, -top * .85),
                                               (w * .18, L + .35, -top * .6)], .07 * s, lod, 'black', rib=1)
    # Two thick power cables arch over the box from the capacitor deck back to the rear frame.
    for sx in (-.26, .26):
        _shape['hose'](ref, 'Power cable', [(sx * w, box_end - .45, top + box_h * .7),
                                            (sx * w, .7 * box_end, top + box_h + .15),
                                            (sx * w, .2 * box_end, top + box_h + .15),
                                            (sx * w, -.7, top + .05)], .22 * s, lod, 'black', rib=1)
    # Rounded rear frame loops; cables and lifting gear tie into them.
    for sx in (-.28, .28):
        # The loop stays above the barrel axis so it clears the roof when the barrel elevates.
        loop = ([(.3, top - .15), (-.8, top - .1), (-1.15, top - .55), (-1.15, .1), (-.8, -.25), (.3, -.2)]
                if lod == 0 else [(.3, top - .15), (-1.1, top - .35), (-1.1, -.05), (.3, -.2)])
        _shape['hose'](ref, 'Rear frame rail', [(sx * w, y, z) for y, z in loop], .16 * s, lod, 'steel', rib=1)
    return ref.PARTS[start:]
