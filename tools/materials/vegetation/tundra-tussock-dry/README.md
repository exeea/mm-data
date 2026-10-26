# Dry tundra tussock

A single photographic sedge cutout for upright crossed cards. The dry straw skirt and muted olive center give it a low, irregular crown. The source is generated artwork, not a botanical photograph.

- Editable graph: `tundra-tussock-dry.ptex`.
- Unchanged source and generation prompt: `sources/tundra-tussock-dry.png` and `sources/prompt.txt`.
- Export: `data/models/board/textures/vegetation/tundra-tussock-dry.tres` and `tundra-tussock-dry_albedo.png` in the mm-data repository.
- Exported image: 1024 x 1024, sRGB RGB with straight opacity alpha. Roughness 0.88, metallic 0. No height or normal map is supplied.

The source is a front elevation, intended for the game's existing crossed-card clump geometry rather than a ground decal. `RootRegistration` shifts it down by 0.12 UV so the central base meets the existing card's bottom UV at image y=0.98. Keep this registration when editing the pigment or coverage. The clump renderer downsamples its input to 512 x 512 with alpha-aware filtering and clips alpha below 0.32.

This is a catalogued alternative material. The runtime currently selects `vegetation/tundra-tussock`; this variant does not replace or activate over that concurrently authored material. No renderer code was changed.

To reproduce the export, use Material Maker's **Godot/Godot 4 Standard** target. With its MCP, pass `graph_path` pointing to this project, `path` ending in `data/models/board/textures/vegetation/tundra-tussock-dry` (a basename, not a directory), and `exact_8bit: false`. The graph's existing `AlphaPNG8` group already encodes PNG bin centers. The standard `tools/materials/export.py` workflow can also export this project.

Verified: Material Maker loads the graph without problems; a repeat export reproduces both the PNG and TRES exactly; the image has transparent corners and opaque-enough roots at the card baseline; the material references its image and is listed once in the constrained material catalog. This variant has not been activated or visually tested in the running game.
