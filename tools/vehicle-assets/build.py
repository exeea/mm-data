"""Builds the photographic vehicles (photo_shell.py) from their reference sheets in this folder.

    python build.py picture [name ...]   each vehicle's material picture: tools/materials/structures/vehicles/<name>/sources/artwork.png
    python build.py model [name ...]     each vehicle's GLB, from its exported material (tools/materials/export.py)

A vehicle's numbers are read off its sheet: sheet pixels for what a face shows, model units for where it stands.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent)]
from photo_shell import BOARD, TOOLS, Sheet, Shell, carried
from car_body import Car
from glb_geometry import write_glb

HEAVY_WHEEL, CAR_WHEEL = 'structures/vehicles/heavy-wheel', 'structures/vehicles/car-wheel'
CAR_PRESETS = [["Silver", "#b8b8b8"], ["Gray", "#707070"], ["White", "#d1d1d1"], ["Blue", "#142ba6"], ["Steel", "#546985"], ["Azure", "#245c99"],
               ["Orange", "#996121"], ["Olive", "#7a701a"], ["Yellow", "#b8b014"], ["Teal", "#248f8a"], ["Pink", "#7a3d5c"], ["Purple", "#8f2482"],
               ["Green", "#14ab1a"], ["Red", "#a6140a"], ["Maroon", "#54120f"], ["Mustard", "#806b1a"], ["Turquoise", "#267380"],
               ["Magenta", "#8f2159"], ["Ochre", "#73612e"]]
CAR_PAINT = (0xa6/255, 0x14/255, 0x0a/255)  # Red, the Paint slot's own colour.
RUSTED = 'structures/common/rusted-steel'


# -- Straddle carrier -------------------------------------------------------------------------------

STRADDLE = Sheet('straddle-carrier', {
    'side': {'box': (145, 0, 865, 526), 'rect': (0, 0, .70, .63)},
    'front': {'box': (1050, 12, 1354, 518), 'rect': (.70, 0, 1, .63)},
    'top': {'box': (150, 640, 845, 946), 'rect': (0, .63, .70, 1)},
    'rear': {'box': (1070, 528, 1344, 1008), 'rect': (.70, .63, 1, 1)}})


def straddle_carrier(lod):
    """Four legs on wheel bogies under a portal of side and cross beams; on top a walkway, an engine house and the cab
    on its front corner; between the legs the spreader on its ropes. The sheet mirrors its front view."""
    scale = .03734  # Units a side-view pixel.

    def at(px, py):
        return (px-511)*scale, (520-py)*scale

    def y(px):
        return (px-511)*scale

    def z(py):
        return (520-py)*scale

    shell = Shell(STRADDLE)
    half = 4.07  # The side frames' centre lines.
    sides = (10, 8, 6)[lod]
    for sx in (1, -1):
        x = sx*half
        left = sx > 0  # The sheet's side view is this side's; the cab stands on it.
        for front in (True, False):
            shift = 0 if front else 490
            outline = [(168+shift, 430), (195+shift, 412), (338+shift, 412), (366+shift, 430), (366+shift, 472), (168+shift, 472)]
            nose = (1140, 422, 1078, 470) if left else (1350, 422, 1298, 470)
            tail = (1285, 905, 1345, 960) if left else (1080, 905, 1140, 960)
            shell.prism(outline, x-1.12, x+1.12, at, {5: ('front', nose), 0: ('front', nose), 2: ('rear', tail), 3: ('rear', tail)})
            for px in (224, 316):
                shell.wheel(x, y(px+shift), 1.42, 2.3, sx, HEAVY_WHEEL, sides, back=lod < 2, lowest=lod == 2)
            px0, px1 = (232, 292) if front else (735, 785)
            shell.box(x-.95, x+.95, y(px0), y(px1), z(412), z(157), side=(px0, 157, px1, 412),
                      front=(1135, 150, 1085, 405) if left else (1340, 150, 1297, 405),
                      rear=(1288, 655, 1335, 905) if left else (1086, 655, 1133, 905))
            if lod == 0:  # The gusset under the beam.
                corner = [(292, 157), (322, 157), (292, 207)] if front else [(705, 157), (735, 157), (735, 207)]
                shell.prism(corner, x-.22, x+.22, at)
        shell.box(x-1.0, x+1.0, y(245), y(832), z(157), z(127), side=(245, 127, 832, 157),
                  top=(215, 852, 830, 903) if left else (215, 678, 830, 725),
                  front=(1140, 128, 1082, 152) if left else (1340, 128, 1292, 152),
                  rear=(1288, 628, 1340, 652) if left else (1082, 628, 1133, 652))
        if lod < 2:  # The walkway's railings.
            shell.card(x+sx*.98, y(262), y(835), z(127), z(66), (262, 66, 835, 127))
    # Cross beams, the engine house, the cab.
    shell.box(-half+1.0, half-1.0, y(248), y(278), z(157), z(127), front=(1297, 128, 1135, 152), rear=(1133, 628, 1288, 652), top=(212, 725, 242, 852))
    shell.box(-half+1.0, half-1.0, y(745), y(775), z(157), z(127), front=(1297, 128, 1135, 152), rear=(1133, 628, 1288, 652))
    shell.box(-2.6, 2.6, y(650), y(785), z(127), z(42), side=(650, 42, 785, 127), front=(1285, 48, 1165, 125), rear=(1158, 568, 1285, 640),
              top=(715, 735, 792, 868))
    shell.box(2.3, 5.8, y(160), y(272), z(136), z(33), side=(160, 33, 272, 136), front=(1157, 40, 1062, 135), rear=(1262, 560, 1340, 640),
              top=(168, 822, 272, 905))
    shell.tube(RUSTED, (1.7, y(802), z(122)), (1.7, y(802), z(14)), .34, (6, 6, 4)[lod])  # The stack: the machine's top.
    # The spreader: its beam along the container, a head across each end, on its ropes.
    shell.box(-.55, .55, y(340), y(690), z(312), z(285), side=(340, 285, 690, 312), top=(375, 772, 670, 800))
    for px0, px1, cap in ((322, 342, (330, 738, 350, 848)), (688, 710, (700, 738, 715, 848))):
        shell.box(-2.9, 2.9, y(px0), y(px1), z(328), z(286), side=(px0, 286, px1, 328), front=(1262, 286, 1172, 322), rear=(1160, 778, 1262, 815), top=cap)
    if lod < 2:
        shell.card(0, y(320), y(712), z(330), z(157), (320, 157, 712, 330))
    return shell


# -- Reach stacker ----------------------------------------------------------------------------------

REACH = Sheet('reach-stacker', {
    'side': {'box': (36, 18, 932, 528), 'rect': (0, 0, .71, .56)},
    'front': {'box': (1076, 18, 1450, 528), 'rect': (.71, 0, 1, .56)},
    'top': {'box': (48, 614, 932, 975), 'rect': (0, .56, .71, 1)},
    'rear': {'box': (1092, 554, 1430, 996), 'rect': (.71, .56, 1, 1)}})


def reach_stacker(lod):
    """A low chassis on dual front wheels and a rear steering axle, a cab over its middle, an engine cover and a striped
    counterweight behind; the two-stage boom hinged over the counterweight on two rams, its head carrying the spreader
    that holds a container across the vehicle. It stands on the board with its spreader to +y, 1.8 off its origin."""
    scale = .0367

    def at(px, py):
        return (px-145)*scale-10.2, (520-py)*scale

    def y(px):
        return at(px, 0)[0]

    def z(py):
        return (520-py)*scale

    shell = Shell(REACH)
    sides = (10, 8, 6)[lod]
    for sx in (1, -1):
        for x in (2.58, 4.37):
            shell.wheel(sx*x, y(320), 2.22, 1.72, sx, HEAVY_WHEEL, sides, back=lod < 2)
        shell.wheel(sx*4.3, y(808), 2.13, 1.7, sx, HEAVY_WHEEL, sides, back=lod < 2)
    # The chassis: a nose between the front wheels, the body, the engine cover, the counterweight.
    shell.box(-1.7, 1.7, y(253), y(401), z(487), z(390), side=(253, 390, 401, 487), front=(1227, 377, 1307, 477), top=(253, 751, 401, 845))
    shell.box(-4.3, 4.3, y(399), y(747), z(487), z(390), side=(399, 390, 747, 487), front=(1127, 383, 1407, 480), top=(399, 679, 747, 914))
    shell.box(-3.4, 3.4, y(747), y(840), z(487), z(410), side=(747, 410, 840, 487))
    shell.box(-4.4, 4.4, y(704), y(840), z(410), z(319), side=(704, 319, 840, 410), front=(1213, 357, 1317, 383), top=(704, 676, 840, 916))
    shell.box(-4.42, 4.42, y(840), y(924), z(487), z(341), side=(840, 341, 924, 487), rear=(1140, 810, 1390, 957), top=(840, 679, 926, 902))
    shell.box(-2.4, 2.4, y(401), y(550), z(390), z(256), side=(401, 256, 550, 390), front=(1197, 257, 1330, 383), rear=(1197, 257, 1330, 383),
              top=(426, 714, 554, 874))
    # The boom: its yellow outer stage from the hinge, the dark stage that slides out of it, the head.
    shell.prism([(343, 77), (873, 261), (868, 310), (845, 350), (800, 325), (327, 133)], -1.2, 1.2, at, {0: ('top', (337, 765, 723, 828))})
    shell.prism([(201, 35), (343, 77), (328, 118), (201, 72)], -.95, .95, at, {0: ('top', (177, 768, 337, 825))})
    shell.prism([(136, 30), (170, 26), (201, 36), (201, 73), (176, 124), (124, 124), (124, 61)], -1.2, 1.2, at,
                {5: ('front', (1227, 61, 1297, 153)), 6: ('front', (1227, 27, 1297, 61)), 0: ('top', (100, 750, 177, 845))})
    shell.box(-1.3, 1.3, y(110), y(199), z(153), z(124), side=(110, 124, 199, 153), front=(1215, 110, 1310, 153), rear=(1215, 110, 1310, 153))
    for sx in (1, -1):
        ram = (1213, 197, 1227, 257)
        shell.prism([(573, 181), (600, 176), (726, 392), (699, 404)], sx*1.75-.4, sx*1.75+.4, at, {1: ('front', ram), 3: ('front', ram)})
    # The spreader: a beam across the vehicle, a head along each end.
    shell.box(-6.6, 6.6, y(107), y(183), z(193), z(153), side=(107, 150, 183, 193), front=(1083, 153, 1443, 203), rear=(1100, 650, 1423, 690),
              top=(100, 639, 177, 948))
    for sx in (1, -1):
        x = sx*6.2
        shell.box(x-.45, x+.45, y(43), y(247), z(193), z(160), side=(43, 150, 247, 193), front=(1083, 160, 1110, 203), rear=(1100, 655, 1127, 690),
                  top=(54, 934, 231, 951) if sx > 0 else (54, 639, 231, 659))
        if lod == 0:
            for px in (43, 228):
                shell.box(x-.35, x+.35, y(px), y(px+19), z(219), z(193), side=(43, 193, 62, 219), front=(1083, 193, 1100, 213), rear=(1083, 193, 1100, 213))
            # The platform's handrail.
            for z0 in (z(350), z(313)):
                shell.tube('structures/common/safety-yellow', (sx*4.25, y(345), z0), (sx*4.25, y(575), z0), .09, 4)
            for px in (345, 400, 478, 575):
                shell.tube('structures/common/safety-yellow', (sx*4.25, y(px), z(390)), (sx*4.25, y(px), z(313)), .09, 4)
    if lod < 2:
        shell.tube(RUSTED, (-2.75, y(868), z(341)), (-2.75, y(868), z(283)), .32, 6)
    return shell.half_turn(dx=1.8)


# -- Yard truck -------------------------------------------------------------------------------------

TRUCK = Sheet('yard-truck', {
    'side': {'box': (96, 120, 746, 410), 'rect': (0, 0, .75, .5)},
    'front': {'box': (1087, 123, 1317, 408), 'rect': (.75, 0, 1, .5)},
    'top': {'box': (97, 652, 745, 890), 'rect': (0, .5, .75, 1)},
    'rear': {'box': (1099, 627, 1313, 908), 'rect': (.75, .5, 1, 1)}})


def yard_truck(lod):
    """A three-axle cab-over freight truck with an empty container frame, which the yard container stands on. It
    stands on the board with its cab to +y."""
    scale = .033

    def at(px, py):
        return (px-533)*scale+1.5, (402-py)*scale

    def y(px):
        return at(px, 0)[0]

    def z(py):
        return (402-py)*scale

    shell = Shell(TRUCK)
    sides = (10, 8, 6)[lod]
    for sx in (1, -1):
        shell.wheel(sx*2.5, y(240), 1.485, 1.0, sx, HEAVY_WHEEL, sides, back=lod < 2, lowest=lod == 2)
        for px in (565, 672):
            shell.wheel(sx*2.3, y(px), 1.485, 1.45, sx, HEAVY_WHEEL, sides, back=lod < 2, lowest=lod == 2)
    shell.prism([(114, 297), (123, 229), (148, 147), (176, 129), (298, 129), (298, 297)], -2.95, 2.95, at,
                {0: ('front', (1117, 229, 1286, 297)), 1: ('front', (1117, 147, 1286, 229)), 2: ('top', (110, 679, 150, 860)),
                 3: ('top', (150, 679, 295, 860)), 4: ('rear', (1126, 640, 1286, 761))})
    shell.box(-2.95, 2.95, y(104), y(300), z(352), z(297), side=(104, 297, 300, 352), front=(1117, 297, 1286, 354))
    shell.box(-2.35, 2.35, y(318), y(739), z(300), z(283), side=(318, 283, 739, 300), top=(329, 701, 739, 844), rear=(1120, 783, 1292, 800))
    shell.box(-2.5, 2.5, y(310), y(505), z(366), z(300), side=(310, 300, 505, 366))
    shell.box(-2.3, 2.3, y(700), y(739), z(366), z(300), side=(700, 300, 739, 366), rear=(1107, 800, 1305, 869))
    if lod < 2:
        shell.box(-2.4, 2.4, y(298), y(318), z(292), z(150), side=(298, 150, 318, 292), rear=(1126, 655, 1286, 761))
    # The mirrors: the cab's widest point at every level.
    shell.box(2.82, 3.52, y(108), y(122), z(225), z(160), front=(1288, 165, 1311, 225), rear=(1288, 165, 1311, 225))
    shell.box(-3.52, -2.82, y(108), y(122), z(225), z(160), front=(1093, 165, 1115, 225), rear=(1093, 165, 1115, 225))
    return shell.half_turn()


# -- Bulldozer --------------------------------------------------------------------------------------

DOZER = Sheet('bulldozer', {
    'side': {'box': (70, 28, 902, 452), 'rect': (0, 0, .68, .5)},
    'front': {'box': (1012, 60, 1466, 452), 'rect': (.68, 0, 1, .5)},
    'top': {'box': (70, 548, 902, 952), 'rect': (0, .5, .68, 1)},
    'rear': {'box': (1062, 545, 1398, 950), 'rect': (.68, .5, 1, 1)}})
DARK_STEEL = 'structures/common/painted-steel'


def bulldozer(lod):
    """A crawler dozer, its blade to -y: tracks, an engine hood with its stack, a glazed cab under its roll bar, the
    blade on its push arms and rams, a three-tine ripper."""
    scale = .02546

    def at(px, py):
        return (px-486.5)*scale, (445-py)*scale

    def y(px):
        return at(px, 0)[0]

    def z(py):
        return (445-py)*scale

    shell = Shell(DOZER)
    for sx in (1, -1):
        x0, x1 = sorted((sx*2.2, sx*4.0))
        shell.prism([(285, 400), (300, 345), (330, 318), (700, 300), (740, 330), (745, 385), (715, 440), (310, 440)], x0, x1, at,
                    {1: ('top', (277, 595, 745, 665)), 2: ('top', (277, 595, 745, 665)), 3: ('top', (277, 595, 745, 665)),
                     4: ('rear', (1070, 760, 1135, 930)), 0: ('rear', (1070, 760, 1135, 930))})
        x0, x1 = sorted((sx*4.05, sx*4.55))
        shell.prism([(165, 395), (420, 355), (420, 385), (165, 430)], x0, x1, at, {0: ('top', (165, 880, 420, 905))})
        if lod == 0:
            shell.tube('structures/common/chrome', (sx*2.75, y(250), z(350)), (sx*2.75, y(335), z(300)), .2, 5)
    shell.flat(DARK_STEEL, [(-2.2, y(250), z(302)), (2.2, y(250), z(302)), (2.2, y(735), z(302)), (-2.2, y(735), z(302))], (.12, .12, .12))
    shell.box(-1.78, 1.78, y(248), y(500), z(300), z(200), side=(248, 200, 500, 300), top=(248, 680, 500, 820), front=(1178, 195, 1300, 300))
    shell.box(-2.6, 2.6, y(500), y(735), z(300), z(215), side=(500, 215, 735, 300), top=(668, 650, 735, 855), rear=(1105, 690, 1360, 760),
              front=(1150, 195, 1335, 290))
    shell.box(-2.1, 2.1, y(500), y(700), z(215), z(62), side=(500, 62, 700, 215), front=(1160, 62, 1320, 195), rear=(1150, 555, 1310, 690),
              top=(500, 665, 700, 840))
    shell.tube(RUSTED, (0, y(366), z(200)), (0, y(366), z(78)), .32, 6)
    # The blade: hollow to the front, its back to the machine.
    shell.prism([(78, 440), (100, 290), (125, 268), (165, 300), (165, 420), (120, 445)], -4.96, 4.96, at,
                {0: ('front', (1022, 330, 1460, 440)), 1: ('front', (1022, 300, 1460, 330)), 2: ('top', (78, 555, 165, 945)),
                 3: ('front', (1022, 300, 1460, 440))})
    # The ripper: a cross beam and its three tines.
    shell.box(-2.4, 2.4, y(750), y(800), z(335), z(285), side=(750, 285, 800, 335), rear=(1135, 770, 1325, 830), top=(752, 655, 790, 850))
    for x in ((-1.9, 0, 1.9) if lod < 2 else (0,)):
        shell.card(x, y(750), y(895), z(440), z(268), (750, 268, 895, 440))
    return shell


# -- Crawler crane ----------------------------------------------------------------------------------

CRANE = Sheet('crawler-crane', {
    'side': {'box': (45, 40, 1105, 465), 'rect': (0, 0, .78, .52)},
    'front': {'box': (1192, 63, 1479, 465), 'rect': (.78, 0, 1, .52)},
    'top': {'box': (45, 622, 1105, 932), 'rect': (0, .52, .78, 1)},
    'rear': {'box': (1186, 541, 1476, 949), 'rect': (.78, .52, 1, 1)}})


def crawler_crane(lod):
    """A crawler crane, its boom raised to -y: tracks, a house with its cab and counterweight, an A-frame, a lattice
    boom on its pendants, a hook block. The sheet draws the boom lowered; the model raises it."""
    import math
    scale = .0385

    def at(px, py):
        return (px-852)*scale, (455-py)*scale

    def y(px):
        return at(px, 0)[0]

    def z(py):
        return (455-py)*scale

    shell = Shell(CRANE)
    for sx in (1, -1):
        x0, x1 = sorted((sx*3.35, sx*5.8))
        shell.prism([(608, 400), (625, 362), (1085, 358), (1099, 400), (1085, 452), (625, 452)], x0, x1, at,
                    {1: ('top', (605, 628, 1099, 690)), 0: ('front', (1198, 360, 1260, 461)), 2: ('rear', (1192, 840, 1255, 943)),
                     3: ('rear', (1192, 840, 1255, 943))})
    shell.box(-3.5, 3.5, y(690), y(1040), z(345), z(240), side=(690, 240, 1040, 345), top=(690, 688, 1040, 870), front=(1252, 246, 1418, 351),
              rear=(1248, 725, 1414, 830))
    shell.box(-3.7, 3.7, y(1040), y(1099), z(345), z(250), side=(1040, 250, 1099, 345), rear=(1240, 725, 1422, 830), top=(1040, 688, 1099, 870))
    for x in ((-2.2, 2.2) if lod < 2 else (0,)):
        shell.card(x, y(860), y(1000), z(240), z(50), (860, 50, 1000, 240))
    # The boom, raised about its foot: its two sides are the side view's lattice, its top the top view's.
    cut = CRANE.key+'#cut'
    foot, lift, length, deep, half = (y(700), z(305)), math.radians(55), (700-75)*scale, 30*scale, .9
    along = (-math.cos(lift), math.sin(lift))
    across = (math.sin(lift), math.cos(lift))
    tip = (foot[0]+along[0]*length, foot[1]+along[1]*length)

    def boom(x, t, side):
        """A point of the boom: `t` along it from its foot, `side` across it (1 its upper chords)."""
        return (x, foot[0]+along[0]*length*t+across[0]*deep*side, foot[1]+along[1]*length*t+across[1]*deep*side)

    for x in ((-half, half) if lod < 2 else (0,)):
        shell.face(cut, [boom(x, 0, -1), boom(x, 1, -1), boom(x, 1, 1), boom(x, 0, 1)],
                   [CRANE.uv('side', 700, 337), CRANE.uv('side', 75, 337), CRANE.uv('side', 75, 273), CRANE.uv('side', 700, 273)], both=True)
    if lod == 0:
        shell.face(cut, [boom(-half, 0, 1), boom(-half, 1, 1), boom(half, 1, 1), boom(half, 0, 1)],
                   [CRANE.uv('top', 700, 740), CRANE.uv('top', 75, 740), CRANE.uv('top', 75, 802), CRANE.uv('top', 700, 802)], both=True)
    if lod < 2:
        for x in (-.5, .5):
            shell.tube(DARK_STEEL, (x, y(950), z(70)), (x, tip[0], tip[1]), .07, 3, (.2, .2, .2))
        shell.tube(DARK_STEEL, (0, tip[0]-.3, tip[1]), (0, tip[0]-.3, 7.2), .07, 3, (.2, .2, .2))
    shell.card(0, tip[0]-1.55, tip[0]+.95, 3.7, 7.2, (50, 340, 115, 430))
    return shell


# -- Car park shelter -------------------------------------------------------------------------------

SHELTER = Sheet('parking-shelter', {
    'side': {'box': (98, 98, 506, 428), 'rect': (0, 0, .34, .5)},
    'front': {'box': (682, 124, 1484, 408), 'rect': (.34, 0, 1, .5)},
    'top': {'box': (146, 475, 483, 984), 'rect': (0, .5, .34, 1)},
    'rear': {'box': (674, 619, 1484, 885), 'rect': (.34, .5, 1, 1)}})


def shelter(floor):
    """A car port for four cars, open to -y: five steel posts along its back, cantilever arms, a low-pitched corrugated
    roof; with `floor`, its concrete slab and painted bay lines."""
    def build(lod):
        shell = Shell(SHELTER)
        front, back = 8.2, 6.8  # The roof's height at its open edge and over its posts.
        corners = [(-13, -6, front), (13, -6, front), (13, 6, back), (-13, 6, back)]
        pixels = [SHELTER.uv('top', 152, 481), SHELTER.uv('top', 152, 978), SHELTER.uv('top', 465, 978), SHELTER.uv('top', 465, 481)]
        shell.face(SHELTER.key, corners, pixels)
        under = [(x, y_, z_-.18) for x, y_, z_ in corners]
        shell.face(SHELTER.key, under[::-1], pixels[::-1], (.5, .5, .5))
        shell.panel('front', [(-13, -6, front-.5), (13, -6, front-.5), (13, -6, front), (-13, -6, front)], (690, 130, 1478, 150), (0, 0, 0))
        shell.panel('rear', [(-13, 6.1, back-.6), (13, 6.1, back-.6), (13, 6.1, back), (-13, 6.1, back)], (688, 628, 1478, 652), (0, 0, 0))
        for px in ((710, 900, 1085, 1272, 1455) if lod == 0 else (710, 1085, 1455)):  # Each post with its arm and brace, in profile.
            shell.card((px-1084)/788*26, -6, 6.15, 0, front, (105, 105, 500, 423))
        shell.panel('front', [(-13, 5.5, 0), (13, 5.5, 0), (13, 5.5, back), (-13, 5.5, back)], (690, 150, 1478, 402), (0, 20, 0), cut=True, both=True)
        if floor:
            concrete = 'structures/common/cast-concrete'
            shell.flat(concrete, [(-13, -6, .3), (13, -6, .3), (13, 6, .3), (-13, 6, .3)], (.62, .62, .6))
            for a_, b_ in (((-13, -6), (13, -6)), ((13, -6), (13, 6)), ((13, 6), (-13, 6)), ((-13, 6), (-13, -6))):
                shell.flat(concrete, [(*a_, 0), (*b_, 0), (*b_, .3), (*a_, .3)], (.5, .5, .48))
            if lod == 0:
                for k in range(1, 4):
                    x = -13+26*k/4
                    shell.flat(DARK_STEEL, [(x-.12, -5.6, .32), (x+.12, -5.6, .32), (x+.12, 5.0, .32), (x-.12, 5.0, .32)], (.92, .92, .88))
        return shell
    return build


# -- Parking barrier --------------------------------------------------------------------------------

BARRIER = Sheet('parking-barrier', {
    'side': {'box': (50, 222, 1122, 413), 'rect': (0, 0, 1, .4)},
    'top': {'box': (56, 727, 1115, 836), 'rect': (0, .4, 1, .65)},
    'front': {'box': (1273, 222, 1401, 412), 'rect': (0, .65, .3, 1)},
    'rear': {'box': (1273, 686, 1401, 877), 'rect': (.3, .65, .6, 1)}})


def parking_barrier(lod):
    """Three striped concrete barrier blocks in a row along a hex's east side."""
    shell = Shell(BARRIER)
    x, foot, top, high = 24.0, 1.4, .45, 2.1
    blocks = (((-12.5, -4.3), (62, 408)), ((-4.1, 4.1), (414, 757)), ((4.3, 12.5), (765, 1108))) if lod == 0 else (((-12.5, 12.5), (62, 1108)),)
    for (y0, y1), (px0, px1) in blocks:
        middle = (x, (y0+y1)/2, 1)
        for sx in (-1, 1):
            shell.panel('side', [(x+sx*foot, y0, 0), (x+sx*foot, y1, 0), (x+sx*top, y1, high), (x+sx*top, y0, high)], (px0, 222, px1, 413), middle)
        shell.panel('top', [(x-top, y0, high), (x+top, y0, high), (x+top, y1, high), (x-top, y1, high)], (px0, 757, px1, 800), middle)
        for y, view in ((y0, 'front'), (y1, 'rear')):
            box = BARRIER.views[view]['box']
            shell.panel(view, [(x-foot, y, 0), (x+foot, y, 0), (x+top, y, high), (x-top, y, high)], box, middle)
    return shell


