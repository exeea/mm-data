import * as THREE from 'three';

// Preview mapping of docs/gpu-board-materials.md. The original GLB and .tres are never modified.
export async function prepareMaterials(gltf, asset, owned, report) {
  const textureLoader = new THREE.TextureLoader();
  const cache = new Map();
  async function texture(map, template, color = false, channel = null) {
    const key = [map.url, color, channel, template?.wrapS, template?.wrapT, template?.minFilter, template?.magFilter].join('|');
    if (!cache.has(key)) cache.set(key, (async () => {
      let result = await textureLoader.loadAsync(map.url);
      owned.add(result);
      if (channel !== null) {
        const canvas = document.createElement('canvas'); canvas.width = result.image.width; canvas.height = result.image.height;
        const ctx = canvas.getContext('2d', { willReadFrequently: true }); ctx.drawImage(result.image, 0, 0);
        const pixels = ctx.getImageData(0, 0, canvas.width, canvas.height);
        for (let at = 0; at < pixels.data.length; at += 4) {
          const v = channel === 4 ? .2126 * pixels.data[at] + .7152 * pixels.data[at + 1] + .0722 * pixels.data[at + 2] : pixels.data[at + channel];
          pixels.data[at] = pixels.data[at + 1] = pixels.data[at + 2] = v; pixels.data[at + 3] = 255;
        }
        ctx.putImageData(pixels, 0, 0); result = new THREE.CanvasTexture(canvas); owned.add(result);
      }
      result.flipY = false; result.colorSpace = color ? THREE.SRGBColorSpace : THREE.NoColorSpace;
      if (template) for (const key of ['wrapS', 'wrapT', 'minFilter', 'magFilter', 'anisotropy']) result[key] = template[key];
      else result.wrapS = result.wrapT = THREE.RepeatWrapping;
      return result;
    })());
    return cache.get(key);
  }
  const loaded = await gltf.parser.getDependencies('material');
  loaded.forEach(material => owned.add(material));
  for (const surface of asset.surfaces) {
    const material = loaded[surface.index]; if (!material) continue;
    const spec = surface.managed; const glow = new THREE.Color(0, 0, 0);
    if (spec) {
      try {
        material.color.multiply(new THREE.Color().fromArray(spec.tint).convertSRGBToLinear());
        material.roughness = spec.roughness; material.metalness = spec.metallic;
        material.roughnessMap = spec.maps.roughness ? await texture(spec.maps.roughness, material.map, false, spec.channels.roughness) : null;
        material.metalnessMap = spec.maps.metallic ? await texture(spec.maps.metallic, material.map, false, spec.channels.metallic) : null;
        if (!surface.gltf.normalTexture && spec.maps.normal) { material.normalMap = await texture(spec.maps.normal, material.map); material.normalScale.set(spec.normalScale, spec.normalScale); }
        if (!surface.gltf.occlusionTexture && spec.maps.ao) material.aoMap = await texture(spec.maps.ao, material.map, false, spec.channels.ao);
        const tint = new THREE.Color().fromArray(spec.emissionColor).convertSRGBToLinear().multiplyScalar(spec.emissionEnergy);
        if (spec.emissionOperator === 0 || !spec.maps.emission) glow.copy(tint);
        if (spec.maps.emission && !surface.gltf.emissiveTexture) {
          material.emissiveMap = await texture(spec.maps.emission, material.map, true);
          const factor = surface.gltf.emissiveFactor;
          material.emissive.copy(spec.emissionOperator === 0 ? new THREE.Color().setRGB(spec.emissionEnergy, spec.emissionEnergy, spec.emissionEnergy) : tint);
          if (factor?.some(v => v !== 0)) material.emissive.multiply(new THREE.Color().fromArray(factor));
        }
        if (spec.maps.height && !material.normalMap) { material.bumpMap = await texture(spec.maps.height, material.map); material.bumpScale = spec.heightScale / 100 * (spec.heightFlip ? -1 : 1); }
      } catch (error) { report(`${surface.name}: map preview failed: ${error.message}`); }
    }
    const paint = !!surface.gltf.extras?.mmPaintMask;
    if (paint) { material.transparent = false; material.alphaTest = 0; }
    if (paint || glow.r || glow.g || glow.b) {
      material.onBeforeCompile = shader => {
        shader.uniforms.mmGlow = { value: glow };
        shader.fragmentShader = 'uniform vec3 mmGlow;\n' + shader.fragmentShader;
        shader.fragmentShader = shader.fragmentShader.replace('#include <emissivemap_fragment>', '#include <emissivemap_fragment>\ntotalEmissiveRadiance += mmGlow;');
        if (paint) shader.fragmentShader = shader.fragmentShader.replace('#include <color_fragment>', `
          #if defined(USE_COLOR) || defined(USE_COLOR_ALPHA)
            #ifdef USE_MAP
              diffuseColor.rgb *= mix(vec3(1.0), vColor.rgb, texture2D(map, vMapUv).a);
            #else
              diffuseColor.rgb *= vColor.rgb;
            #endif
          #endif
        `);
      };
      material.customProgramCacheKey = () => `mm-paint-${paint}-glow`;
    }
    material.needsUpdate = true;
  }
  // GLTFLoader creates vertex-color and flat-shading derivatives during parsing. Keep those flags,
  // but apply the same managed surface and shader hooks to every rendered derivative.
  gltf.scene.traverse(object => {
    if (!object.isMesh) return;
    const association = gltf.parser.associations.get(object.material);
    const index = association?.materials;
    const source = loaded[index];
    if (source && source !== object.material) {
      const vertexColors = object.material.vertexColors, flatShading = object.material.flatShading;
      object.material.copy(source); object.material.vertexColors = vertexColors; object.material.flatShading = flatShading;
      object.material.onBeforeCompile = source.onBeforeCompile; object.material.customProgramCacheKey = source.customProgramCacheKey;
    }
    object.userData.mmMaterial = index;
  });
}

