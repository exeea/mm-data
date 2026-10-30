"""Autocannons: calibre-scaled barrels, complete receivers and cast front-bay mantlets.

Calibre tiers follow the catalogue rack size (AC/2, AC/5, AC/10, AC/20); 'compact' serves crowded heads.
The barrel starts at the rear datum Y=0 and belongs to the recoil joint. Receivers are authored around the
barrel axis (Z=0); the trunnion at cy along it carries the bosses the shared roof posts' pins enter
(pod_mounts.py).
"""
import math
# HERE, the kit folder, is set by the file that loads this one (author.py or a family module).
_shape = {}
exec(compile((HERE/'hard_surface.py').read_text(), 'hard_surface', 'exec'), _shape)

# Receiver length/width/height, trunnion pivot, barrel length ahead of the receiver, tube/jacket/brake/bore
# radii and brake length. Heavier calibres trade barrel length for bore.
CALIBRES = {
    '2': dict(L=10.0, w=3.6, h=3.3, cy=4.2, cz=6.8, barrel=22.0, r=.56, jacket=.92, brake=.84, bore=.34, brake_len=2.4),
    '5': dict(L=10.8, w=4.0, h=3.6, cy=4.5, cz=6.8, barrel=19.5, r=.72, jacket=1.12, brake=1.04, bore=.45, brake_len=2.7),
    '10': dict(L=11.5, w=4.4, h=4.0, cy=4.8, cz=6.9, barrel=16.5, r=.92, jacket=1.38, brake=1.32, bore=.6, brake_len=3.0),
    '20': dict(L=12.0, w=4.8, h=4.4, cy=4.9, cz=6.9, barrel=11.5, r=1.32, jacket=1.8, brake=1.8, bore=.92, brake_len=3.4),
    'compact': dict(L=9.5, w=3.8, h=3.4, cy=4.0, cz=6.8, barrel=10.5, r=.85, jacket=1.18, brake=1.12, bore=.55,
                    brake_len=2.4),
}


def layout(family, variant):
    c = CALIBRES[variant]
    return c['w'], c['L'], c['cy'], c['cz']


def recuperators(c):
    """Twin recoil cylinders below either side of the barrel root, clear of the barrel race."""
    radius = .26 + .12 * c['jacket']
    d = 1.28 * c['jacket'] + radius * .6
    return [(s * .72 * d, -.72 * d) for s in (-1, 1)], radius


def lathe(ref, name, steps, lod, segments=None):
    """steps: (y, radius, material of the span to the next step); one closed turned part with material bands."""
    return ref.ring(name, [(y, r) for y, r, _ in steps], steps[0][2], segments or (16 if lod == 0 else 8), (0, 0),
                    axis='Y', bands=[m for _, _, m in steps[:-1]])


def slots(ref, name, y0, y1, r0, r1, count, open_fraction):
    half = math.pi / count * (1 - open_fraction)
    for i in range(count):
        _shape['radial_bar'](ref, name, (i + .5) * math.tau / count, half, r0 * .98, r1, y0, y1, 'dark')


def barrel(ref, family, variant, lod):
    """Barrel, vented heat jacket, recoil clamp and slotted multi-baffle brake. Returns the muzzle tip.

    The compact gun fills crowded multi-weapon heads at reduced scale: it keeps the slotted brake, paints its
    jacket vents and drops the clamp.
    """
    c = CALIBRES[variant]; lean = variant == 'compact'
    segments = (10 if lod == 0 else 6) if lean else None
    j, r, rb, bore, brake, length = c['jacket'], c['r'], c['brake'], c['bore'], c['brake_len'], c['barrel']
    jacket_end = .9 + min(6.8, max(4.4, .36 * length))
    start = length - brake
    if lod:
        # At LOD1 distance the silhouette carries the gun: jacket with one vent band, taper, brake band and bore.
        lathe(ref, 'Autocannon barrel', [(0, j, 'edge'), (3.2, j, 'black'), (jacket_end - .9, j, 'edge'),
                                         (jacket_end, 1.08 * r, 'steel'), (start - .25, .96 * r, 'steel'),
                                         (start, rb, 'black'), (length - .5, rb, 'edge'), (length, .9 * rb, 'steel'),
                                         (length, bore, 'black'), (length - .6, bore, 'black')], lod, segments)
        return [(0, length, 0)]
    sections = 2 if jacket_end - .9 >= 5 else 1
    slot = (jacket_end - 3.2 - .45 * (sections - 1) - .9) / sections
    core = .78 * j
    steps = [(0, .9 * j, 'steel'), (.9, .9 * j, 'steel'), (.9, j, 'edge')]
    y = 3.2
    for k in range(sections):
        if lean:
            steps += [(y, j, 'black'), (y + slot, j, 'edge')]
        else:
            steps += [(y, j, 'edge'), (y, core, 'black'), (y + slot, core, 'edge'), (y + slot, j, 'edge')]
            slots(ref, 'Heat jacket rib', y, y + slot, core, j, 8, .42)
        y += slot + .45
    y -= .45
    steps += [(y + .5, j, 'steel'), (jacket_end, 1.08 * r, 'steel')]
    if variant not in ('20', 'compact'):
        ye = jacket_end + .4 * (start - jacket_end)
        e = max(.9, .08 * length)
        steps += [(ye, 1.04 * r, 'steel'), (ye + .3, 1.34 * r, 'edge'), (ye + .3 + e, 1.34 * r, 'steel'),
                  (ye + .6 + e, r, 'steel')]
    steps += [(start - .25, .96 * r, 'steel'), (start, .86 * rb, 'steel'), (start + .18, rb, 'edge'),
              (start + .6, rb, 'edge'), (start + .6, .72 * rb, 'black'), (length - .6, .72 * rb, 'edge'),
              (length - .6, rb, 'edge'), (length - .1, rb, 'steel'), (length, .9 * rb, 'steel'),
              (length, bore, 'black'), (length - .9, bore, 'black')]
    slots(ref, 'Muzzle brake baffle', start + .6, length - .6, .72 * rb, rb, 6, .5)
    lathe(ref, 'Autocannon barrel', steps, lod, segments)
    if lean:
        return [(0, length, 0)]
    recoil_clamp(ref, c, lod)
    return [(0, length, 0)]


