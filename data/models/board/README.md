# 3D board assets

This directory is the libGDX board's independent art source. Runtime never reads
terrain or water from the 2D board's images directory. The Java build stages this
directory with the game's data. Blender is an authoring dependency only.

## Rock and scatter meshes

- `rocks/block-N.glb` and `rocks/boulder-N.glb` (N = 0..7) are sixteen independently
  editable rock variants. Each contains three root nodes named `block-N-lod0`,
  `block-N-lod1`, `block-N-lod2` (or `boulder-N-lod0`, etc.). The library has 48
  meshes and 1,572 triangles. Rough terrain, rims, slopes and cliffs share these files.
- `scatter.glb` contains 26 root nodes: `stone-block-N-lod0` and
  `stone-boulder-N-lod0` (eight triangles each, open base), `bush-N-lod0` (eight
  shrub masses), `grass-lod0` (six triangles) and `plant-lod0` (sixteen).
  The complete scatter kit has 498 triangles. Grass and plants have explicit
  back faces; green and dry grass share geometry.

LOD0 is the most detailed version of that shape. LOD1 and LOD2 are optional;
the loader resolves missing levels once as LOD2 -> LOD1 -> LOD0, sharing the
existing mesh. LOD0 is required. Fallback stays within one shape and file,
so a scatter stone can never select a larger terrain rock. Scatter currently
uses only LOD0. Terrain's first two sampling bands use rock LOD0; subsequent
bands use rock LOD1 and LOD2, preserving the established screen-size thresholds.

These files are the editable mesh source, baked from the original Java shapes.
Import/export one file in Blender as uncompressed GLB, preserving names, triangle
budgets and flat normals. Each shape is a root node. After Y-up to Z-up import,
rocks have their base at zero and a largest horizontal extent of one. There
are no textures or embedded animation clips. Their material is named `geometry`;
the renderer chooses colors and terrain shading. The importer restores shared
corners for CPU ground sampling. Placement, picking and batching share the meshes;
no rock or scatter geometry is generated in-game.

## Contents and editing

- `tileset/saxarba.tileset`: the forced 3D tileset, with all recursive includes
  and referenced images, including references outside the Saxarba subdirectory.
  The 7,295 files are independent copies. Edit these without affecting 2D.
- `buildings/`: 3,295 structure models with roofs derived from the exact selected
  tile image. Simplified outlines retain diagonal walls, curves, disconnected
  parts and courtyards; no runtime pixel extrusion or generic substitutions.
- `building-manifest.json`: each structure's source, facade family, wall tint,
  outline, vertex and triangle counts. The largest has 499 triangles. Fuel tanks
  and industrial structures use their selected Saxarba artwork too; generic
  cylinder/factory substitutes have been removed.
- `bridge.glb`, `field.glb`, and twenty-two foliage GLB
  files, plus 63 additional complete bridge exit patterns, all at or below 480 triangles. Counts and
  the imported Blender source names are in `manifest.json`.
- Each tree GLB contains `-lod0`, `-lod1`, and `-lod2` groups. The near opaque mesh
  removes only fully enclosed faces and keeps the surviving vertex attributes
  unchanged (366Ã¢â‚¬â€œ480 triangles). The original remains available for close
  transparent trees. The two distant meshes have 238Ã¢â‚¬â€œ240 and 94Ã¢â‚¬â€œ96 triangles,
  retaining the source coordinates, bounds, material roles and shared textures.
  The manifest records every level; screen-pixel thresholds live in Java's
  `TreeLod`, so no camera or game state is baked into these assets.
- `textures/foliage/`: nine shared 64 by 64 detail albedos for broad leaves,
  pine needles, hanging willow leaves, palm fronds, ordinary bark, birch bark,
  ringed palm bark, ribbed cactus stems and snow. Source material boundaries keep snow caps separate
  from green foliage and preserve the birch's pale trunk and dark scars. Existing
  vertex colors tint the pale maps; dominant-axis UVs follow the tree's original
  proportions. Snow variants use their own authored geometry. Texture generation
  prompts are recorded in `tools/board-foliage-texture-prompts.json`; the cactus
  map is procedural (`tools/build_cactus_texture.py`, CC0-1.0), and cactus stems
  take a pale sage in place of the source's saturated green.
