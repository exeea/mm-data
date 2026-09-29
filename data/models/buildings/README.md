# Modular building kits

Store kits as `<family>/<name>.glb`, for example `fortress_light/fortress_light_a_52.glb`.
Do not nest this catalog under the source tileset's `saxarba` directory. The selected tileset artwork remains
the key for legacy fallback under `models/board/buildings`.

Each file contains one building: an identity `<name>-lod0` group and, normally, optional `<name>-lod1`.
Author no more than two levels for this work; simple kits (especially under 200 triangles) can use just `lod0`.
This is an asset budget: if an existing kit supplies `<name>-lod2`, the loader uses that additional level.
Each group contains mesh nodes ending in `-floor0`, `-floor1` (additional upper variants allowed),
and `-roof0` (additional roofs allowed). Roles must match across LODs.

Floor meshes are hollow and exactly 18 units high in authoring Z-up space. Display them stacked in the file;
the loader derives module bases and centers from geometry and discards these display offsets when assembling
N floors plus a roof. All variants share the centered footprint. The roof's flat downward underside defines
the volume used for generated interior floors and struts. Keep notches and courtyards in that surface.
