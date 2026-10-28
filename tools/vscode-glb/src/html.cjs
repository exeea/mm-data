function html({ cspSource, nonce, script, style }) {
  return `<!doctype html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
  <meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src ${cspSource} data: blob:; connect-src ${cspSource} data: blob:; script-src 'nonce-${nonce}'; style-src ${cspSource}; worker-src blob:;">
  <link rel="stylesheet" href="${style}"><title>MegaMek GLB Viewer</title></head><body>
  <header><strong id="filename">MegaMek GLB</strong><span id="revision"></span><span id="summary"></span><div class="toolbar"><label class="check" title="Link camera and preview settings with other open versions of this GLB"><input id="syncViews" type="checkbox" checked>Sync views</label><button id="workingCopy" hidden>Open working copy</button><button id="fit" title="Frame visible geometry (F)">Fit</button><button id="reload">Reload</button><button id="settings">Settings</button><button id="inspectorToggle" aria-expanded="true">Inspector</button></div></header>
  <div id="comparisonNote" hidden role="status"></div>
  <main><section id="viewport" aria-label="3D model viewport"><canvas id="canvas" tabindex="0" aria-label="Orbit with left drag; pan with right drag; zoom with wheel"></canvas><div id="overlay">Loading viewer…</div><div id="hint">Drag to orbit · Right drag to pan · Wheel to zoom · F to fit</div></section>
  <aside id="inspector"><nav aria-label="Inspector tabs"><button class="active" data-tab="view">View</button><button data-tab="materials">Materials</button><button data-tab="parts">Parts</button><button data-tab="test">Test</button><button data-tab="info">Info</button></nav>
  <section class="tab active" id="tab-view"><h2>Geometry by LOD</h2><div id="lodStats"></div><p class="muted">Vertices = unique referenced vertices. Tris / primitives include repeated mesh instances. Click a LOD row to view it.</p><h2>Display</h2>
  <label>LOD<select id="lod"><option value="0">LOD 0</option></select></label>
  <label>Season / variant<select id="variant"><option value="">Default</option></select></label>
  <label>Projection<select id="projection"><option value="ortho">Orthographic</option><option value="perspective">Perspective</option></select></label>
  <div class="buttons"><button data-camera="iso">Isometric</button><button data-camera="front">Front</button><button data-camera="side">Side</button><button data-camera="top">Top</button></div>
  <label>Shading<select id="shading"><option value="pbr">Materials</option><option value="clay">Clay</option><option value="normal">Normals</option><option value="uv">UVs</option></select></label>
  <label class="check"><input id="wire" type="checkbox">Wireframe</label><label class="check"><input id="grid" type="checkbox" checked>Grid & hex footprint</label><label class="check"><input id="helpers" type="checkbox">Cut geometry & stand markers</label><label class="check"><input id="bounds" type="checkbox">Model bounds</label><div class="buttons"><button id="measure">Measure two points</button><button id="screenshot">Save PNG</button></div><p id="measurement" class="muted"></p>
  <label>Exposure<input id="exposure" type="range" min="0.1" max="3" step="0.05" value="1"></label><label>Environment<input id="environment" type="range" min="0" max="3" step="0.05" value="1"></label>
  <label class="check"><input id="bloom" type="checkbox" checked>Emission bloom</label><label>Background<input id="background" type="color" value="#202a35"></label>
  <section id="colours"></section><section id="labelSection" hidden><h2>Label preview</h2><input id="label" placeholder="Label text" maxlength="64" aria-label="Label text"></section>
  <section id="animationSection" hidden><h2>glTF animation</h2><select id="animation" aria-label="Animation"></select><button id="play">Play / Pause</button></section>
  <p class="muted">Preview controls never change the GLB. Game lighting, parallax and procedural effects can differ.</p></section>
  <section class="tab" id="tab-materials"><h2>Materials in this GLB</h2><input id="materialSearch" type="search" placeholder="Filter materials…" aria-label="Filter materials"><select id="materialList" size="6" aria-label="Materials"></select><div id="materialDetail"></div></section>
  <section class="tab" id="tab-parts"><h2>Hierarchy</h2><input id="partSearch" type="search" placeholder="Filter nodes…" aria-label="Filter nodes"><div class="buttons"><button id="showAll">Reset visibility</button><button id="clearSelection">Clear selection</button></div><div id="partList"></div><pre id="selectionInfo"></pre></section>
  <section class="tab" id="tab-test"><h2>Engine asset test</h2><p class="muted">Uses MegaMek’s existing loader and connected-kit assembly rules.</p><p id="enginePath"></p><button id="build">Build / Refresh Engine</button>
  <label>Test<select id="kind"><option value="KIT">Building / connected kit</option><option value="RIGID">Rigid asset / scenery</option></select></label>
  <label>Building levels<input id="height" type="number" min="1" max="100" value="1"></label>
  <fieldset id="connections"><legend>Connected levels (0 = disconnected)</legend>${['N', 'NE', 'SE', 'S', 'SW', 'NW'].map(d => `<label>${d}<input data-reach="${d}" type="number" min="0" max="100" value="0"></label>`).join('')}</fieldset>
  <div class="buttons"><button data-preset="none">None</button><button data-preset="straight">Straight</button><button data-preset="corner">Corner</button><button data-preset="all">All six</button></div>
  <label>Clockwise turn<select id="rotation">${[0, 60, 120, 180, 240, 300].map((d, i) => `<option value="${i}">${d}°</option>`).join('')}</select></label><label>Variant seed<input id="seed" type="number" min="0" max="2147483647" value="0"></label>
  <div class="buttons"><button id="test">Validate / Assemble</button><button id="authored">Show authored</button><button id="logs">Logs</button></div><pre id="engineStatus">No engine test run.</pre></section>
  <section class="tab" id="tab-info"><h2>Diagnostics</h2><div id="diagnostics"></div><h2>Dependencies</h2><div id="dependencies"></div><h2>Descriptor / extras</h2><pre id="metadata"></pre></section>
  </aside></main><footer id="status" role="status">Starting…</footer><script nonce="${nonce}" src="${script}"></script></body></html>`;
}
module.exports = { html };
