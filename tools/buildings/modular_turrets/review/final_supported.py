"""Read-only exported-mesh clearance audit for the authored turret layouts.

Requires Python + NumPy and clearance.py beside this file. Run:
    python final_supported.py [--sweep] [--output REPORT.json]
--sweep samples every five degrees; --output writes every case and the metadata. This is a sampled vertex audit,
not a continuous or general-purpose triangle collision solver.
"""
import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import clearance as c

GUNS = ['autocannon-2', 'autocannon-5', 'autocannon-10', 'autocannon-20',
        'autocannon-compact', 'machine-gun', 'laser-small', 'laser-medium',
        'laser-large', 'ppc-light', 'ppc', 'ppc-heavy', 'artillery-light',
        'artillery', 'artillery-heavy', 'gauss-light', 'gauss', 'gauss-heavy',
        'rotary-2', 'rotary-5', 'plasma-rifle', 'plasma-cannon', 'flamer',
        'flamer-heavy', 'hag-20', 'hag-30', 'hag-40']
_racks = {}
exec(compile((Path(__file__).resolve().parents[1]/'racks.py').read_text(encoding='utf-8'), 'racks', 'exec'), _racks)
LAUNCHERS = [_racks['name'](kind, count) for kind, rack in _racks['RACKS'].items() for count in rack['cols']]
GUN_SOCKETS = ['pod-center', 'pod-left', 'pod-right']
MISSILE_SOCKETS = GUN_SOCKETS + ['pod-wide-left', 'pod-wide-right', 'pod-outer-left',
                               'pod-inner-left', 'pod-inner-right', 'pod-outer-right']
BROAD_ARMS = ['arm-left', 'arm-right']
# BuildingTurretVisual.FRONT_BAY_DEPRESSION: a roof gun above front bays stops depressing there.
FRONT_BAY_DEPRESSION = 6
# The parts a roof weapon shows: a gun leaves its front-bay mantlet out.
ROOF_PARTS = ('geometry', 'collar', 'spin', 'receiver')
PILLAR_ARMS = BROAD_ARMS + ['arm-left-0', 'arm-left-1', 'arm-right-0', 'arm-right-1']


