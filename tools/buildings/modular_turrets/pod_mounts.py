"""Shared external weapon mounts, authored in Blender: the side-arm bracket, the roof post and the roof pedestal, and
the trunnion bosses a weapon carries. A bracket's or post's pin enters a weapon's boss; BuildingTurretVisual places the
mounts from their pin, hinge and seat points."""
import math
_shape = {}
exec(compile((HERE/'hard_surface.py').read_text(encoding='utf-8'),
             'hard_surface', 'exec'), _shape)
ARM_REACH = 1.3
# How far out from the head flank a bracket's pin reaches: the weapon's inner side.
ARM_PIN = ARM_REACH + .9


_racks = {}
exec(compile((HERE/'racks.py').read_text(encoding='utf-8'),
             'racks', 'exec'), _racks)
dimensions = _racks['dimensions']


def axle(ref, name, profile, cy, cz, material, lod):
    # Rotate a Z-axis cylinder onto X without touching the shared ring helper.
    obj = ref.ring(name, profile, material, 12 if lod == 0 else 6, (cy, cz), axis='Z')
    for v in obj.data.vertices:
        v.co = (v.co.z, v.co.x, v.co.y)
    obj.data.update()
    return obj


# Shared roof mounts, from the roof socket up: a post's trunnion bearing, and a pedestal's hinge pin.
POST_HEIGHT = 7.5
PEDESTAL_HINGE = 4.2
# The pedestal's hinge pin: a weapon rests on its top.
PIN_RADIUS = .38
# A post's trunnion pin reaches this far inboard of its middle, to a weapon's side, clear of its side controls.
POST_PIN = -.74


def post(ref, lod):
    """A roof post: a foot seated in the roof and an upright arm whose bearing, at POST_HEIGHT on X, carries a trunnion
    pin into a weapon's right boss, the cap and the elevation gear on its outer (+X) face. It is symmetric front to back,
    so a half turn about Z makes it the left post. Posts stand in pairs, a fork holding both sides, or alone beside it."""
    h = POST_HEIGHT
    # The lower portion seats inside the receiving roof.
    ref.block('Post foot', (0, 0, 1.4), (1.8, 3.4, 2.8), 'armor', cut=.45 if lod == 0 else 0, bevel=0)
    contour = [(-1.0, 2.65), (1.0, 2.65), (1.0, h - .9), (.65, h + .65), (-.65, h + .65), (-1.0, h - .9)]
    ref.loft('Post arm', [[(dx, y, z) for y, z in contour] for dx in (-.26, .26)], 'armor')
    axle(ref, 'Trunnion bearing', [(-.36, 1.05), (.36, 1.05)], 0, h, 'dark', lod)
    axle(ref, 'Trunnion retaining cap', [(.11, .67), (.41, .67)], 0, h, 'steel', lod)
    axle(ref, 'Trunnion pin', [(POST_PIN, .45), (-.36, .45)], 0, h, 'steel', lod)
    if lod == 0:
        ref.flat_patch('Post service recess', (.265, 0, 4.9), (.72, 1.0), 'X', 'dark')
        # Toothed elevation ring seated .01 into the outer face, driven by a pinion box below it.
        teeth = [(r * math.cos(i * math.pi / 22), h + r * math.sin(i * math.pi / 22))
                 for i in range(44) for r in ((1.62,) if i % 2 == 0 else (1.38,))]
        _shape['side_panel'](ref, 'Elevation gear ring', .29, teeth, .08, 'steel')
        ref.block('Elevation pinion housing', (.38, -.2, h - 2.1), (.34, 1.1, .9), 'dark', cut=.12, bevel=0)