def recoil_clamp(ref, c, lod):
    """The recoil clamp carries the recuperator rods; it slides toward the receiver when firing."""
    j = c['jacket']
    lathe(ref, 'Recoil clamp', [(2.6, 1.0 * j, 'steel'), (2.6, 1.14 * j, 'steel'), (3.1, 1.14 * j, 'steel'),
                                (3.1, 1.0 * j, 'steel')], lod)
    rods, radius = recuperators(c)
    for x, z in rods:
        ref.ring('Recuperator piston rod', [(0, .5 * radius), (2.85, .5 * radius)], 'steel', 8, (x, z), axis='Y')
        _shape['radial_bar'](ref, 'Recoil clamp lug', math.atan2(z, x), .6 * radius / math.hypot(x, z),
                             .95 * j, math.hypot(x, z) + .55 * radius, 2.6, 3.1, 'steel')


def mantlet(ref, family, variant, lod):
    """Front-bay installation: the barrel leaves the head through a heavy armored mantlet."""
    c = CALIBRES[variant]; j = c['jacket']; start = len(ref.PARTS); lean = variant == 'compact'
    # A bolted flange on the bay face carries a cast, turned mantlet and its steel barrel race.
    flange = _shape['shell'](ref, 'Mantlet flange', [(0, 3.4 * j, 3.0 * j, .5 * j, 0), (.35, 3.4 * j, 3.0 * j, .5 * j, 0)],
                             'armor')
    if not lean:
        _shape['harden'](ref, flange, .04 * j)
    lathe(ref, 'Cast gun mantlet', [(.3, 1.42 * j, 'armor'), (.55, 1.5 * j, 'armor'), (1.15, 1.5 * j, 'armor'),
                                    (1.45, 1.3 * j, 'dark'), (1.45, 1.15 * j, 'steel'), (1.75, 1.15 * j, 'dark'),
                                    (1.75, j, 'dark')], lod, (10 if lod == 0 else 6) if lean else None)
    if lod == 0 and not lean:
        for x, z in ((1.45, 1.2), (-1.45, 1.2), (1.45, -1.2), (-1.45, -1.2), (1.6, 0), (-1.6, 0)):
            _shape['stud'](ref, (x * j, .35, z * j), (0, 1, 0), .08 * j)
    return ref.PARTS[start:]


