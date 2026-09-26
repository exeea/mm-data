"""Shared low-poly figure and transport artwork; formation assembly belongs to the runtime."""
from math import cos, pi, sin

from unit_model_geometry import Geometry, MODEL_UNITS_PER_METRE, add, cross, mul, normal, sub


# person() draws a standing figure 21 units tall and canon makes a soldier 1.8 m. Transports share the factor so they
# stay in scale with their troops; the runtime assembles them at twice their exported size.
TROOP_SCALE = 1.8 * MODEL_UNITS_PER_METRE / 21
# Battle armour is the same figure, evenly larger than a soldier: 2.7 m, within the canonical 2.5 to 3 m.
BATTLE_ARMOR_SIZE = 1.5


def person(pose, armored=False, jump=False, modular=False):
    g = Geometry(modular=modular)
    kneel = pose == 'kneeling'
    advance = pose == 'advancing'
    torso_z = 10 if kneel else 14
    spread = 3.2 if armored else 2.1
    group = lambda role: role if modular else 'soldier'
    if modular:
        g.joint('hips', (0, 0, torso_z-3))
        g.joint('torso', (0, 0, torso_z-3), 'hips')
        g.joint('head', (0, -.8, torso_z+3), 'torso')
    for sign in (-1, 1):
        hip = (sign*spread/2, 0, torso_z-3)
        knee = (sign*spread, 3 if kneel and sign == -1 else -1 if kneel else sign*2 if advance else 0, 4 if kneel else 6)
        foot = (sign*spread, -3 if kneel and sign == 1 else 4 if advance and sign == 1 else 0, 1)
        width = 3.1 if armored else 1.9
        leg = 'leftLeg' if sign == -1 else 'rightLeg'
        if modular:
            g.joint(leg, hip, 'hips')
            g.joint(leg+'Shin', knee, leg)
            g.joint(leg+'Foot', foot, leg+'Shin')
        g.beam(hip, knee, width, width, group(leg), 'paint')
        g.beam(knee, foot, width, width, group(leg+'Shin'), 'edge')
        g.box((foot[0], foot[1]+1, 1), (width, 3.5, 2), group(leg+'Foot'), 'metal')
    g.box((0, 0, torso_z), (7 if armored else 5, 5 if armored else 3.3, 7 if armored else 6),
          group('torso'), 'paint', .3 if armored else 0, .82)
    g.box((0, -.8, torso_z+5), (4.5 if armored else 3.3, 4 if armored else 3.3, 4),
          group('head'), 'paint', .4 if armored else 0, .8)
    g.face([(-1.5, 1.3, torso_z+5.6), (1.5, 1.3, torso_z+5.6),
            (1.5, 1.3, torso_z+4.4), (-1.5, 1.3, torso_z+4.4)],
           group('head'), 'glass' if armored else 'dark')
    for sign in (-1, 1):
        shoulder = (sign*(4 if armored else 3), 0, torso_z+2)
        elbow = (sign*(4.5 if armored else 3.5), 2, torso_z-1)
        hand = (1.5, 3, torso_z-2) if pose == 'standing' else (sign*3, 4, torso_z-2) if advance else (1.5, 5, torso_z+1)
        arm = 'leftArm' if sign == -1 else 'rightArm'
        if modular:
            g.joint(arm, shoulder, 'torso')
            g.joint(arm+'Forearm', elbow, arm)
        g.beam(shoulder, elbow, 3.5 if armored else 2, group=group(arm), material='paint')
        g.beam(elbow, hand, 3 if armored else 1.7, group=group(arm+'Forearm'), material='edge')
    g.box((1.5, 3, torso_z-2) if pose == 'standing' else (1.5, 5, torso_z+.8),
          (2, 3, 8) if pose == 'standing' else (2, 8, 2), group('rightArmForearm'), 'metal')
    if modular and not armored:
        g.emitter((1.5, 3, torso_z-6) if pose == 'standing' else (1.5, 9, torso_z+.8),
                  (0, 0, -1) if pose == 'standing' else (0, 1, 0), 'rightArmForearm', 'muzzle', 'bullet')
    if armored:
        # A compact jump pack / arm cannon follows the generic BA sprite's bulky shoulders.
        g.box((0, -3, torso_z+2), (7, 3, 7), group('torso'), 'edge')
        g.beam((4, 2, torso_z), (4, 8, torso_z), 2.4, 2.4, group('rightArmForearm'), 'metal')
        if modular:
            g.emitter((4, 8, torso_z), (0, 1, 0), 'rightArmForearm', 'muzzle', 'bullet')
            for side in (-1, 1):
                g.emitter((side*2, -3.3, torso_z-1.5), (0, 0, -1), 'torso', 'exhaust', 'exhaust')
    if jump:
        # Preserve the established tapered jump pack and downward exhaust.
        lo = [(-2.3, -1.4, torso_z-4), (0, -4.3, torso_z-4), (2.3, -1.4, torso_z-4)]
        hi = [(x*.8, y, torso_z+2.5) for x, y, _ in lo]
        g.face(list(reversed(lo)), group('torso'), 'dark')
        g.face(hi, group('torso'), 'edge')
        for i in range(3):
            j = (i+1) % 3
            g.face([lo[i], lo[j], hi[j], hi[i]], group('torso'), 'edge')
        if modular:
            g.emitter((0, -2.4, torso_z-4), (0, 0, -1), 'torso', 'exhaust', 'exhaust')
    return g