- `textures/foliage/marsh-sedge.png`: the editable 1254 by 1254 RGBA sedge/cattail
  cutout for marsh vegetation. The renderer filters it to one shared 512 by 512
  texture with mipmaps; all three plant LODs use this same image. Ground peat,
  moss and pools are shaded separately using the existing sculpt earth maps.
- `textures/buildings/`: 128 by 128 runtime facade maps. Light buildings retain
  windows; medium uses concrete, hard reinforced concrete, and heavy armored
  panels. Fortresses/gun emplacements use massive sci-fi walls, hangars use
  large shutter bays, fuel tanks use metal courses, and industry uses service
  panels/vents. Sealed structures and dropships use closed armored panels.
  Source names select the family; opaque roof colors tint each model's walls.
  Ordinary facade courses repeat once per four stories. Hangar doors and
  fortress buttresses span the full height instead of stacking per story.
  Eight light-building windows span 128 world units; other families have fewer,
  larger structural bays at that width.
- `textures/terrain/`: 128 by 128 runtime concrete, dirt, rock and sand maps,
  repeating once per 96 world units. Both texture directories have a
  `full-resolution/` subdirectory containing the untouched editable originals.
  Models and materials reference only the small runtime versions. Rebuild those
  after editing originals with `tools/prepare_board_textures.py`.
- `textures/sculpt/`: the sculpted terrain's thirteen 512 by 512 materials (ground,
  debris, wall and mantle maps for every surface family): `NAME.png` is sRGB albedo
  with normalized height in alpha, `NAME-normal.png` a tangent normal (U right, V
  down) with ambient occlusion in alpha, and `manifest.json` the metres each repeat
  spans. All are original procedural works (CC0-1.0) generated from fixed seeds by
  `tools/build_terrain_materials.py`; no photographs or generated images are used.
  The former `outcrop-*` formations are replaced by the shared GLB rock kit below.
- `textures/cliffs/`: the vertical hex sides' 1024 by 1024 color, tangent normal,
  and packed height/roughness/occlusion maps for rock, sandstone, soil, concrete
  and snow. These retain full mip resolution and use the board's dedicated
  parallax material shader. Missing sets fall back to `textures/terrain/`.
  Rebuild with `tools/prepare_cliff_materials.py`; `--check` verifies all baked
  pixels. Sources and generation prompts live in `tools/cliff-sources/` and
  `tools/cliff-texture-prompts.json`. Optional grayscale `NAME-height.png` sources
  supply authored geometry; otherwise height is an artistic approximation from
  source luminance. No baking or height estimation runs in the game. These maps
  are separate from top tiles, upper rims, cornices, buildings and water beds.
- `textures/bed.png`: a 128 by 128 silt, sand and pebble riverbed albedo;
  water reflections and animation remain in the separate water surface.
- `textures/*-rim.png`: six 128 by 128 pale material-detail maps for grass,
  dirt, sand, rock, concrete and snow. Runtime tints them from the selected
  Saxarba ground artwork, preserving each theme's palette. An irregular mesh
  edge fades into the geology; fixed world-scale UVs crop the texture on short
  walls instead of stretching it to fit. Model rebuilds preserve these maps.
