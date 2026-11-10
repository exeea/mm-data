"""The layout of a generated kit's JSON spec (data/models/buildings/README.md, "Connected kits").

A kit's writer names its roofs and builds its variants each complete on its own; layout() makes the file of them, what
every variant shares written once under `shared`. dumps() writes it with short values on one line.
"""
import json

ROLES = ('base', 'floor', 'top')  # A variant's storeys: each a list of the runs the game picks among.
RUN_DEFAULTS = ('planar', 'bay')  # A run's fields a kit may state once for all its runs.
WIDTH = 118


def colour(pigment):
    """An sRGB pigment as the #rrggbb a spec's `tint` takes."""
    return '#'+''.join('%02x' % round(255*v) for v in pigment)


def layout(style, pieces, roofs, variants):
    """The file of a kit: its roofs by name, its variants (each naming its `roof`, a hall its `vaulted` one too)."""
    roofs, variants = json.loads(json.dumps([roofs, variants]))  # Copies that share nothing: fields move out of them.
    for variant in variants:
        assert all(variant.get(key, variant['roof']) in roofs for key in ('roof', 'vaulted')), variant['name']
    every = [r for v in variants for role in ROLES for r in v.get(role, ())]+[r for roof in roofs.values() for r in roof.get('runs', ())]
    shared = {}
    for key in RUN_DEFAULTS:  # Stated once where every run of the kit agrees.
        if every and all(key in r and r[key] == every[0][key] for r in every):
            shared[key] = every[0][key]
            for r in every:
                del r[key]
    if len(variants) > 1:
        for key in [k for k in variants[0] if k not in ('name', 'class', *ROLES)]:
            if all(key in v and v[key] == variants[0][key] for v in variants):
                shared[key] = variants[0][key]
                for v in variants:
                    del v[key]
        for role in ROLES:  # A role's fields that all its runs share, in every variant that has the role.
            runs = [r for v in variants for r in v.get(role, ())]
            common = {k: val for k, val in runs[0].items() if k not in ('bays', 'far') and all(k in r and r[k] == val for r in runs)} if runs else {}
            if common and len(runs) > 1:
                shared[role] = common
                for r in runs:
                    for k in common:
                        del r[k]
    return {'style': style, 'pieces': pieces, **({'shared': shared} if shared else {}), 'roofs': roofs, 'variants': variants}


def dumps(value, indent=0, column=0):
    """JSON with whatever fits on a line written on one: `indent` where this value's lines start, `column` where it does."""
    flat = json.dumps(value)
    if len(flat)+column <= WIDTH or not isinstance(value, (dict, list)) or not value:
        return flat
    pad = ' '*(indent+2)
    if isinstance(value, dict):
        rows = [f'{pad}{json.dumps(k)}: {dumps(v, indent+2, indent+4+len(json.dumps(k)))}' for k, v in value.items()]
        return '{\n'+',\n'.join(rows)+'\n'+' '*indent+'}'
    return '[\n'+',\n'.join(pad+dumps(v, indent+2, indent+2) for v in value)+'\n'+' '*indent+']'


def write(path, style, pieces, roofs, variants):
    path.write_text(dumps(layout(style, pieces, roofs, variants))+'\n', encoding='utf-8')