# -- Cars -------------------------------------------------------------------------------------------

def car(name, length, **options):
    """A road car's builder, its bonnet to -y: a body lofted through the outlines its sheet gives (car_body.py), every
    face showing the view it faces most; its pale paint takes the Paint slot."""
    body = Car(name, HERE/name/'sheet.png', length, **options)

    def build(lod):
        shell = Shell(body.sheet, paint=CAR_PAINT)
        stations = body.stations
        for (y0, a), (y1, b) in zip(stations, stations[1:]):
            away = (0, (y0+y1)/2, 1.2)
            for band in range(5):
                for sx in (1, -1):
                    shell.project(None, [(sx*a[band][0], y0, a[band][1]), (sx*a[band+1][0], y0, a[band+1][1]),
                                         (sx*b[band+1][0], y1, b[band+1][1]), (sx*b[band][0], y1, b[band][1])], away)
        for (y_end, outline), view in ((stations[0], 'front'), (stations[-1], 'rear')):
            ring = [(x, y_end, z_) for x, z_ in outline]+[(-x, y_end, z_) for x, z_ in outline[-2::-1]]
            shell.project(view, ring, (0, 0, 1.2))
        for sx in (1, -1):
            for y, radius in body.wheels:
                shell.wheel(sx*(body.half-.3), y, radius, .6, sx, CAR_WHEEL, (10, 6)[lod], back=lod == 0)
        return shell
    return body.sheet, build