def infantry_vehicle(kind, modular=False):
    """Small sprite-proportioned transports; +Y is forward, as for the troops."""
    g = Geometry(modular=modular)
    if modular:
        g.joint('vehicle', (0, 0, 0))
        g.joint('boarding', (8, -5, 0) if kind == 'motorized' else (0, -15, 0), 'vehicle')
        g.joint('cabin', (0, -3, 4), 'vehicle')
    if kind == 'motorized':
        g.box((0, 0, 4), (11, 21, 3), 'vehicle', 'paint')
        g.box((0, 6.7, 6.5), (10, 8, 3), 'vehicle', 'paint', taper=.85)
        g.box((0, -5, 6), (8, 3, 4), 'vehicle', 'dark')
        for sign in (-1, 1):
            for y in (-7, 7):
                wheel = f'wheel-{sign}-{y}' if modular else 'vehicle'
                if modular:
                    g.joint(wheel, (sign*6, y, 3.5), 'vehicle')
                g.beam((sign*6-1.3, y, 3.5), (sign*6+1.3, y, 3.5),
                       7.2, group=wheel, material='dark', sides=6)
            g.beam((sign*4.5, -6, 5), (sign*4.5, -6, 12), 1.2, group='vehicle')
        g.beam((-4.5, -6, 12), (4.5, -6, 12), 1.2, group='vehicle')
        windshield = [(-4, 0, 12), (4, 0, 12), (4, 2.5, 8), (-4, 2.5, 8)]
        g.face(windshield, 'vehicle', 'glass')
        g.face(list(reversed(windshield)), 'vehicle', 'glass')
        g.box((0, 11, 4), (12, 1.5, 2), 'vehicle', 'metal')
        for x in (-3.5, 3.5):
            g.face([(x-.8, 10.72, 6.5), (x+.8, 10.72, 6.5),
                    (x+.8, 10.72, 5.5), (x-.8, 10.72, 5.5)], 'vehicle', 'glass')
        return g

    # Shared enclosed APC hull, visibly different from the open motorized jeep.
    g.box((0, 0, 8.5), (13, 25, 9), 'vehicle', 'paint', bevel=.35, taper=.78)
    g.box((0, -1, 13.4), (5, 6, .8), 'vehicle', 'edge')
    for sign in (-1, 1):
        g.face([(sign*.4, 10.08, 12), (sign*3, 10.08, 12),
                (sign*3, 10.68, 10), (sign*.4, 10.68, 10)][::sign], 'vehicle', 'glass')
        x = sign*4
        g.face([(x-.65, 11.96, 6), (x+.65, 11.96, 6),
                (x+.65, 12.2, 5.2), (x-.65, 12.2, 5.2)], 'vehicle', 'glass')
    g.face([(-3, -12.23, 5), (3, -12.23, 5), (3, -10.4, 11), (-3, -10.4, 11)],
           'vehicle', 'metal')
    if kind == 'wheeled':
        for sign in (-1, 1):
            for y in (-8, 0, 8):
                wheel = f'wheel-{sign}-{y}' if modular else 'vehicle'
                if modular:
                    g.joint(wheel, (sign*6.5, y, 3.5), 'vehicle')
                g.beam((sign*6.5-1.3, y, 3.5), (sign*6.5+1.3, y, 3.5),
                       7.2, group=wheel, material='dark', sides=6)
    elif kind == 'tracked':
        profile = [(-10, 0), (10, 0), (13, 3), (10, 6), (-10, 6), (-13, 3)]
        for sign in (-1, 1):
            g.loft([[(x, y, z) for y, z in profile]
                    for x in (sign*7.2-1.7, sign*7.2+1.7)], 'vehicle', 'dark')
            x = sign*8.92
            g.face([(x, -9, 1.5), (x, 9, 1.5), (x, 10.5, 3),
                    (x, 9, 4.5), (x, -9, 4.5), (x, -10.5, 3)][::sign], 'vehicle', 'metal')
    elif kind == 'hover':
        g.box((0, 0, 2), (20, 29, 4), 'vehicle', 'dark', bevel=.5, taper=.9)
        for x in (-4, 4):
            g.beam((x, -11, 6.5), (x, -14, 6.5), 4.5, group='vehicle', material='metal', sides=6)
            g.face([(x-1, -14.02, 5.5), (x+1, -14.02, 5.5),
                    (x+1, -14.02, 7.5), (x-1, -14.02, 7.5)], 'vehicle', 'dark')
    else:
        raise ValueError('Unknown infantry transport '+kind)
    return g


