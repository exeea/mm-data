# MegaMek GLB Viewer for VS Code

A read-only 3D editor for the GLBs in `mm-data`. The viewport stays separate from
the scrollable View, Materials, Parts, Test and Info tabs. No asset is rewritten.

## Install

1. In VS Code, open **Extensions**, choose **⋯ → Install from VSIX…** and select
   `tools/vscode-glb/megamek-glb-viewer.vsix`.
2. Open a `.glb`. If another extension owns the file, right-click its editor tab,
   choose **Reopen Editor With… → MegaMek GLB Viewer**, and optionally configure it
   as the default for `.glb`.
3. Open the `mm-data` folder as a workspace. Normally no configuration is needed.
   **Settings** in the viewer opens the extension's settings. `mmDataPath` accepts
   the checkout folder containing `data/models`; it is useful when viewing a GLB
   outside that checkout.

Command-line installation is also available:

```powershell
code --install-extension tools/vscode-glb/megamek-glb-viewer.vsix
```

## View and inspect

- Source Control and Git diffs open the **Staged**, **Working copy**, or named Git
  revision. Git views load the mesh, textures, `.tres` files and descriptors from
  that revision; missing dependencies never silently use working-copy files.
  Staged views refresh when the index changes. **Open working copy** opens its
  editable-on-disk counterpart beside the revision.
- **Sync views** is on by default for open versions of the same GLB. Orbit, pan,
  zoom, framing, LOD, projection, shading, wireframe, lighting, helpers, variants,
  labels and colour selections follow in both directions. Turn it off in a view
  to inspect that version independently. A missing LOD or variant is reported
  in that view; its existing selection is retained. Parts visibility, selection,
  animations and engine-test assemblies remain independent.
- Orbit with left drag, pan with right drag, zoom with the wheel, and press **F**
  over the viewport to fit. Orthographic is the default projection; perspective
  and four camera presets are available. Camera clipping follows the visible model as you orbit and zoom to
  preserve depth precision between nearby surfaces. The grid includes a board
  hex footprint.
- **Geometry by LOD** shows referenced vertices, triangles and primitives for
  each authored LOD. Hover a row for mesh-instance, material and node counts;
  click it to switch and fit. Helper geometry has a separate row. Vertices count
  unique POSITION-accessor/index pairs; triangles and primitives include repeated
  scene instances. These are authored counts, not engine-generated back faces,
  floors or rendering passes. An assembled kit's visible triangle/mesh counts
  appear in the header.
- Display materials, wireframe, clay, normals or UVs; adjust exposure, environment
  illumination and background. Toggle bloom, model bounds, `cut` geometry and
  `stand-N`, `vehicle-N`, `hide-N` direction markers.
- **Measure two points** reports distance and axis differences in model units.
  **Save PNG** exports the viewport to a location you choose.
- Click geometry to inspect it in **Parts**. Search nodes, hide them, solo a part,
  double-click its name to frame it, or reset visibility. Selection details show
  geometry counts and original node metadata, including joints and hardpoints.
- **Materials** lists only this GLB's materials, with search, map previews,
  factors, channel choices and links to their source `.tres` and images.
- **Info** lists dependencies, diagnostics, file extras and adjacent JSON
  descriptors that reference this mesh. Nothing in those files is executed.

## MegaMek materials and metadata

External `_albedo.png` images under `data/models/board/textures` discover their
adjacent `.tres`. StandardMaterial3D tint, roughness, metallic, selected map
channels, normal strength, occlusion and emission are previewed alongside ordinary
glTF materials, embedded PNG/JPEG textures, vertex colours, alpha cutouts and
double-sided surfaces. Walls retain their separate emissive lamp materials.

Colour-slot presets and custom colours, paint masks, label atlases and seasonal
`mmVariants` such as snow have preview controls. Standard glTF animation playback
is available for inspection; the engine's rigid loader rejects animation tracks
and skins. The Info panel points out that distinction and unsupported engine
extensions, including `KHR_materials_emissive_strength`.