def pedestal(ref, lod):
    """A roof pedestal: a column on a foot under the weapon, and a clevis on top whose hinge pin, on X at
    PEDESTAL_HINGE, carries the weapon resting on it; the weapon pitches about the pin. Symmetric."""
    p = PEDESTAL_HINGE
    ref.block('Pedestal foot', (0, 0, 1.0), (3.4, 3.4, 2.0), 'armor', cut=.45 if lod == 0 else 0, bevel=0)
    _shape['harden'](ref, ref.loft('Pedestal column', [[(a, b, z) for a, b in _shape['section'](w, w, .3)]
                                                      for z, w in ((1.9, 2.2), (p - .55, 1.7))], 'armor'), .05)
    ref.block('Pedestal saddle', (0, 0, p - .45), (2.1, 1.9, .3), 'dark', cut=.1, bevel=0)
    for sign in (-1, 1):
        ref.block('Clevis cheek', (sign * .8, 0, p), (.3, 1.5, 1.6), 'armor', cut=.12, bevel=0)
    axle(ref, 'Hinge pin', [(-1.05, PIN_RADIUS), (1.05, PIN_RADIUS)], 0, p, 'steel', lod)
    if lod == 0:
        for x in (-1.25, 1.25):
            for y in (-1.25, 1.25):
                _shape['stud'](ref, (x, y, 2.0), (0, 0, 1), .09)


def x_prism(ref, name, x0, x1, w, h, cut, mat):
    """A chamfered block extruded along X, so its chamfers face the flank it grows from."""
    return ref.loft(name, [[(x, y, z) for y, z in _shape['section'](w, h, cut)] for x in (x0, x1)], mat)


def bracket(ref, sign, lod):
    """A head's side-arm bracket: an armored arm leaves the head flank (origin) along sign * X and ends in a capped
    trunnion bearing, whose pin reaches ARM_PIN into the weapon's inner boss. It is symmetric top to bottom, so the left
    bracket is the right one rolled half a turn about the firing axis. The weapon hangs outboard and pitches on it."""
    s, a = sign, ARM_REACH
    _shape['harden'](ref, x_prism(ref, 'Arm root flange', -s * .85, s * .3, 3.6, 3.4, .5, 'armor'), .05)
    _shape['harden'](ref, ref.loft('Launcher arm', [[(x, y, z) for y, z in _shape['section'](w, h, c)]
                                                    for x, w, h, c in ((-s * .9, 2.9, 3.0, .6),
                                                                       (s * (a - .25), 2.3, 2.5, .5))], 'armor'), .05)
    # Twin elevation drives and hydraulic lines, above and below the arm.
    for up in (1, -1):
        ref.block('Arm elevation drive', (s * a * .45, .2, up * 1.5), (a * .75, 1.5, .5), 'dark', cut=.12, bevel=0)
    axle(ref, 'Arm trunnion bearing', [(s * (a - .4), 1.3), (s * (a + .25), 1.3)], 0, 0, 'dark', lod)
    axle(ref, 'Arm trunnion cap', [(s * (a + .23), .85), (s * (a + .38), .7)], 0, 0, 'steel', lod)
    axle(ref, 'Arm trunnion pin', sorted([(s * (a + .25), .45), (s * ARM_PIN, .45)]), 0, 0, 'steel', lod)
    if lod == 0:
        for y in (-1.25, 1.25):
            for z in (-1.15, 1.15):
                _shape['stud'](ref, (s * .3, y, z), (s, 0, 0), .09)
        for i in range(6):
            angle = i * math.pi / 3 + .52
            _shape['stud'](ref, (s * (a + .25), 1.08 * math.cos(angle), 1.08 * math.sin(angle)), (s, 0, 0), .08)
        for up in (1, -1):
            _shape['hose'](ref, 'Arm hydraulic line', [(s * .35, -.7, up * 1.55), (s * .7, -.85, up * 1.9),
                                                       (s * (a * .75), -.5, up * 1.75)], .1, lod, 'black')


def rack_trunnion(ref, kind, count, lod):
    """A launcher rack's trunnion: a boss on each side of its middle, where a bracket's or post's pin enters. Returns how
    far out the bosses reach, the module's trunnion point."""
    width, length = dimensions(kind, count)
    for sign in (-1, 1):
        axle(ref, 'Trunnion boss', [(sign * width / 2 - .05, .62), (sign * width / 2 + .05, .62)], length * .5, 0, 'dark', lod)
    return width / 2 + .05


def gun_trunnion(ref, half, cy, lod):
    """A gun's trunnion: a boss on each side of its receiver (or housing) half-width {half} at {cy} along it, where a
    post's pin enters. Returns how far out the bosses reach, the module's trunnion point."""
    for sign in (-1, 1):
        axle(ref, 'Trunnion boss', sorted([(sign * (half - .02), .73), (sign * (half + .1), .73)]), cy, 0, 'dark', lod)
    return half + .1
