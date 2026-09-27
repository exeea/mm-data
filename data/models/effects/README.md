# Effect meshes

These GLBs are the editable source for the two fixed attack-effect meshes.
They preserve the original Java-built geometry. Placement and animation remain
in the renderer, driven by the shared attack clock.

| File | Root group | Geometry |
|---|---|---|
| `explosion-sphere.glb` | `explosion-sphere-lod0` | 35 vertices, 36 triangles; original 6-by-4 sphere, diameter one |
| `missile-body.glb` | `missile-body-lod0` | Four triangles; closed missile body with per-face vertex colors |

Both have only LOD0. Preserve the group names when editing. Export rigid,
uncompressed GLB. Neither currently needs a texture.

The importer converts glTF Y-up into the game's Z-up coordinates. In game
coordinates the sphere is centered at the origin. The missile points along
+Y, from its base at Y=0 to its tip at Y=2.4; its three base corners lie on a
circle of radius 0.45 in the X/Z plane. The renderer rotates this template
along each flight path and batches its transformed vertices together.

## Explosion and smoke appearance

`GpuAttackEffects` owns the shared sphere model. Energy balls still use the
mesh directly. `GpuExplosionEffects` borrows its mesh for raster coverage;
the visible fire and smoke come from `explosion.vert` / `explosion.frag`.
Keep a closed sphere enclosing radius 0.36 in local coordinates: the shader
scales that interior radius to the desired effect size. Moving its origin,
opening its surface or shrinking it below that bound would clip the effect.

The shader integrates animated density and emission along each viewing ray,
with a cooling fire core, local smoke self-shadowing, atmosphere lighting and
opaque scene-depth clipping. It supports orthographic and perspective views,
including a camera inside the volume. The renderer owns its depth snapshot
and shader; it never samples the active framebuffer's attached depth texture.
Time comes from attack playback, so pausing does not evolve the effect.

At most 128 volumes are drawn, using 24 integration steps per ray and two
short light samples. Large-battle frame-time impact has not been benchmarked.
This is a procedural visual effect without fluid simulation or light cast
onto surrounding objects. Missile trails and flame jets retain their existing
bounded quad batches.

`GpuExplosionSmokeTest` checks imported triangle counts, both cameras, cooling,
paused-frame repeatability, opaque occlusion and the inside-volume camera.
`GpuVolleySmokeTest` and `GpuDestructionSmokeTest` cover attack integration.
