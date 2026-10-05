# Modular building kits

Store kits as `<family>/<name>.glb`, for example `fortress_light/fortress_light_a_52.glb`.
Do not nest this catalog under the source tileset's `saxarba` directory. The selected tileset artwork remains
the key for legacy fallback under `models/board/buildings`.

Each file contains one building: an identity `<name>-lod0` group and, normally, optional `<name>-lod1`.
Author no more than two levels for this work; simple kits (especially under 200 triangles) can use just `lod0`.
This is an asset budget: if an existing kit supplies `<name>-lod2`, the loader uses that additional level.
Each group contains mesh nodes ending in `-base#`, `-floor#`, and `-roof#`, with at least one variant of each.
Number variants from 0; sparse numbers are also supported. Roles must match across LODs.
For N levels, the runtime chooses one base, N-1 independently chosen floors (including `floor0`), and one roof.
Choices are stable for each placement; changing height preserves the base, roof, and existing lower floors.

Base and floor meshes are exactly 18 units high in authoring Z-up space. Enterable buildings have hollow walls.
Display the modules as an assembled example or as a spaced library rack;
the loader derives module bases and centers from geometry and discards these display offsets when assembling
one base, N-1 floors and a roof. All variants preserve the same horizontal normalization center. For enterable buildings,
the full roof projection intersected with the selected modules' closed mid-storey wall sections defines generated
interior floors and struts. Keep notches and courtyards in those surfaces.

Heavy industrial terrain (`misc/heavy_industrial_a.glb` through `d.glb`) uses the same module naming but represents
height-only cover. It has no generated interior, no building cutaway, and ground-level pointer selection. The kits
are a power generator, bulk silo cluster, chemical reactor rack, and distillation plant. Each contains `base0..1`,
`floor0..3` and `roof0..1` in both LODs. The open ground lane remains clear through every variant.

Six supported base pipes end at `(0, ±36)`, `(±31.5, ±18)`, at Z=4, in authored Z-up coordinates. At default
orientation, equal ground elevation and zero hex padding, adjacent kits share endpoints regardless of family,
height or chosen variants. Upper segments use continuous equipment/service spines, with no outward floating stubs.
See `tools/buildings/build_heavy_industrial.py` and `tools/buildings/heavy-industrial/` for the generator,
Blender library, concept prompt/image, exported counts and assembled preview.