export function modifyGeometry(gltf, asset, owned) {
  gltf.scene.traverse(object => {
    if (!object.isMesh) return;
    owned.add(object.geometry); object.geometry = object.geometry.clone();
    const geometry = object.geometry, count = geometry.attributes.position.count;
    let colors = geometry.attributes.color;
    if (!colors) { colors = new THREE.Float32BufferAttribute(new Float32Array(count * 3).fill(1), 3); geometry.setAttribute('color', colors); }
    // Convert normalized/interleaved colors to an editable float copy; glTF colors are already linear.
    const values = new Float32Array(count * colors.itemSize);
    for (let i = 0; i < count; i++) for (let c = 0; c < colors.itemSize; c++) values[i * colors.itemSize + c] = colors.getComponent(i, c);
    colors = new THREE.Float32BufferAttribute(values, colors.itemSize); geometry.setAttribute('color', colors);
    const change = asset.surfaces[object.userData.mmMaterial]?.changes;
    if (change?.colours && change.colours.length !== count) throw Error('Variant colour count differs from its primitive');
    for (let i = 0; i < count; i++) for (let c = 0; c < colors.itemSize; c++) {
      if (change?.colours) colors.array[i * colors.itemSize + c] = change.colours[i][c];
      else if (change?.colourScale) colors.array[i * colors.itemSize + c] *= change.colourScale[c] ?? 1;
    }
    geometry.userData.originalColors = colors.array.slice();
    if (geometry.attributes.uv) geometry.userData.originalUv = geometry.attributes.uv.clone();
    object.mmOriginalMaterial = object.material;
  });
}

export function applyColors(scene, slots, replacements) {
  scene.traverse(object => {
    if (!object.isMesh) return;
    const geometry = object.geometry, ids = geometry.attributes._colour_slot, color = geometry.attributes.color;
    if (!ids || !color) return;
    const original = geometry.userData.originalColors;
    for (let i = 0; i < ids.count; i++) {
      const slot = Math.round(ids.getX(i)) - 1;
      if (!slots[slot] || !replacements[slot]) continue;
      const from = new THREE.Color(slots[slot].colour), to = new THREE.Color(replacements[slot]);
      for (const [c, key] of ['r', 'g', 'b'].entries()) color.array[i * color.itemSize + c] = (from[key] > 1e-6 ? original[i * color.itemSize + c] / from[key] : 1) * to[key];
    }
    color.needsUpdate = true;
  });
}

// Same atlas contract documented in RigidGlb.label; UVs start from the authored blank-cell layout on every edit.
export function applyLabel(scene, text) {
  const alphabet = ' ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-';
  const meshes = []; let places = 0;
  scene.traverse(object => {
    if (!object.isMesh || !object.mmOriginalMaterial?.userData.mmLabel || !object.geometry.attributes.uv) return;
    meshes.push(object);
    const uv = object.geometry.userData.originalUv;
    for (let i = 0; i < uv.count; i++) places = Math.max(places, Math.floor(uv.getX(i)) + 1);
  });
  const shown = text.toUpperCase().slice(0, places), start = Math.floor((places - shown.length) / 2);
  for (const object of meshes) {
    const uv = object.geometry.attributes.uv, original = object.geometry.userData.originalUv;
    for (let i = 0; i < uv.count; i++) {
      const u = original.getX(i), v = original.getY(i), place = Math.floor(u), index = place - start;
      const character = index >= 0 && index < shown.length ? Math.max(0, alphabet.indexOf(shown[index])) : 0;
      uv.setXY(i, place + (character % 8 + (u - place) * 8) / 8, (Math.floor(character / 8) + v * 8) / 8);
    }
    uv.needsUpdate = true;
  }
}
