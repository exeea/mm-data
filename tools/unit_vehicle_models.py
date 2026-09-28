"""Named vehicle bodies: each vehicle in unit-models/vehicles.json, drawn by its builder in unit_vehicle_chassis.py.

For every vehicle the build writes:

- `bodies/<id>.json` and its GLB: the body, on MegaMek's ground-vehicle rig (`vehicle-v1`);
- `families/<id>.json`: the assembly descriptor MegaMek loads, like its generic tracked or wheeled bodies.

The weapon spots are the generic vehicle bodies' (unit_family_models.build_families), placed from this body's
size; turret weapons leave from the recipe's `turretSocket`, and every mount uses its `weaponScale`.
"""

import json
import re
from pathlib import Path

from unit_mek_models import aim_rotation
from unit_model_geometry import Geometry, sub
from unit_vehicle_chassis import VEHICLE_BUILDERS

RECIPES = Path(__file__).resolve().parent / 'unit-models/vehicles.json'

TURRET_LOCATIONS = (("TU", "turret"), ("RT", "turret"), ("FT", "turret2"))
REAR_FACING = ("RR", "AFT", "ALS", "ARS", "RRLS", "RRRS")
LEFT_FACING = ("LS", "LWG", "LBS")
RIGHT_FACING = ("RS", "RWG", "RBS")
DEFAULT_TURRET_SOCKET = [0, 9, 4]


def body_extent(geometry) -> tuple[float, float, float]:
    """The body's half width, half length and height, measured from the origin as the generic bodies are."""
    points = [point for triangle, _, _ in geometry.faces for point in triangle]
    half_width = max(abs(min(point[0] for point in points)), max(point[0] for point in points))
    half_length = max(abs(min(point[1] for point in points)), max(point[1] for point in points))
    return half_width, half_length, max(point[2] for point in points)


def hardpoint_locations(x: float, y: float, z: float) -> dict[str, tuple[float, float, float]]:
    """Where each vehicle location's weapons sit on a body `x` half wide, `y` half long and `z` tall."""
    return {"BD": (0, y * .6, z * .45), "FR": (0, y, z * .35), "NOS": (0, y, z * .35),
            "LS": (-x * .8, 0, z * .4), "RS": (x * .8, 0, z * .4), "LWG": (-x * .8, 0, z * .4),
            "RWG": (x * .8, 0, z * .4), "RR": (0, -y, z * .4), "AFT": (0, -y, z * .4),
            "FLS": (-x * .65, y * .55, z * .4), "FRS": (x * .65, y * .55, z * .4),
            "ALS": (-x * .65, -y * .55, z * .4), "ARS": (x * .65, -y * .55, z * .4),
            "FRLS": (-x * .65, y * .55, z * .4), "FRRS": (x * .65, y * .55, z * .4),
            "RRLS": (-x * .65, -y * .55, z * .4), "RRRS": (x * .65, -y * .55, z * .4),
            "LBS": (-x * .8, 0, z * .4), "RBS": (x * .8, 0, z * .4), "HULL": (0, 0, z),
            "FSLG": (0, 0, z), "*": (0, y * .35, z * .65),
            # Converted QuadVees keep Mek equipment locations.
            "HD": (0, y * .5, z), "CT": (0, y * .7, z * .5), "LT": (-x * .5, y * .5, z * .5),
            "LA": (-x * .9, y * .3, z * .4), "RA": (x * .9, y * .3, z * .4),
            "LL": (-x * .65, -y * .6, z * .3), "RL": (x * .65, -y * .6, z * .3)}


def facing(location: str, rear: bool) -> tuple[int, int, int]:
    if rear or location in REAR_FACING:
        return 0, -1, 0
    if location in LEFT_FACING:
        return -1, 0, 0
    if location in RIGHT_FACING:
        return 1, 0, 0
    return 0, 1, 0