def _ring(z, width, depth, x=0, y=0, cut=.32):
    """An octagonal section at height z, for rounded armour shells."""
    a, b = width/2, depth/2
    c = min(a, b)*cut
    return [(x+u, y+v, z) for u, v in ((-a+c, -b), (a-c, -b), (a, -b+c), (a, b-c),
                                       (a-c, b), (-a+c, b), (-a, b-c), (-a, -b+c))]


def _hexagon(z, width, depth, x=0, y=0):
    """A six-sided section at height z, pointed at the sides: cheaper than _ring for small rounded parts."""
    return [(x+cos(pi*k/3)*width/2, y+sin(pi*k/3)*depth/2, z) for k in range(6)]


def _shell(g, rings, group, material, bottom=False, top=False, top_material=None, buried=()):
    """A loft whose end caps are optional: caps buried inside another part only cost triangles.

    `buried` names side faces sealed inside another part of the same rigid node as (band, side) pairs, which are
    left out too.
    """
    if bottom:
        g.face(list(reversed(rings[0])), group, material)
    if top:
        g.face(rings[-1], group, top_material or material)
    for band, (lo, hi) in enumerate(zip(rings, rings[1:])):
        for i in range(len(lo)):
            if (band, i) in buried:
                continue
            j = (i+1) % len(lo)
            g.face([lo[i], lo[j], hi[j], hi[i]], group, material)


def _tube(g, start, end, width, depth, sides, group, material, start_cap=False, end_cap=True, taper=1,
          end_material=None):
    """Geometry.beam with optional caps, so a limb joining another part does not pay for a hidden end."""
    axis = normal(sub(end, start))
    u = normal(cross(axis, (0, 0, 1) if abs(axis[2]) < .9 else (0, 1, 0)))
    v = cross(axis, u)
    rings = [[add(point, add(mul(u, cos(2*pi*i/sides+pi/4)*width*.5*scale),
                             mul(v, sin(2*pi*i/sides+pi/4)*depth*.5*scale))) for i in range(sides)]
             for point, scale in ((start, 1), (end, taper))]
    _shell(g, rings, group, material, start_cap, end_cap, end_material)


def _outward(g, points, inside, group, material):
    """A face wound to point away from a point inside its part, whatever order its points came in."""
    normal_vector = cross(sub(points[1], points[0]), sub(points[2], points[0]))
    middle = [sum(point[k] for point in points)/len(points) for k in range(3)]
    away = sum(normal_vector[k]*(middle[k]-inside[k]) for k in range(3)) > 0
    g.face(points if away else list(reversed(points)), group, material)


def _facing_forward(g, points, group, material):
    """A flat detail on a front face, wound so it faces forward whatever order its points came in."""
    g.face(points if cross(sub(points[1], points[0]), sub(points[2], points[0]))[1] > 0 else list(reversed(points)),
           group, material)


def _elemental_joints(g, arm_x=5.8):
    """The Elemental's rig: the fallback trooper's joints at Elemental proportions, shared by both detail levels
    so the far suit animates exactly like the near one. `arm_x` is the shoulder's distance from the centre."""
    g.joint('hips', (0, 0, 16))
    g.joint('torso', (0, 0, 16), 'hips')
    g.joint('head', (0, -.5, 25), 'torso')
    for sign in (-1, 1):
        leg = 'leftLeg' if sign == -1 else 'rightLeg'
        g.joint(leg, (sign*3, 0, 16), 'hips')
        g.joint(leg+'Shin', (sign*3.4, 1, 8.5), leg)
        g.joint(leg+'Foot', (sign*3.4, 0, 1.2), leg+'Shin')
        arm = 'leftArm' if sign == -1 else 'rightArm'
        g.joint(arm, (sign*arm_x, 0, 24), 'torso')
        g.joint(arm+'Forearm', (sign*(arm_x+.4), 1.2, 18.8), arm)