def body(ref, family, variant, lod):
    """Complete receiver around the barrel axis; it rotates with elevation and stays still during recoil."""
    c = CALIBRES[variant]
    L, w, h, cy, j = c['L'], c['w'], c['h'], c['cy'], c['jacket']
    start = len(ref.PARTS); s = h / 4; H = _shape['harden']; top = h / 2
    H(ref, _shape['shell'](ref, 'Receiver core', [(0, w * .86, h * .84, .5 * s, 0), (.45, w - .12, h - .12, .55 * s, 0),
                                                 (L - 1.4, w - .12, h - .12, .55 * s, 0),
                                                 (L - .3, w * .78, h * .7, .42 * s, -.08 * h)], 'dark'), .05)
    # Raised breech and feed housing over the rear, stepping down to a lower front deck.
    H(ref, _shape['shell'](ref, 'Breech housing', [(.3, w * .84, 1.0 * s, .2 * s, top + .4 * s),
                                                   (.8, w * .92, 1.5 * s, .28 * s, top + .62 * s),
                                                   (.55 * L - .6, w * .92, 1.5 * s, .28 * s, top + .62 * s),
                                                   (.55 * L, w * .8, .9 * s, .2 * s, top + .35 * s)], 'armor'), .06)
    H(ref, _shape['shell'](ref, 'Receiver front deck', [(.55 * L - .3, w * .88, .5, .14 * s, top + .14),
                                                        (L - 1.5, w * .88, .5, .14 * s, top + .14),
                                                        (L - .75, w * .66, .3, .1 * s, top + .04)], 'armor'), .04)
    H(ref, _shape['shell'](ref, 'Receiver mantlet plate', [(L - .6, w * .82, h * .76, .4 * s, -.04 * h),
                                                           (L - .1, w * .74, h * .64, .34 * s, -.06 * h)], 'armor'), .05)
    ref.block('Breech cover plate', (0, .26 * L, top + 1.38 * s), (w * .62, .36 * L, .12), 'pale', cut=.2, bevel=.03)
    if lod == 0:
        # Small fittings vanish at LOD1 distance; the housings above carry the silhouette.
        ref.block('Receiver belly plate', (0, L * .5, -top - .1), (w * .78, L * .62, .26), 'armor', cut=.2, bevel=.03)
        ref.block('Receiver top rail', (0, .76 * L, top + .5), (w * .22, .34 * L, .26), 'steel', cut=.05, bevel=.03)
        H(ref, ref.block('Fire control housing', (w * .26, .66 * L, top + .62), (w * .26, .13 * L, .55), 'armor',
                         cut=.12, bevel=0), .035)
        for dx in (-.24, .24):
            for dy in (.1, .42):
                _shape['stud'](ref, (dx * w, dy * L, top + 1.44 * s), (0, 0, 1), .07 * s)
    x = w / 2 + .02
    for sign in (-1, 1):
        # The trunnion bosses take the middle; armor, covers and vents sit around them.
        rear = [(.5, -h * .36), (cy - 1.0, -h * .36), (cy - 1.0, h * .36), (.85, h * .36), (.5, h * .2)]
        front = [(cy + 1.0, -h * .36), (L - 1.5, -h * .36), (L - .9, -h * .1), (L - 1.2, h * .36), (cy + 1.0, h * .36)]
        H(ref, _shape['side_panel'](ref, 'Receiver side armor', sign * x, rear, .16, 'armor'), .04)
        H(ref, _shape['side_panel'](ref, 'Receiver side armor', sign * x, front, .16, 'armor'), .04)
        if lod == 0:
            _shape['side_panel'](ref, 'Breech side cover', sign * (x + .1), [(.75, -h * .26), (cy - 1.5, -h * .26),
                                                                           (cy - 1.5, h * .26), (.75, h * .26)], .06,
                                 'pale')
        vent_start, vent_end = cy + 3.1, L - 1.6
        if vent_end - vent_start > .6:
            _shape['side_vent'](ref, sign * (x + .09), (vent_start + vent_end) / 2, -h * .06, vent_end - vent_start,
                                h * .34, lod)
        if lod == 0:
            for yy, zz in ((.95, h * .19), (cy - 1.75, -h * .19)):
                _shape['stud'](ref, (sign * (x + .13), yy, zz), (sign, 0, 0), .07 * s)
    # Breech: a heavy rear cover with an access block, not an open box.
    _shape['shell'](ref, 'Rear breech cover', [(-.12, w * .78, h * .74, .35 * s, 0), (.1, w * .78, h * .74, .35 * s, 0)],
                    'steel')
    if lod == 0:
        ref.block('Breech block', (0, -.32, -h * .05), (w * .42, .4, h * .42), 'dark', cut=.1, bevel=0)
    lathe(ref, 'Barrel race', [(L - .3, 1.28 * j, 'dark'), (L + .45, 1.28 * j, 'steel'), (L + .62, 1.15 * j, 'dark'),
                               (L + .62, j, 'dark')], lod)
    rods, radius = recuperators(c)
    for rx, rz in rods:
        ref.ring('Recoil recuperator', [(L - .9, radius), (L + 1.4, radius), (L + 1.55, .78 * radius)], 'steel',
                 12 if lod == 0 else 6, (rx, rz), axis='Y')
        if lod == 0:
            ref.ring('Recuperator band', [(L + .6, 1.12 * radius), (L + .78, 1.12 * radius)], 'dark', 12, (rx, rz),
                     axis='Y')
    # Hydraulic line from the breech housing over the front deck to the barrel race.
    if lod == 0:
        _shape['hose'](ref, 'Recuperator hydraulic line', [(-w * .3, .55 * L - .05, top + .55 * s),
                                                           (-w * .34, .66 * L, top + .5), (-w * .34, L - 1.4, top + .48),
                                                           (-w * .28, L - .45, top + .1)], .13 * s, lod)
    return ref.PARTS[start:]
