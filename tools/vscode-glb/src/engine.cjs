const fs = require('node:fs/promises');
const path = require('node:path');
const os = require('node:os');
const { spawn } = require('node:child_process');
const { exists } = require('./assets.cjs');

async function findEngine(configured, dataRoot, folders = []) {
  const candidates = configured ? [configured] : [...folders, ...['megamek_temp', 'megamek'].map(name => path.join(dataRoot ? path.dirname(dataRoot) : process.cwd(), name))];
  for (const root of candidates) {
    if (await exists(path.join(root, 'gradle/wrapper/gradle-wrapper.jar')) && await exists(path.join(root, 'megamek/build.gradle'))) return root;
  }
  return null;
}
function run(executable, args, cwd, onOutput = () => {}, signal, timeout = 120000) {
  return new Promise((resolve, reject) => {
    const child = spawn(executable, args, { cwd, windowsHide: true, shell: false, signal, timeout });
    let output = '';
    const receive = chunk => { const text = chunk.toString(); output = (output + text).slice(-16000); onOutput(text); };
    child.stdout.on('data', receive); child.stderr.on('data', receive);
    child.on('error', reject);
    child.on('close', (code, killedBy) => code === 0 ? resolve(output) : reject(Error(`Engine process failed (${killedBy || code}).\n${output}`)));
  });
}
async function buildEngine(root, java, output, signal) {
  if (!root) throw Error('Configure the MegaMek checkout in Viewer Settings first.');
  return run(java, ['-cp', path.join(root, 'gradle/wrapper/gradle-wrapper.jar'), 'org.gradle.wrapper.GradleWrapperMain', ':megamek:prepareBlenderPreview', '--console=plain'], root, output, signal, 600000);
}
async function preview(root, request, output, signal) {
  if (!root) throw Error('Configure the MegaMek checkout in Viewer Settings first.');
  const configFile = path.join(root, 'megamek/build/blender-preview.json');
  if (!await exists(configFile)) throw Error('Build / Refresh Engine first. This uses the same bridge as the Blender add-on.');
  const config = JSON.parse(await fs.readFile(configFile, 'utf8'));
  if (typeof config.java !== 'string' || !path.isAbsolute(config.java) || typeof config.classpath !== 'string') throw Error('Invalid engine runtime descriptor. Build / Refresh Engine again.');
  const folder = await fs.mkdtemp(path.join(os.tmpdir(), 'mm-glb-preview-'));
  try {
    const input = path.join(folder, 'request.json'), result = path.join(folder, 'result.json');
    await fs.writeFile(input, JSON.stringify(request));
    await run(config.java, ['-Djava.awt.headless=true', '-cp', config.classpath, 'megamek.client.ui.clientGUI.boardview.gpu.BlenderAssetPreview', input, result], path.join(root, 'megamek'), output, signal);
    const response = JSON.parse(await fs.readFile(result, 'utf8'));
    if (!response.ok) throw Error(response.error || 'Engine rejected this asset');
    if (!Array.isArray(response.instances) || response.instances.some(i => typeof i.node !== 'string' || i.matrix?.length !== 16 || !i.matrix.every(Number.isFinite))) throw Error('Invalid engine placement response');
    return response;
  } finally { await fs.rm(folder, { recursive: true, force: true }); }
}
module.exports = { findEngine, run, buildEngine, preview };
