const vscode = require('vscode');
const crypto = require('node:crypto');
const path = require('node:path');
const { watch } = require('node:fs');
const { findRoots, loadAsset, inside } = require('./assets.cjs');
const { gitSource } = require('./git-source.cjs');
const { viewState } = require('./view-state.cjs');
const { findEngine, buildEngine, preview } = require('./engine.cjs');
const { html } = require('./html.cjs');

function activate(context) {
  const comparisons = new Map();
  const output = vscode.window.createOutputChannel('MegaMek GLB');
  context.subscriptions.push(output);
  context.subscriptions.push(vscode.commands.registerCommand('megamekGlb.configure', () => vscode.commands.executeCommand('workbench.action.openSettings', '@ext:megamek-local.megamek-glb-viewer')));
  context.subscriptions.push(vscode.commands.registerCommand('megamekGlb.open', async uri => {
    uri ||= (await vscode.window.showOpenDialog({ filters: { 'Binary glTF': ['glb'] }, canSelectMany: false }))?.[0];
    if (uri) await vscode.commands.executeCommand('vscode.openWith', uri, 'megamek.glb');
  }));
  context.subscriptions.push(vscode.window.registerCustomEditorProvider('megamek.glb', {
    openCustomDocument: async uri => {
      let git;
      if (uri.scheme === 'git') {
        try { git = JSON.parse(uri.query); } catch { throw Error('Invalid Git GLB reference'); }
        if (typeof git.path !== 'string' || !path.isAbsolute(git.path) || typeof git.ref !== 'string' || git.submoduleOf) throw Error('Unsupported Git GLB reference');
      } else if (uri.scheme !== 'file') throw Error(`Unsupported GLB URI scheme: ${uri.scheme}. Open a file from a local checkout or Source Control.`);
      return { uri, git, dispose() {} };
    },
    async resolveCustomEditor(document, panel) {
      const uri = document.uri, file = document.git?.path || uri.fsPath, fileUri = vscode.Uri.file(file), disposables = [], jobs = new Set();
      let disposed = false, generation = 0, timer, asset, roots, engine, variant = '', watchers = [], running = false;
      let snapshot;
      let watchedDependencies = [file];
      const pathKey = value => process.platform === 'win32' ? path.resolve(value).toLowerCase() : path.resolve(value);
      const config = () => vscode.workspace.getConfiguration('megamekGlb', fileUri);
      const folders = () => (vscode.workspace.workspaceFolders || []).filter(f => f.uri.scheme === 'file').map(f => f.uri.fsPath);
      const post = message => { if (!disposed) panel.webview.postMessage(message); };
      const comparisonKey = pathKey(file);
      if (!comparisons.has(comparisonKey)) comparisons.set(comparisonKey, { views: new Set(), state: null });
      const comparison = comparisons.get(comparisonKey); comparison.views.add(post);
      const dependencyUri = file => snapshot ? vscode.Uri.file(file).with({ scheme: 'git', query: JSON.stringify({ path: file, ref: snapshot.ref }) }) : vscode.Uri.file(file);
      const fail = error => { output.appendLine(error.stack || error.message); post({ type: 'error', message: error.message }); };
      async function reload() {
        const current = ++generation;
        // Invalidate an engine snapshot immediately; never show an old pass after a changed/failed asset.
        post({ type: 'loading' });
        try {
          const gitPath = vscode.workspace.getConfiguration('git').get('path');
          const nextSnapshot = document.git ? await gitSource(file, document.git.ref, typeof gitPath === 'string' && gitPath || 'git') : null;
          if (current !== generation || disposed) return;
          const nextRoots = await findRoots(file, config().get('mmDataPath'), folders(), nextSnapshot?.io);
          const nextEngine = await findEngine(config().get('enginePath'), nextRoots.root, folders());
          if (current !== generation || disposed) return;
          roots = nextRoots; engine = nextEngine;
          panel.webview.options = { enableScripts: true, localResourceRoots: [vscode.Uri.joinPath(context.extensionUri, 'dist'), vscode.Uri.file(path.dirname(file)), vscode.Uri.file(roots.models)] };
          watchers.forEach(w => w.dispose());
          const watchedRoots = [roots.models]; if (!inside(roots.models, file)) watchedRoots.push(path.dirname(file));
          watchers = nextSnapshot ? [] : watchedRoots.map(root => vscode.workspace.createFileSystemWatcher(new vscode.RelativePattern(vscode.Uri.file(root), '**/*.{glb,png,jpg,jpeg,tres,gdshader,json}')));
          const changed = changedUri => {
            if (config().get('autoReload') && (!asset || watchedDependencies.some(p => pathKey(p) === pathKey(changedUri.fsPath)))) {
              clearTimeout(timer); timer = setTimeout(reload, 350);
            }
          };
          for (const watcher of watchers) { watcher.onDidChange(changed); watcher.onDidCreate(changed); watcher.onDidDelete(changed); }
          if (nextSnapshot) {
            const watcher = watch(path.dirname(nextSnapshot.indexPath), (_, name) => {
              if (String(name) === path.basename(nextSnapshot.indexPath) && config().get('autoReload')) { clearTimeout(timer); timer = setTimeout(reload, 350); }
            });
            watcher.on('error', error => output.appendLine(`Git watcher: ${error.message}`));
            watchers.push({ dispose: () => watcher.close() });
          }
          const urlFor = nextSnapshot?.urlFor || ((p, stamp) => panel.webview.asWebviewUri(vscode.Uri.file(p)).with({ query: `v=${stamp}` }).toString());
          const loaded = await loadAsset(file, roots, urlFor, variant, nextSnapshot?.io);
          if (current !== generation || disposed) return;
          snapshot = nextSnapshot; asset = loaded; watchedDependencies = loaded.dependencies;
          asset.revision = snapshot?.label || 'Working copy';
          panel.title = `${path.basename(file)} — ${asset.revision}`;
          post({ type: 'asset', asset, engine, trusted: vscode.workspace.isTrusted, revision: !!snapshot, generation: current, variant });
          if (comparison.state) post({ type: 'linkedView', state: comparison.state });
        } catch (error) { if (current === generation) { asset = null; fail(error); } }
      }
      panel.webview.options = { enableScripts: true, localResourceRoots: [vscode.Uri.joinPath(context.extensionUri, 'dist')] };
      const nonce = crypto.randomBytes(18).toString('base64');
      panel.webview.html = html({ cspSource: panel.webview.cspSource, nonce,
        script: panel.webview.asWebviewUri(vscode.Uri.joinPath(context.extensionUri, 'dist/viewer.js')).toString(),
        style: panel.webview.asWebviewUri(vscode.Uri.joinPath(context.extensionUri, 'dist/viewer.css')).toString() });
      disposables.push(panel.webview.onDidReceiveMessage(async message => {
        if (!message || typeof message.type !== 'string') return;
        try {
          if (message.type === 'ready' || message.type === 'reload') {
            if (message.type === 'ready' && typeof message.variant === 'string' && message.variant.length < 100) variant = message.variant;
            await reload();
          }
          else if (message.type === 'viewState') {
            const state = viewState(message.state); if (!state) return;
            comparison.state = state;
            for (const peer of comparison.views) if (peer !== post) peer({ type: 'linkedView', state });
          }
          else if (message.type === 'workingCopy' && document.git) await vscode.commands.executeCommand('vscode.openWith', fileUri, 'megamek.glb', { viewColumn: vscode.ViewColumn.Beside });
          else if (message.type === 'variant') {
            if (typeof message.value !== 'string' || message.value && !asset?.variants.includes(message.value)) return;
            variant = message.value; await reload();
          } else if (message.type === 'settings') await vscode.commands.executeCommand('megamekGlb.configure');
          else if (message.type === 'logs') output.show(true);
          else if (message.type === 'screenshot') {
            if (typeof message.data !== 'string' || !message.data.startsWith('data:image/png;base64,') || message.data.length > 24_000_000) throw Error('Invalid screenshot');
            const target = await vscode.window.showSaveDialog({ defaultUri: vscode.Uri.file(file.replace(/\.glb$/i, '-preview.png')), filters: { PNG: ['png'] } });
            if (target) await vscode.workspace.fs.writeFile(target, Buffer.from(message.data.slice('data:image/png;base64,'.length), 'base64'));
          }
          else if (message.type === 'openDependency') {
            if (!asset?.dependencies.includes(message.file)) throw Error('Not a dependency of this model');
            await vscode.commands.executeCommand('vscode.open', dependencyUri(message.file));
          } else if (message.type === 'build' || message.type === 'test') {
            if (document.git) throw Error('Open the working copy to run engine tests. This view shows a Git revision.');
            if (!vscode.workspace.isTrusted) throw Error('Engine builds and tests require a trusted workspace. Ordinary viewing remains available.');
            if (running) return;
            if (message.type === 'test' && (!asset || message.generation !== generation)) return;
            const current = generation, controller = new AbortController(); jobs.add(controller); running = true;
            post({ type: 'engineBusy', message: message.type === 'build' ? 'Building engine bridge…' : 'Testing with the engine…' });
            try {
              const log = text => output.append(text);
              if (message.type === 'build') {
                await buildEngine(engine, config().get('javaPath'), log, controller.signal);
                post({ type: 'engineResult', message: 'Engine ready. Choose Validate or Assemble.' });
              } else {
                const settings = message.settings;
                if (!settings || !['KIT', 'RIGID'].includes(settings.kind) || !Number.isInteger(settings.lod) || settings.lod < 0 || settings.lod > 3
                  || !Number.isInteger(settings.height) || settings.height < 1 || settings.height > 100 || !Array.isArray(settings.reach) || settings.reach.length !== 6
                  || !settings.reach.every(n => Number.isInteger(n) && n >= 0 && n <= 100) || !Number.isInteger(settings.rotation) || settings.rotation < 0 || settings.rotation > 5 || !Number.isSafeInteger(settings.seed)) throw Error('Invalid engine test controls');
                const result = await preview(engine, { ...settings, model: file, modelsRoot: roots.models }, log, controller.signal);
                if (current === generation) post({ type: 'assembly', result, kind: settings.kind });
              }
            } catch (error) {
              output.appendLine(error.stack || error.message);
              if (current === generation) post({ type: 'engineResult', error: true, message: error.message });
            } finally { running = false; jobs.delete(controller); post({ type: 'engineIdle' }); }
          }
        } catch (error) { fail(error); }
      }));
      disposables.push(vscode.workspace.onDidChangeConfiguration(event => { if (event.affectsConfiguration('megamekGlb', fileUri)) reload(); }));
      disposables.push(vscode.workspace.onDidGrantWorkspaceTrust(reload));
      panel.onDidDispose(() => { disposed = true; generation++; clearTimeout(timer); watchers.forEach(w => w.dispose()); jobs.forEach(job => job.abort()); disposables.forEach(d => d.dispose()); comparison.views.delete(post); if (!comparison.views.size) comparisons.delete(comparisonKey); });
    }
  }, { supportsMultipleEditorsPerDocument: false, webviewOptions: { retainContextWhenHidden: true } }));
}
module.exports = { activate };