- Liquid artwork comes from this directory's own `tileset/saxarba/anim_water_N.gif`,
  `theme_mars/water_anim_mars_N.gif`, `theme_volcano/water_anim_volcano_N.gif`,
  `base/base_magma_anim_N.gif`, and `water/rapids_anim.gif` / `water/torrent_anim.gif`.
  The latter paths are relative to `tileset/saxarba/`. All are independent copies
  of the original 32-frame, 3.2-second animations. `tools/copy_board_tileset.py`
  includes these runtime-selected images even when the static tileset omits them.
  `GpuWaterShader.USE_PROCEDURAL_WATER` selects shader-generated water patterns
  and palettes matched to this artwork, using the renderer's shared noise field.
  Set it to `false` and rebuild for the authored water GIFs. Both paths share
  wave/rain normals, lighting, reflection, downstream currents and waterfall foam/spray.
  Magma retains its original artwork. `GpuLiquidShader.USE_SHADER_ANIMATION`
  interpolates the original GIF frames; set it to `false` for discrete frame timing.
  In the GIF path, transparent foam is composed onto the water image. Hazardous
  liquid shares the water material with a green tint in both paths.
  The renderer constructs curved banks and actual depth; the static
  `Structured_Water` art is a shoreline reference, not a baked replacement.
  Two nonadjacent water openings form a continuous channel. Elevation drops
  use vertically scrolling, animated water on the waterfall face.
- Exposed top edges reuse the single south-facing `08` patches under
  `tileset/High_Incline/`, oriented per edge. Edit these to change cliff-top
  detail without affecting 2D. The renderer avoids mixing their baked lighting
  with the brighter north-facing variants and leaves road approaches open.
  `normals/High_Incline/` supplies their matching normal maps. Runtime rotates
  these directions with the edge, combines color and normals with the ground
  before lighting, and caches the resulting paired atlas material. The source
  images remain separate. Riverbanks keep the undecorated ground artwork.

Edit roof art under `tileset/`, then rebuild the derived roof texture and mesh.
Opaque source roof pixels and their UV locations are unchanged by the export;
RGB is extended only outside the roof mask to prevent filtering fringes.
Each `buildings/<name>.png` is an exact copy of the original tile artwork,
including transparency and shadows, for inspection beside `<name>.glb`.
The processed RGB roof texture is embedded in the GLB; its offline input is
under `tools/board-models/roofs`. Edit the facade originals under
`textures/buildings/full-resolution/` to change windows/walls. Edit
`tools/building-footprints.json` between preparation
and export to author a silhouette manually.

Models are indexed GLB with positions, flat normals, vertex colors and UVs.
The importer converts glTF Y-up and linear colors back to the board convention.
In the runtime representation Z is up; X/Y use the 84 by 72 pixel hex dimensions.
Plants preserve their original proportions at local height 30. Buildings,
including tanks and industrial structures, stand at Z=0 with their roof at
Z=18: one default board level, visible at useful proportions in ordinary GLB
viewers. Placement fits their actual bounds to the game's feature height;
interior floors/columns share the shell's coordinates and placement. Wall UVs
and facade repetition remain independent of these authored coordinates.
Crops retain their legacy height-one convention. Each bridge is a complete deck
for one of the 64 six-bit exit patterns. `bridge.glb` is the north/south straight
span (mask 09); `bridges/bridge-exits-NN.glb` contains every other pattern.
Each file contains one named LOD0 group. These are connection patterns, not LODs.
The carriageway is 15 units wide, slab bottom Z=-1.5, deck Z=0 and rail top Z=2.5.
Rails follow the outside of the joined deck and leave every connected exit open.
Turns are curved; three-to-six-exit junctions have one open connected center.
The runtime places one GLB per bridge hex at the bridge elevation plus the road
surface clearance. Board scale applies uniformly; terrain-level height affects
only elevation, never slab thickness or rail height.
The deck uses shared road asphalt and the road's normal/surface maps, lighting
and world-space texture phase. Sides and underside use shared repeating concrete.

Rebuild only bridges:
1. In the MegaMek code checkout run `gradlew :megamek:exportBridgeShapes`.
2. In mm-data run `blender --background --python tools/build_bridge_assets.py`.