def elemental(modular=True, launchers=True):
    """Elemental battle armour on the trooper rig, drawn in person()'s units (29.6 tall against the armoured
    figure's 31.5) and exported at TROOP_SCALE, which keeps that proportion: about 2.5 m.

    Follows the line art: a tortoise-shell chest under a wide, low oval helmet with a V-shaped viewport, a square
    missile launcher with a side ear on each shoulder, a laser barrel along the right forearm and a three-prong claw
    on the left. Battle armour weapons are not drawn by the game, so the laser is part of the suit. MegaMek budgets
    battle armour at 330 triangles per suit, whatever the squad size. Faces sealed inside another part of the same
    rigid node are left out. `elemental_far` is the simpler suit shown when the squad is small on screen.

    `launchers` off gives the suit for Elementals that carry no missiles (the Headhunter and Space versions): no
    shoulder launchers, and the shoulder domes closed on top instead.
    """
    g = Geometry(modular=modular)
    group = lambda role: role if modular else 'soldier'
    if modular:
        _elemental_joints(g)
    for sign in (-1, 1):
        leg = 'leftLeg' if sign == -1 else 'rightLeg'
        hip, knee, ankle = (sign*3, 0, 16), (sign*3.4, 1, 8.5), (sign*3.4, -.2, 2.2)
        # Massive thighs widening toward the knee (a four-sided _tube's faces sit at cos 45 degrees of its size).
        _tube(g, hip, knee, 6.6, 7, 4, group(leg), 'paint', end_cap=False, taper=1.05)
        # Heavy shins tapering to the ankle, with a shield-shaped pad over the front of the knee.
        _tube(g, knee, ankle, 6.4, 7, 4, group(leg+'Shin'), 'edge', end_cap=False, taper=.8)
        pad = [(sign*3.4-2.7, 3.3, 11.4), (sign*3.4+2.7, 3.3, 11.4), (sign*3.4, 3.3, 5.6)]
        point = (sign*3.4, 4.5, 9.8)
        for i in range(3):
            _outward(g, [pad[i], pad[(i+1) % 3], point], (sign*3.4, 3.3, 9.5), group(leg+'Shin'), 'paint')
        # Big wedge feet; the sole always sits on the ground, so it has no face.
        sole = [(sign*3.4-2.8, -2.6, 0), (sign*3.4+2.8, -2.6, 0), (sign*3.4+3.1, 4.4, 0), (sign*3.4-3.1, 4.4, 0)]
        instep = [(sign*3.4+(x-sign*3.4)*.72, .9+(y-.9)*.72, 2.8) for x, y, _ in sole]
        _shell(g, [sole, instep], group(leg+'Foot'), 'metal', top=True)
    # A tortoise-shell chest: near-straight sides below the shoulders, domed forward at mid-chest, rounded
    # corners, narrowing to a V-shaped groin plate between the thighs. The wide helmet covers its top, so it
    # has no lid, and the upper back is sealed inside the back pack.
    _shell(g, [_ring(12.6, 3.8, 3.6, y=.4, cut=.4), _ring(20.2, 11.4, 8, y=.6, cut=.4), _ring(24.6, 10.6, 7, y=.2, cut=.4)],
           group('torso'), 'paint', buried={(1, 0)})
    # A wide, low oval helmet spanning the chest from shoulder to shoulder, rounding over below the launchers.
    base, crown = (24.4, 11.2, 7, .4), (26.9, 8.4, 6.2, .4)
    _shell(g, [_ring(base[0], base[1], base[2], y=base[3]), _ring(crown[0], crown[1], crown[2], y=crown[3]),
               _ring(27.9, 5, 4, y=.3)], group('head'), 'paint', top=True)
    visor_half_width = 3.1
    # A wide V-shaped viewport across the helmet's face, laid on the face's flat front plane.
    front = lambda z: base[3]+base[2]/2 + (crown[3]+crown[2]/2 - base[3]-base[2]/2)*(z-base[0])/(crown[0]-base[0]) + .08
    top_edge = [(-visor_half_width, 26.85), (0, 26.1), (visor_half_width, 26.85)]
    bottom_edge = [(x, z-.7) for x, z in top_edge]
    for i in (0, 1):
        quad = [top_edge[i], top_edge[i+1], bottom_edge[i+1], bottom_edge[i]]
        _facing_forward(g, [(x, front(z), z) for x, z in quad], group('head'), 'glass')
    # Back pack. Its front face is buried in the chest and its underside is never seen from above.
    pack = [(-4.2, -6.2, 19), (4.2, -6.2, 19), (4.2, -2.8, 19), (-4.2, -2.8, 19)]
    lid = [(x, y, 26) for x, y, _ in pack]
    g.face(lid, group('torso'), 'edge')
    for i in (0, 1, 3):
        g.face([pack[i], pack[(i+1) % 4], lid[(i+1) % 4], lid[i]], group('torso'), 'edge')
    if launchers:
        # A square missile launcher on each shoulder: the face narrows toward the front for a chamfered look,
        # with one round missile port in its centre. Held by the torso so it stays level while the arms swing.
        for sign in (-1, 1):
            centre = (sign*6.2, 0, 28)
            _tube(g, (centre[0], -2, centre[2]), (centre[0], 2.1, centre[2]), 4.2, 4.4, 4, group('torso'), 'paint',
                  start_cap=True, taper=.84)
            # A four-sided _tube's faces sit at cos(45 degrees) of its nominal half size.
            half_width, half_height, chamfer = 4.2*.84/2*cos(pi/4), 4.4*.84/2*cos(pi/4), .55
            _facing_forward(g, [(centre[0]+cos(pi*k/4+pi/8)*.72, 2.14, centre[2]+sin(pi*k/4+pi/8)*.72)
                                for k in range(8)], group('torso'), 'dark')
            # The ear: a "7"-shaped plate on the outer side, straight out near the top, then slanting back down to
            # the launcher's foot, with its hole in the wide upper part. Its inner side is buried in the launcher body,
            # so it has no face.
            inner = centre[0]+sign*(half_width-.2)
            ear = [(inner, centre[2]+.7), (centre[0]+sign*(half_width+1.3), centre[2]+.75),
                   (centre[0]+sign*(half_width+.4), centre[2]-1.2), (inner, centre[2]-1.2)]
            ear_middle = (sum(x for x, _ in ear)/4, 0, sum(z for _, z in ear)/4)
            back, face = [(x, -1.4, z) for x, z in ear], [(x, 1.9, z) for x, z in ear]
            _outward(g, face, ear_middle, group('torso'), 'paint')
            _outward(g, back, ear_middle, group('torso'), 'paint')
            for i in (0, 1, 2):
                _outward(g, [back[i], back[i+1], face[i+1], face[i]], ear_middle, group('torso'), 'paint')
            hole, size = (centre[0]+sign*(half_width+.75), centre[2]+.3), .22
            _facing_forward(g, [(hole[0]-size, 1.94, hole[1]+size), (hole[0]+size, 1.94, hole[1]+size),
                                (hole[0]+size, 1.94, hole[1]-size), (hole[0]-size, 1.94, hole[1]-size)], group('torso'), 'dark')
            # Darker facets across the face's corners make the octagonal frame around the port.
            for across in (-1, 1):
                for up in (-1, 1):
                    corner = (centre[0]+across*half_width, centre[2]+up*half_height)
                    _facing_forward(g, [(corner[0], 2.12, corner[1]),
                                        (corner[0]-across*chamfer, 2.12, corner[1]),
                                        (corner[0], 2.12, corner[1]-up*chamfer)], group('torso'), 'edge')
    for sign in (-1, 1):
        arm = 'leftArm' if sign == -1 else 'rightArm'
        elbow = (sign*6.2, 1.2, 18.8)
        # A domed shoulder held by the torso, closing under the launcher that covers its open top (capped when
        # there is no launcher); the arm hangs from inside it.
        _shell(g, [_hexagon(23.4, 4.6, 4.6, sign*6.1), _hexagon(25.2, 6, 5.6, sign*6.1),
                   _hexagon(26.6, 2.8, 2.6, sign*6.2)], group('torso'), 'paint', top=not launchers)
        _tube(g, (sign*6, 0, 24.5), elbow, 5.4, 5.6, 4, group(arm), 'paint', end_cap=False, taper=.72)
    # Right forearm levelled forward with the laser along it.
    _tube(g, (6.2, 1.2, 18.8), (6.2, 6.6, 19.4), 3.6, 3.8, 4, group('rightArmForearm'), 'edge')
    _tube(g, (6.2, 6.4, 19.6), (6.2, 12.6, 19.6), 1.8, 1.8, 5, group('rightArmForearm'), 'metal', taper=.8,
          end_material='dark')
    # Left forearm hanging forward, ending in a three-prong claw.
    _tube(g, (-6.2, 1.2, 18.8), (-6.4, 4.2, 13.8), 3.6, 3.8, 4, group('leftArmForearm'), 'edge')
    for tip in ((-5.1, 6.1, 10.8), (-7.5, 6.1, 10.8), (-6.4, 2.6, 10.6)):
        _tube(g, (-6.4, 4.2, 13.4), tip, 1.3, 1.3, 3, group('leftArmForearm'), 'metal', end_cap=False, taper=.35)
    if modular:
        g.emitter((6.2, 12.7, 19.6), (0, 1, 0), 'rightArmForearm', 'muzzle', 'laser')
        for side in (-1, 1):
            g.emitter((side*2.2, -4.6, 18.9), (0, 0, -1), 'torso', 'exhaust', 'exhaust')
    return g