CARS = {'car': 9.3, 'car-hatchback': 8.4, 'car-wagon': 9.5, 'car-minivan': 9.6}  # Each car's length.
PAINT_SLOT = {'name': 'Paint', 'colour': '#a6140a', 'presets': CAR_PRESETS}

# name: (sheet, builder, folder, levels, near triangle limit, its picture's options, its own colour slot)
VEHICLES = {'straddle-carrier': (STRADDLE, straddle_carrier, 'scenery/seaport/yard', 3, 900, {}, None),
            'reach-stacker': (REACH, reach_stacker, 'scenery/seaport/yard', 3, 900, {}, None),
            'yard-truck': (TRUCK, yard_truck, 'scenery/seaport/yard', 3, 600, {}, None),
            'bulldozer': (DOZER, bulldozer, 'scenery/construction', 3, 500, {}, None),
            'crawler-crane': (CRANE, crawler_crane, 'scenery/construction', 3, 500, {}, None),
            'parking-barrier': (BARRIER, parking_barrier, 'scenery/vehicles', 2, 80, {}, None),
            'parking-shelter': (SHELTER, shelter(True), 'scenery/vehicles', 2, 200, {}, None),
            'parking-shelter-no-floor': (SHELTER, shelter(False), 'scenery/vehicles', 2, 200, {}, None),
            **{name: (*car(name, length), 'scenery/vehicles', 2, 500, {'paint': .9}, PAINT_SLOT)
               for name, length in CARS.items() if (HERE/name/'sheet.png').is_file()}}