The exported `tools/board-models/bridge-shapes.json` comes from `BoardRoad` curves
and unioned footprints; the Blender tool triangulates/extrudes it into GLBs.
The main board-asset builder delegates its bridge rebuild to this same tool.
No separate bridge path algorithm or runtime mesh generator is used. Textures and meshes are shared;
translucency changes instance materials, not the assets. Snow trees have their
own snow geometry/materials.
Rough terrain places the shared GLB rock templates in its terrain mesh.
Ground image normal maps remain a separate surface detail. `normals/` mirrors ground image paths
under `tileset/`, appending `.png` to the complete source name (including its
original extension and any crop). `normal-manifest.json` records dimensions,
strength and source pixel hashes. Runtime selects each map through the chosen
albedo image and composites both in the same order, then packs aligned atlases.
No height estimation or normal-map generation runs in the game. Missing maps
for custom art fall back to flat shading until they are prepared.

`tools/prepare_board_normals.py` smooths alpha-weighted image brightness and
bakes constant normals over alternating 4-pixel triangles. Painted brightness
is only an approximation to height; baked highlights can also produce relief.
Rubble/rough use the strongest relief, rocky themes are next, and grass, dirt,
sand, snow, mud/swamp, tundra, fields and ice use gentler detail. Pavement and
paved roads receive neutral maps, including their opaque coverage over grass.
South-edge cliff-top patches use restrained relief at strength 3. Their alpha
masks control both color and normal coverage; reoriented normal mapping retains
the base relief under the rim. These derived maps retain the same limitation as
other painted sources: authored height/normal maps would give more accurate
relief. Missing custom rim normals preserve the base normal map.
F9 opens Tuning, where the Normal maps checkbox switches this shading live.
It starts enabled, and Defaults re-enables it; switching needs no atlas,
geometry or shadow rebuild.
Animated water keeps its separate rendering. These maps affect ground lighting
and bank slopes, not silhouettes, picking, movement or cast-shadow geometry.

## Rebuild

Run from the mm-data root (Python requires Pillow and NumPy):

```text
python tools/copy_board_tileset.py
python tools/build_terrain_materials.py
python tools/prepare_board_textures.py
python tools/prepare_cliff_materials.py
python tools/prepare_cliff_materials.py --check
python tools/test_cliff_materials.py
python tools/prepare_board_normals.py
python tools/prepare_board_normals.py --check
python tools/test_board_normals.py
python tools/prepare_building_footprints.py
blender --background tools/board-assets.blend --python tools/build_saxarba_buildings.py
blender --background tools/board-assets.blend --python tools/build_board_assets.py
python tools/validate_board_assets.py
```

The copy step copies missing files only; it preserves local 3D artwork edits.
It repairs two pre-existing fungus image-path typos in the copy only.
Preparation follows actual building, fuel-tank and industrial entries in the
independent include tree. Family selection lives in `facade_family` in the
preparation script; it recognizes named fortress/hangar/sealed families before
ordinary construction strength, including reinforced SMV structures.
Blender uses constrained triangulation for the simplified roof outlines,
exports runtime files, and saves editable object libraries at
`tools/saxarba-buildings.blend` and `tools/board-assets.blend`.
Use Blender's Append command to load their objects. The source scripts create
their own scenes and do not replace the user's open scene.

The nature pack must be present at
`TO_SORT/many_trees/Ultimate Nature Pack - Jun 2019/Blends` to rebuild foliage. These sources match the user's Quaternius ZIP;
runtime does not need that folder. Export converts Blender's linear colors to
display-space vertex colors, preserving the green/snow material distinction.

`build_board_assets.py` runs `prepare_tree_lods.py` after exporting the trees.
To rebuild detail levels from GLB authoring sources under `tools/board-models/foliage`, run
`blender --background --factory-startup --python tools/prepare_tree_lods.py`.
Near pruning requires an enclosing component to be closed with consistent winding;
surface intersections and boundary contacts are retained. Open palm fronds are
never treated as enclosing solids. Smaller meshes are decimated from the complete
original, rather than a pruned mesh whose canopy could expose missing faces.
The script owns a temporary Blender scene and preserves the active scene.