def elemental_far(modular=True, launchers=True):
    """The Elemental for a squad small on screen: the same rig and silhouette in about 60% of the triangles.

    It keeps what reads at a distance (the oval helmet and its V viewport, the tortoise-shell chest, the square
    launchers and their ports, the laser arm, the claw and the heavy legs) and drops the shoulder domes, the
    launcher ears, the knee pads and the chamfer facets. Six-sided sections replace eight-sided ones. `launchers`
    matches the near suit's.
    """
    g = Geometry(modular=modular)
    group = lambda role: role if modular else 'soldier'
    if modular:
        _elemental_joints(g)
    for sign in (-1, 1):
        leg = 'leftLeg' if sign == -1 else 'rightLeg'
        hip, knee, ankle = (sign*3, 0, 16), (sign*3.4, 1, 8.5), (sign*3.4, -.2, 2.2)
        _tube(g, hip, knee, 6.6, 7, 4, group(leg), 'paint', end_cap=False, taper=1.05)
        _tube(g, knee, ankle, 6.4, 7, 4, group(leg+'Shin'), 'edge', end_cap=False, taper=.8)
        sole = [(sign*3.4-2.8, -2.6, 0), (sign*3.4+2.8, -2.6, 0), (sign*3.4+3.1, 4.4, 0), (sign*3.4-3.1, 4.4, 0)]
        instep = [(sign*3.4+(x-sign*3.4)*.72, .9+(y-.9)*.72, 2.8) for x, y, _ in sole]
        _shell(g, [sole, instep], group(leg+'Foot'), 'metal', top=True)
    # Chest and helmet as six-sided sections; the chest's upper back is sealed inside the pack.
    _shell(g, [_hexagon(12.6, 3.8, 3.6, y=.4), _hexagon(20.2, 11.4, 8, y=.6), _hexagon(24.6, 10.6, 7, y=.2)],
           group('torso'), 'paint', buried={(1, 4)})
    # The helmet's base reaches back over the chest's open top, which the near suit's shoulder domes cover.
    base, crown = (24.4, 11.2, 7.2, .2), (27.9, 5.4, 4.2, .3)
    _shell(g, [_hexagon(base[0], base[1], base[2], y=base[3]), _hexagon(crown[0], crown[1], crown[2], y=crown[3])],
           group('head'), 'paint', top=True)
    front = lambda z: base[3]+base[2]/2 + (crown[3]+crown[2]/2 - base[3]-base[2]/2)*(z-base[0])/(crown[0]-base[0]) + .08
    top_edge = [(-2, 26.5), (0, 25.9), (2, 26.5)]
    bottom_edge = [(x, z-.7) for x, z in top_edge]
    for i in (0, 1):
        quad = [top_edge[i], top_edge[i+1], bottom_edge[i+1], bottom_edge[i]]
        _facing_forward(g, [(x, front(z), z) for x, z in quad], group('head'), 'glass')
    pack = [(-4.2, -6.2, 19), (4.2, -6.2, 19), (4.2, -2.8, 19), (-4.2, -2.8, 19)]
    lid = [(x, y, 26) for x, y, _ in pack]
    g.face(lid, group('torso'), 'edge')
    for i in (0, 1, 3):
        g.face([pack[i], pack[(i+1) % 4], lid[(i+1) % 4], lid[i]], group('torso'), 'edge')
    for sign in (-1, 1):
        if launchers:
            centre = (sign*6.2, 0, 28)
            _tube(g, (centre[0], -2, centre[2]), (centre[0], 2.1, centre[2]), 4.2, 4.4, 4, group('torso'), 'paint',
                  start_cap=True, taper=.84)
            port = .75
            _facing_forward(g, [(centre[0]-port, 2.14, centre[2]+port), (centre[0]+port, 2.14, centre[2]+port),
                                (centre[0]+port, 2.14, centre[2]-port), (centre[0]-port, 2.14, centre[2]-port)],
                            group('torso'), 'dark')
        arm = 'leftArm' if sign == -1 else 'rightArm'
        # Without the shoulder domes the upper arm rises to the launcher, capped where its top shows.
        _tube(g, (sign*6, 0, 26.3), (sign*6.2, 1.2, 18.8), 5.4, 5.6, 4, group(arm), 'paint', start_cap=True,
              end_cap=False, taper=.72)
    _tube(g, (6.2, 1.2, 18.8), (6.2, 6.6, 19.4), 3.6, 3.8, 4, group('rightArmForearm'), 'edge')
    _tube(g, (6.2, 6.4, 19.6), (6.2, 12.6, 19.6), 1.8, 1.8, 4, group('rightArmForearm'), 'metal', taper=.8,
          end_material='dark')
    _tube(g, (-6.2, 1.2, 18.8), (-6.4, 4.2, 13.8), 3.6, 3.8, 4, group('leftArmForearm'), 'edge')
    for tip in ((-5.2, 6.1, 10.8), (-7.4, 6.1, 10.8)):
        _tube(g, (-6.4, 4.2, 13.4), tip, 1.3, 1.3, 3, group('leftArmForearm'), 'metal', end_cap=False, taper=.35)
    if modular:
        g.emitter((6.2, 12.7, 19.6), (0, 1, 0), 'rightArmForearm', 'muzzle', 'laser')
        for side in (-1, 1):
            g.emitter((side*2.2, -4.6, 18.9), (0, 0, -1), 'torso', 'exhaust', 'exhaust')
    return g