def hardpoints_and_mounts(geometry, recipe: dict) -> tuple[list[dict], list[dict], list[dict]]:
    """The body's weapon spots, the descriptor's mounts and its chassis rules: facing spots, turret spots,
    the searchlight.

    Optional recipe keys place weapons by role rather than all at one spot:
    - `hullSockets`: {location: [x, y, z]} moves a facing's spot, in body coordinates (e.g. FR onto the front plate).
      `stackRows`: [location, ...] puts that facing's weapons side by side rather than stacked.
    - `turretSockets`: {family: [x, y, z]} a spot on the turret, relative to the turret node, for one weapon family
      (ppc, laser, ballistic, missile...), or a list of spots filled in turn. MegaMek prefers it over the plain
      `turretSocket` for that family.
      `turretSocketScale`: {family: factor} draws that family's weapons larger or smaller than `weaponScale`, and
      `turretSocketStyle`: {family: style} picks their barrel (long, medium, short, recessed), and
      `turretSocketLength`: {family: length} stretches them to that length, and `turretSocketProfile`:
      {family: profile} draws them with another build of their art (e.g. "housing").
    - `turretRules`: [{"names": [...], "socket": [x, y, z], "size": [w, h], "scale": factor}] draws each named
      weapon (MegaMek's internal name) at its own turret spot, whatever its family: the long-range launchers in a
      raised box while the short-range ones, also missiles, take the family spot.
    """
    weapon_scale = recipe.get("weaponScale", .8)
    x, y, z = body_extent(geometry)
    locations = hardpoint_locations(x, y, z)
    for location, position in recipe.get("hullSockets", {}).items():
        locations[location] = tuple(position)
    hardpoints, mounts = [], []
    for location, position in locations.items():
        for rear in (False, True):
            key = location + ("-rear" if rear else "-front")
            hardpoints.append({"id": key, "location": location, "side": "rear" if rear else "front", "node": "hull",
                               "position": sub(position, geometry.pivots["hull"]),
                               "rotation": aim_rotation(facing(location, rear)), "size": [18, 12, 18],
                               "minScale": .25, "maxScale": 2, "roles": ["weapon", "physical", "misc"]})
            mounts.append({"hardpoint": key, "scale": weapon_scale})
            if location in recipe.get("stackRows", []):
                # Weapons sharing this spot sit side by side in a row, not one above another.
                mounts[-1]["stack"] = "rows"
    for location, node in TURRET_LOCATIONS:
        if node not in geometry.pivots:
            continue
        socket = recipe.get("turretSocket", DEFAULT_TURRET_SOCKET) if node == "turret" else DEFAULT_TURRET_SOCKET
        key = location + "-turret"
        hardpoints.append({"id": key, "location": location, "side": "front", "node": node, "position": list(socket),
                           "rotation": [0, 0, 0, 1], "size": [18, 12, 10], "minScale": .25, "maxScale": 2,
                           "roles": ["weapon", "physical", "misc"]})
        mounts.append({"hardpoint": key, "scale": weapon_scale})
        if node != "turret":
            continue
        for family, family_sockets in recipe.get("turretSockets", {}).items():
            # One spot, or a list of spots MegaMek fills in turn: the first weapon of the family takes the first
            # spot, the second the next (the Manticore II's two launchers, one on each side).
            several = isinstance(family_sockets[0], (list, tuple))
            for index, family_socket in enumerate(family_sockets if several else [family_sockets]):
                family_key = location + "-turret-" + family + ("-" + str(index) if several else "")
                hardpoints.append({"id": family_key, "location": location, "side": "front", "node": node,
                                   "position": list(family_socket), "rotation": [0, 0, 0, 1], "size": [18, 12, 10],
                                   "minScale": .25, "maxScale": 2, "roles": ["weapon", "physical", "misc"]})
                mounts.append({"hardpoint": family_key, "family": family,
                               "scale": weapon_scale*recipe.get("turretSocketScale", {}).get(family, 1)})
                if family in recipe.get("turretSocketStyle", {}):
                    # The barrel style for this family's weapons here: long, medium, short or recessed.
                    mounts[-1]["style"] = recipe["turretSocketStyle"][family]
                if family in recipe.get("turretSocketProfile", {}):
                    # Another build of the weapon's art, e.g. "housing" (the SRM family's triangular housing) or
                    # "drum-medium".
                    mounts[-1]["profile"] = recipe["turretSocketProfile"][family]
                if family in recipe.get("turretSocketLength", {}):
                    # How far this family's barrels reach from the spot, in body units, whatever their art's length.
                    mounts[-1]["length"] = recipe["turretSocketLength"][family]
    rules = []
    turret_location = next((location for location, node in TURRET_LOCATIONS if node == "turret"
                            and "turret" in geometry.pivots), None)
    for index, rule in enumerate(recipe.get("turretRules", []) if turret_location else []):
        rule_key = "turret-rule-" + str(index)
        width, height = rule.get("size", [12, 10])
        hardpoints.append({"id": rule_key, "location": turret_location, "side": "front", "node": "turret",
                           "position": list(rule["socket"]), "rotation": [0, 0, 0, 1], "size": [width, 6, height],
                           "minScale": .25, "maxScale": 2, "roles": ["weapon", "physical", "misc"]})
        for name in rule["names"]:
            # One rule per weapon, drawn with its own art: a rule's drawAs is a single name.
            rules.append({"match": "^" + re.escape(name) + "$", "exclude": "", "drawAs": name,
                          "placement": {"hardpoint": rule_key, "family": "", "form": "", "bay": False,
                                        "scale": weapon_scale*rule.get("scale", 1), "rule": True}})
    hardpoints.append({"id": "external-searchlight", "location": "BD", "side": "front", "node": "hull",
                       "position": sub((x * .3, y * .2, z * .85), geometry.pivots["hull"]),
                       "rotation": [0, 0, 0, 1], "size": [8, 8, 8], "minScale": .4, "maxScale": 2,
                       "roles": ["misc"]})
    mounts.append({"hardpoint": "external-searchlight", "family": "lamp", "scale": .8})
    return hardpoints, mounts, rules