def model(name):
    sheet, builder, folder, count, limit, _, own = VEHICLES[name]
    depth = '../'*len(folder.split('/'))
    levels, triangles, slots = {}, [], []
    for lod in range(count):
        shell = builder(lod)
        triangles.append(shell.triangles())
        level = shell.level(name, lod, depth)
        meshes, parts, materials, slots = carried(name, lod)
        level['meshes'] += meshes
        level['nodes'][0]['parts'] += parts
        level['materials'] += materials
        levels[lod] = level
    assert triangles[0] <= limit and triangles == sorted(triangles, reverse=True), (name, triangles)
    out = Path(sys.argv[sys.argv.index('--out')+1])/folder if '--out' in sys.argv else BOARD/folder
    out.mkdir(parents=True, exist_ok=True)
    slots = [own] if own else slots
    write_glb(out/(name+'.glb'), levels=levels, **({'extras': {'mmColourSlots': slots}} if slots else {}))
    print('RESULT', name, 'triangles', *triangles)


if __name__ == '__main__':
    names = [arg for arg in sys.argv[2:] if arg in VEHICLES] or list(VEHICLES)
    for vehicle in names:
        if sys.argv[1] == 'picture':
            sheet = VEHICLES[vehicle][0]
            sheet.picture(HERE/sheet.name/'sheet.png', TOOLS/f'materials/structures/vehicles/{sheet.name}/sources/artwork.png',
                                         **VEHICLES[vehicle][5])
            print('picture', vehicle)
        else:
            model(vehicle)