Validation checks all 3,319 base models and 66 tree detail meshes, their budgets and texture dependencies, structure
roof winding, unchanged opaque roof pixels, facade assignments, small runtime
texture dimensions, preserved source resolution, and independent copied files.
Native Java integration tests additionally check transparency, lighting,
water animation and representative model loading.

## Provenance

Roof/terrain/water art comes from the existing MegaMek data tileset; its license
headers and original paths are retained. The repository license remains at
`../../../LICENSE`.

Trees are simplified derivatives of Quaternius's **Ultimate Nature
Pack (June 2019)**: `CommonTree_1/2/4`, `CommonTree_Dead_2`, `PineTree_1/2/3`,
`BirchTree_2`, `Willow_2`, their corresponding snow models, `PalmTree_1/2`,
`Cactus_2` and `CactusFlowers_2`. The supplied CC0 notice is preserved
in `QUATERNIUS-LICENSE.txt`.

Bridge models are baked from the shared road outlines; crop models are authored with the Blender script.
Dirt, sandstone, rock, concrete and windowed facade albedos were generated with
the built-in image_gen tool; exact prompts are in
`../../../tools/board-texture-prompts.json`. The seven contextual facade prompts
are in `../../../tools/building-texture-prompts.json`; these also used built-in
image_gen. Bed and rim art also use built-in image_gen; their prompts and
references are in `../../../tools/board-rim-texture-prompts.json`. Only the
128 by 128 runtime maps are shipped. The rim maps are pale detail albedos;
their final theme colors come from the hex artwork, and geometry supplies
their uneven lower silhouette.

## Plant GLB packaging

Each of the 22 plant variants has one GLB, for example `pine.glb`, containing
identity groups `pine-lod0`, `pine-lod1`, `pine-lod2`. Their authored geometry,
UVs and material roles are preserved. The runtime chooses one level and resolves
missing optional levels toward LOD0 once while loading. Foliage PNGs remain
external under `textures/foliage`, shared by all variants and levels.
All levels have natural proportions and a base at zero, including when inspected
in an ordinary GLB viewer. Export and LOD preparation never flatten the height.
The complete source meshes for Blender regeneration and visual regression
checks are in `tools/board-models/foliage`; they are not deployed game meshes.

## Building GLBs and textures

All 3,295 Saxarba buildings now use one GLB each, with an identity
`<building>-lod0` group. Each embeds its dedicated roof PNG without changing
the image bytes, and uses a relative URI for one of eight shared facade PNGs.
Roof and wall are separate material groups, not two layers over the same mesh.
Runtime wall materials still scale vertical UVs with building height; `shell`
materials retain full-height UVs. Roof samplers clamp; facade samplers repeat.

`RigidGlb` supports embedded PNG/JPEG diffuse images and local image references.
`ModelTextures` caches images with their sampler state, releases native pixels
after upload, retains encoded bytes for context restoration and gives texture
disposal to the owning asset library. Unit and plant models use the same path.
Only the roof belongs inside each building package; the facade stays shared.
Each building keeps `<building>.png` beside `<building>.glb`: a byte-for-byte
copy of its original tileset image, retaining alpha and shadows. This is for
inspection and is not a runtime texture dependency. The processed roof PNG
stays embedded, with no loose `*-roof.png` under deployed buildings. The
footprint tool copies the original sibling and prepares the filtering-safe
RGB roof under `tools/board-models/roofs`; the exporter embeds that prepared
image. Validation checks the original sibling against its source and the
embedded roof against the source's opaque pixels. There is no measured
runtime performance gain claimed from embedding.

`bridge.glb` and `field.glb` also contain a single LOD0 group. No G3DJ remains
under deployed `data/` or authoring/reference `tools/`. The 475 former tool
meshes also use GLB, including seven empty squad references. All 4,056 deployed GLBs pass Khronos validation with zero errors. One
warning originally came from ancillary metadata in the old external bridge PNG.
The redesigned bridge uses shared asphalt/concrete instead and now validates
with zero errors and warnings.

See the glTF image specification:
https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html#images