def build_vehicles(output, export_asset, write_json, only=None):
    """Exports every named vehicle, or only the one whose id is `only`; returns the manifest entries by key."""
    recipes = json.loads(RECIPES.read_text(encoding='utf-8'))['vehicles']
    if only is not None:
        recipes = [recipe for recipe in recipes if recipe['id'] == only]
        if not recipes:
            raise ValueError(f'vehicles.json has no vehicle with the id {only}')
    assets = {}
    for recipe in recipes:
        vehicle_id = recipe['id']
        builder = VEHICLE_BUILDERS.get(vehicle_id)
        if builder is None:
            raise ValueError(f'unit_vehicle_chassis.py has no builder registered for {vehicle_id}')
        geometry = Geometry(modular=True)
        builder(geometry)
        if 'hull' not in geometry.pivots or not geometry.faces:
            raise ValueError(f"{vehicle_id}: the builder made no hull (a vehicle needs g.joint('hull', ...))")
        hardpoints, mounts, rules = hardpoints_and_mounts(geometry, recipe)
        joints = {node: node for node in geometry.pivots}
        key = 'bodies/' + vehicle_id
        assets[key] = export_asset(geometry, output, key, 'body', 'vehicle', 'vehicle-v1', joints, hardpoints)
        descriptor = {'schema': 2, 'kind': 'family', 'family': 'vehicle', 'body': 'units/modular/' + key + '.json',
                      'equipment': 'units/modular/equipment.json', 'mounts': mounts}
        if rules:
            descriptor['rules'] = rules
        write_json(output / 'families' / (vehicle_id + '.json'), descriptor)
        print(f"{vehicle_id}: {assets[key]['triangles']} triangles, {len(hardpoints)} weapon spots")
    return assets
