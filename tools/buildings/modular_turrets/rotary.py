"""Rotary autocannons (RAC/2, RAC/5): six barrels in a ring around a spindle, held by clamp rings ahead of the drive
drum, on the autocannon receivers and mantlets (ballistic.py reads these tiers from its calibre table). The cluster starts at the rear datum Y=0 and belongs to the recoil joint.
"""
import math
# HERE, the kit folder, is set by the file that loads this one (author.py or a family module).
_ac = {'HERE': HERE}
exec(compile((HERE/'ballistic.py').read_text(encoding='utf-8'), 'ballistic', 'exec'), _ac)

# Receiver and pivot as ballistic.CALIBRES; cluster length, ring radius of the barrels and barrel radius.
TIERS = {
    '2': dict(L=10.4, w=3.8, h=3.5, cy=4.2, cz=6.8, barrel=15.0, cluster=.62, tube=.2, jacket=1.05),
    '5': dict(L=11.0, w=4.2, h=3.8, cy=4.5, cz=6.8, barrel=14.0, cluster=.8, tube=.26, jacket=1.3),
}
_ac['CALIBRES'].update(TIERS)
# The barrel cluster turns about its axis while firing (author.py gives it a spin joint).
SPIN = True
layout, mantlet, body = _ac['layout'], _ac['mantlet'], _ac['body']


def barrel(ref, family, variant, lod):
    """Drive drum, spindle, six barrels and two clamp rings. Returns the cluster's muzzle centre."""
    t = TIERS[variant]
    j, cluster, tube, length = t['jacket'], t['cluster'], t['tube'], t['barrel']
    rim = cluster + tube + .14
    _ac['lathe'](ref, 'Rotary drive drum', [(0, .9 * j, 'steel'), (.9, .9 * j, 'steel'), (.9, j, 'edge'), (1.5, j, 'dark'),
                                            (1.5, .82 * j, 'dark'), (2.3, .82 * j, 'edge'), (2.3, .5 * cluster, 'steel'),
                                            (length - .3, .5 * cluster, 'steel'), (length - .3, .3 * cluster, 'black')], lod)
    for k in range(6):
        a = k * math.tau / 6
        steps = [(2.2, tube), (length - .25, tube), (length, .86 * tube), (length, .5 * tube)]
        ref.ring('Rotary barrel', steps, 'steel', 8 if lod == 0 else 6, (cluster * math.cos(a), cluster * math.sin(a)),
                 axis='Y', bands=['steel', 'edge', 'black'])
    for y, depth in ((.45 * length, .4), (length - .9, .5)):
        _ac['lathe'](ref, 'Barrel clamp ring', [(y, .55 * cluster, 'dark'), (y, rim, 'edge'), (y + depth, rim, 'edge'),
                                                (y + depth, .55 * cluster, 'dark')], lod, 12 if lod == 0 else 8)
    if lod == 0:
        # Clamp bolts sit on the ring's flats, between the barrels.
        flat = rim * math.cos(math.pi / 12)
        for k in range(6):
            a = k * math.tau / 6 + math.pi / 12
            _ac['_shape']['stud'](ref, (flat * math.cos(a), length - .65, flat * math.sin(a)), (math.cos(a), 0, math.sin(a)),
                                  .07 * rim)
    return [(0, length, 0)]