def pairs(weapons, sockets, mount):
    """(module, socket, mount): a weapon on the roof 'posts' or, a launcher, on a side 'arm'."""
    return [(weapon, socket, mount) for weapon in weapons for socket in sockets]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--assets', type=Path, default=c.ROOT)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--sweep', action='store_true')
    args = parser.parse_args()
    c.ROOT = args.assets.resolve()
    pitches = list(range(-20, 26, 5)) if args.sweep else [-20, 0, 25]
    # (head, (module, socket, mount) triples, lowest checked world height, depression stop). Roof mounts seat their
    # feet in the hull, so only parts above z = 8 count; side-arm launchers are checked against the whole head down to
    # the bearing. Weapons are checked against their shared mounts (posts, arm bracket) as their support.
    front = ('head-center', 'head-twin', 'head-mixed')
    groups = [('head-pods', pairs(GUNS, GUN_SOCKETS, 'posts'), 8, 20)] + [
        (head, pairs(GUNS, GUN_SOCKETS, 'posts'), 8, FRONT_BAY_DEPRESSION) for head in front] + [
        (head, pairs(LAUNCHERS, MISSILE_SOCKETS, 'posts'), 8, 20) for head in ('head-pods',) + front] + [
        ('head-pillar', pairs(GUNS + LAUNCHERS, ['pod-center'], 'posts'), 8, 20)] + [
        (head, pairs(LAUNCHERS, BROAD_ARMS, 'arm'), 0, 20) for head in ('head-pods', 'head-shoulder') + front] + [
        ('head-pillar', pairs(LAUNCHERS, PILLAR_ARMS, 'arm'), 0, 20)]
    points = {name: next(h['position'] for h in json.loads((c.ROOT / (name + '.json')).read_text())['hardpoints']
                         if h['id'] == 'pin') for name in ('mount-post', 'mount-arm')}
    cases, used, poses, rears = [], {'mount-post', 'mount-arm'}, {}, {}
    for head_name, mounts, floor, depression in groups:
        descriptor = json.loads((c.ROOT / (head_name + '.json')).read_text())
        for lod in (0, 1):
            head, head_matrices = c.load(head_name, lod)
            roof = c.Roof(np.concatenate(list(head.values())))
            shapes = {name: np.concatenate(list(c.load(name, lod, ignore_black=True)[0].values()))
                      for name in ('mount-post', 'mount-arm')}
            used.add(head_name)
            for weapon, socket_name, mount in mounts:
                used.add(weapon)
                for deg in sorted({max(deg, -depression) for deg in pitches}):
                    key = (weapon, lod, deg)
                    if key not in poses:
                        data, matrices = c.load(weapon, lod)
                        pivot = matrices['aim']
                        vertices = np.unique(np.concatenate([
                            t.reshape(-1, 3) for node, t in data.items() if node in ROOF_PARTS]), axis=0)
                        a = math.radians(deg)
                        co, si = math.cos(a), math.sin(a)
                        rotation = np.array([[1, 0, 0], [0, co, -si], [0, si, co]])
                        poses[key] = (vertices - pivot) @ rotation.T + pivot
                    local = poses[key]
                    socket = next(s for s in descriptor['hardpoints'] if s['id'] == socket_name)
                    # This audit intentionally covers the current identity-rotation,
                    # unscaled exterior mounting contract. Fail if that changes.
                    assert socket['node'] == 'yaw' and socket['rotation'] == [0, 0, 0, 1]
                    assert socket['minScale'] == socket['maxScale'] == 1
                    translation = head_matrices['yaw'] + np.array(socket['position'])
                    module = json.loads((c.ROOT / (weapon + '.json')).read_text())
                    if weapon not in rears:
                        # The roof parts' rear, from the detailed level, as UnitEquipmentAssembly.restBounds.
                        data, _ = c.load(weapon, 0)
                        rears[weapon] = float(min(t.reshape(-1, 3)[:, 1].min() for node, t in data.items()
                                                  if node in ROOF_PARTS))
                    trunnion = next(h['position'][0] for h in module['hardpoints'] if h['id'] == 'trunnion')
                    if mount == 'posts':
                        # Rear at the socket, both post pins in its trunnion bosses (BuildingTurretVisual.roofMount);
                        # in the weapon's frame the right post stands at its right side, the left one turned half a turn.
                        post, bearing = shapes['mount-post'], points['mount-post']
                        translation = translation + [0, -rears[weapon], bearing[2]]
                        right = post + [trunnion - bearing[0], 0, -bearing[2]]
                        left = post * [-1, -1, 1] + [bearing[0] - trunnion, 0, -bearing[2]]
                        support = c.shoulder_intersections(np.concatenate([right, left]), local, pivot)
                    else:
                        # Outboard of the bracket's pin, the left bracket the right one rolled half a turn.
                        right = socket['position'][0] > 0
                        bearing = points['mount-arm'][0]
                        offset = bearing + trunnion if right else -bearing - trunnion
                        translation = translation + [offset, 0, 0]
                        bracket = shapes['mount-arm'] if right else shapes['mount-arm'] * [-1, 1, -1]
                        support = c.shoulder_intersections(bracket - [offset, 0, 0], local, pivot)
                    posed = local + translation
                    penetrating = []
                    for point in posed:
                        height = roof.at(*point[:2])
                        if height is not None and point[2] > floor and point[2] < height - .001:
                            penetrating.append((float(height - point[2]), *map(float, point), height))
                    cases.append(dict(head=head_name, module=weapon, lod=lod, socket=socket_name,
                                      translation=translation.tolist(), pitch=deg,
                                      belowRoofVertices=len(penetrating),
                                      worstDepthXYZRoof=max(penetrating) if penetrating else None,
                                      insideShoulderVertices=len(support), shoulderExamples=support[:4]))
    flagged = [r for r in cases if r['belowRoofVertices'] or r['insideShoulderVertices']]
    hashes = {name + ext: hashlib.sha256((c.ROOT / (name + ext)).read_bytes()).hexdigest()
              for name in sorted(used) for ext in ('.glb', '.json')}
    report = dict(metadata=dict(createdUtc=datetime.now(timezone.utc).isoformat(), assets=str(c.ROOT),
                  coordinateFrame='Authored engine Z-up, +Y forward; converted from GLB Y-up/-Z forward.',
                  mounting='World placement from exported yaw translation plus JSON socket position; unit scale; zero insertion.',
                  supportedLayouts='One/two roof guns on the pods/center/twin/mixed heads (above front bays down to a 6-degree depression stop) and one on the pillar roof; one-to-four roof launchers on pods/center/twin/mixed and one on the pillar roof, all on the two-post fork; side-arm launchers on every head flank, stacked pairs on the pillar. The single post and the pedestal are not swept. Low auxiliary MGs are a separate height-separation audit.',
                  method='Moving geometry/collar/spin/receiver vertices against the topmost head triangle at XY; two-ray parity against the fixed posts or arm bracket with whole-AABB rejection. Intended bearing overlap within radius1.12 in pivot YZ is excluded. No asset mutation.',
                  limitations='Discrete vertex samples only. Does not prove continuous swept-volume clearance or detect all triangle/edge intersections. Static seating overlap is excluded. External lamps, recoil offsets, arbitrary front weapon poses and other unit chassis are outside this script. Ray-parity results are diagnostic for inspection because joined meshes may include open surface details.',
                  pitches=pitches, lods=[0, 1], sha256=hashes),
                  summary=dict(cases=len(cases), flaggedCases=len(flagged)), cases=cases)
    if args.output:
        args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'summary':report['summary'], 'examples':flagged[:5]}, indent=2))


if __name__ == '__main__':
    main()