Save changes in Blender or Material Maker and the viewer refreshes its GLB and
material dependencies while keeping the camera. **Reload** is available for an
explicit refresh. A file change invalidates any previous engine-test snapshot.
Preview controls do not save materials, geometry, colour choices or labels.

## Engine validation and connected kits

**Test** reuses the same Java bridge as `tools/blender`; it does not implement a
second set of connection rules. A sibling `megamek_temp` or `megamek` checkout is
detected automatically. Otherwise set `enginePath` to the folder containing
`gradlew` and `gradle/wrapper`.

1. Trust the workspace, then choose **Build / Refresh Engine** once, and again
   after engine changes. The build needs the engine's JDK and Gradle dependencies.
   `javaPath` defaults to `java`; the bridge runs with the JDK recorded by Gradle.
2. Choose **Building / connected kit** or **Rigid asset / scenery**.
3. For kits, set building levels, six connected heights (0 means disconnected),
   rotation and variant seed. Straight/corner/all-side presets fill those inputs.
4. **Validate / Assemble** runs the existing engine loader and displays its returned
   placements. This covers `base`, `floor`, `roof`, `link`, `end`, two-tag corners,
   symmetric rotation, early connection roofs and LOD fallback.
5. **Show authored** returns to the source geometry. **Logs** opens the full engine
   output. A failed test removes a previous successful assembly.

The bridge uses `megamek/build/blender-preview.json`, created by the existing
`:megamek:prepareBlenderPreview` Gradle task. It writes only temporary requests and
results, never the GLB. Engine processes require a trusted workspace. Viewing is
available without running Java or Gradle.

Engine tests run on the working copy. Git revision views disable these actions
so an older/staged model is never accidentally validated against a different
file on disk; use **Open working copy** for engine validation and assembly.

## Preview boundaries

Three.js PBR lighting is an authoring preview, not the game renderer. Custom Godot
shader code is not executed. Lava/ice effects, game parallax, subsurface lighting,
foliage response, generated interiors, terrain fitting and cutaways require the
game. Height/SSS maps remain inspectable; height has a bump approximation when no
normal map is present. Combined GLB and shared-material emission is approximate.
Bloom can also catch bright highlights.

The viewer displays unit meshes, rigs, hardpoint nodes and adjacent descriptor
metadata; it does not assemble equipment loadouts or simulate gameplay animation.
Draco/KTX2/meshopt decoders are not bundled: the shipped MegaMek rigid assets do
not use them, and unsupported compressed GLBs report a load error. Models and
texture dependencies must be local; network image URIs and escaping paths are
rejected. An invalid/missing required dependency produces a visible error.

## Develop and package

Requires Node.js 22 or newer and npm. Dependencies are pinned in `package-lock.json`.

```powershell
cd tools/vscode-glb
npm ci
npm run build
npm test
npm run test:browser
npm run test:extension
npm run audit
npm run package
```

The VSIX includes bundled Three.js and works offline. It contains no game assets,
no telemetry and no CDN dependency. Use **F5** with this folder open in VS Code
for an Extension Development Host. Browser tests use installed Microsoft Edge;
extension tests use a separate VS Code profile. Set `VSCODE_EXECUTABLE` to select
a particular VS Code executable. `test-output` and build/dependency directories
are ignored by Git.

`npm test` exercises GLB parsing, accurate per-LOD counts, path restrictions,
Godot material parsing, shipped asset metadata, and the existing engine bridge
when a sibling checkout is available. Browser tests exercise the actual bundled
viewer and save captures, including a pixel regression for nearly touching
surfaces in both camera modes while orbiting and zooming. The extension-host test
checks registration and the real webview's local resources, materials, statistics
and engine assembly. Git fixtures verify separate staged/working geometry and
materials, index refresh, linked controls, and bidirectional camera movement
without update loops. They use disposable repositories and do not stage project
files.
`npm run audit` reads every shipped GLB and writes a detailed report; warnings
about shading approximations are separate from actual load errors.

The extension code is GPL-3.0-or-later. Bundled Three.js is MIT licensed (see
`dist/THREE-LICENSE.txt`). The separate `mm-data` assets retain their own license.