ELEMENTAL_II_ARM_X = 7


def _elemental_ii_front(z, low, high):
    """The y of a shell band's flat front at height z, between its lower and upper (z, depth, y) sections."""
    (z0, d0, y0), (z1, d1, y1) = low, high
    return y0+d0/2 + (y1+d1/2 - y0-d0/2)*(z-z0)/(z1-z0)


def elemental_ii(modular=True, far=False):
    """Elemental II battle armour, from the line art: one hunched shell over chest and head with a raised chest plate
    and vents, a visor strip near its top, a segmented belly, big domed pauldrons and no launchers, an AP Gauss barrel
    slung under the right forearm, an anti-personnel pod on the left, fists, hip fins, and flared boots with knee
    plates and ankle discs. Drawn in person()'s units on the Elemental rig with the arms set wider.

    `far` gives the simpler suit MegaMek shows while the squad is small on screen: six-sided sections, one pauldron
    band, four-sided limbs, and no vents, knee plates or ankle discs.
    """
    g = Geometry(modular=modular)
    group = lambda role: role if modular else 'soldier'
    if modular:
        _elemental_joints(g, ELEMENTAL_II_ARM_X)
    section = _hexagon if far else (lambda z, w, d, x=0, y=0: _ring(z, w, d, x=x, y=y, cut=.38))
    for sign in (-1, 1):
        leg = 'leftLeg' if sign == -1 else 'rightLeg'
        x = sign*3.4
        hip, knee, ankle = (sign*3, 0, 16), (x, 1, 8.5), (x, -.2, 2.2)
        _tube(g, hip, knee, 6.8, 7.2, 4, group(leg), 'paint', end_cap=False, taper=1.05)
        # Boots from the knee down, flaring toward the ankle.
        _tube(g, knee, ankle, 6.8, 7.6, 4 if far else 6, group(leg+'Shin'), 'edge', end_cap=False, taper=1.12)
        if not far:
            pad = [(x-2.4, 3.6, 11.2), (x+2.4, 3.6, 11.2), (x, 3.6, 6.8)]
            for i in range(3):
                _outward(g, [pad[i], pad[(i+1) % 3], (x, 4.9, 9.6)], (x, 3.6, 9.6), group(leg+'Shin'), 'paint')
            disc = [(x+sign*3.95, -.2+cos(pi*k/3)*1.1, 3.4+sin(pi*k/3)*1.1) for k in range(6)]
            _outward(g, disc, (x, -.2, 3.4), group(leg+'Shin'), 'metal')
        sole = [(x-3, -2.8, 0), (x+3, -2.8, 0), (x+3.3, 4.8, 0), (x-3.3, 4.8, 0)]
        instep = [(x+(px-x)*.75, 1+(py-1)*.75, 2.8) for px, py, _ in sole]
        _shell(g, [sole, instep], group(leg+'Foot'), 'metal', top=True)
        # A pointed fin over each hip, seen from both sides.
        fin = [(sign*4.2, 2.6, 17.8), (sign*6.8, 1, 17.4), (sign*7.9, .2, 12.2)]
        g.face(fin, group('hips'), 'paint')
        g.face(list(reversed(fin)), group('hips'), 'paint')
    # The segmented belly, darker and narrower than the shell above it.
    _shell(g, [section(12.6, 4, 3.8, y=.4), section(15.6, 6.8, 5.6, y=.6), section(18.8, 8.4, 6.6, y=.6)],
           group('torso'), 'edge')
    # One hunched shell over chest and head, widest across the upper chest and rounding over at the top.
    low, high = (22.5, 9.4, .6), (26, 8.8, .2)
    shell = [(18.2, 9.8, 7.2, .5), (22.5, 13.4, 9.4, .6), (26, 12.2, 8.8, .2), (28.2, 6.8, 5, -.4)]
    if far:
        shell = [shell[0], shell[1], (28.2, 7.6, 5.6, -.2)]
        low, high = (22.5, 9.4, .6), (28.2, 5.6, -.2)
    _shell(g, [section(z, w, d, y=y) for z, w, d, y in shell], group('torso'), 'paint', top=True)
    # The raised chest plate, an inverted trapezoid on the upper chest's flat front, with angled vents either side.
    plate_front = lambda z, lift: _elemental_ii_front(z, low, high) + lift
    plate = [(-4, 25.6), (4, 25.6), (2.4, 22.9), (-2.4, 22.9)] if not far else [(-3.2, 25.2), (3.2, 25.2), (2, 23.2), (-2, 23.2)]
    _facing_forward(g, [(px, plate_front(pz, .1), pz) for px, pz in plate], group('torso'), 'edge')
    if not far:
        for side in (-1, 1):
            for drop in (0, 1.1):
                vent = [(side*3.5, 25-drop), (side*2.9, 25-drop), (side*1.2, 23.6-drop), (side*1.8, 23.6-drop)]
                _facing_forward(g, [(px, plate_front(pz, .14), pz) for px, pz in vent], group('torso'), 'dark')
    # The visor strip near the top of the shell.
    visor_low, visor_high = ((26, 8.8, .2), (28.2, 5, -.4)) if not far else ((22.5, 9.4, .6), (28.2, 5.6, -.2))
    visor = [(-1.4, 27.2), (1.4, 27.2), (1.4, 26.4), (-1.4, 26.4)]
    _facing_forward(g, [(px, _elemental_ii_front(pz, visor_low, visor_high)+.08, pz) for px, pz in visor],
                    group('torso'), 'glass')
    for sign in (-1, 1):
        arm = 'leftArm' if sign == -1 else 'rightArm'
        shoulder_x = sign*ELEMENTAL_II_ARM_X
        # Big domed pauldrons, held by the torso so they stay put while the arms swing beneath.
        dome = [_hexagon(22.2, 5, 5, shoulder_x), _hexagon(24.6, 6.6, 6, shoulder_x), _hexagon(26.4, 3.6, 3.2, shoulder_x)]
        _shell(g, [dome[0], dome[2]] if far else dome, group('torso'), 'paint', top=True)
        _tube(g, (shoulder_x, 0, 24), (shoulder_x, 1.2, 18.8), 5.4, 5.6, 4, group(arm), 'paint', end_cap=False, taper=.75)
    # Right arm: a thick round forearm with the AP Gauss barrel slung under it, ending in a fist.
    right = ELEMENTAL_II_ARM_X
    _tube(g, (right, 1.2, 18.8), (right, 6.8, 19.4), 4.4, 4.4, 4 if far else 6, group('rightArmForearm'), 'edge', taper=.95)
    _tube(g, (right, 6.6, 19.4), (right, 8.8, 19.4), 3.2, 3.4, 4, group('rightArmForearm'), 'metal')
    _tube(g, (right, 1.8, 16.6), (right, 10.4, 16.6), 3, 3, 4 if far else 6, group('rightArmForearm'), 'metal',
          start_cap=True, end_material='dark')
    # Left arm: forearm and fist, with the anti-personnel pod along the forearm's outer side.
    left = -ELEMENTAL_II_ARM_X
    _tube(g, (left, 1.2, 18.8), (left-.2, 4.2, 13.8), 3.8, 4, 4, group('leftArmForearm'), 'edge')
    _tube(g, (left-.2, 4.4, 13.4), (left-.3, 5.6, 11.4), 3, 3.2, 4, group('leftArmForearm'), 'metal')
    _tube(g, (left-1.9, 1.8, 18), (left-2.1, 4.4, 13.6), 1.8, 2.8, 4, group('leftArmForearm'), 'edge', start_cap=True)
    if modular:
        g.emitter((right, 10.5, 16.6), (0, 1, 0), 'rightArmForearm', 'muzzle', 'bullet')
        for side in (-1, 1):
            g.emitter((side*2.2, -4.2, 19), (0, 0, -1), 'torso', 'exhaust', 'exhaust')
    return g


def elemental_ii_far(modular=True):
    """The Elemental II for a squad small on screen; see `elemental_ii`."""
    return elemental_ii(modular, far=True)
