import { runTests, downloadAndUnzipVSCode } from '@vscode/test-electron';
import path from 'node:path';
import fs from 'node:fs/promises';
import net from 'node:net';
const root = path.resolve(import.meta.dirname, '..');
const executable = process.env.VSCODE_EXECUTABLE || await downloadAndUnzipVSCode({ version: 'stable', cachePath: path.join(root, '.vscode-test') });
const socket = net.createServer(); await new Promise(resolve => socket.listen(0, '127.0.0.1', resolve)); const port = socket.address().port; await new Promise(resolve => socket.close(resolve));
await fs.mkdir(path.join(root, 'test-output'), { recursive: true });
await runTests({ vscodeExecutablePath: executable, extensionDevelopmentPath: root, extensionTestsPath: path.join(root, 'test/host.cjs'),
  extensionTestsEnv: { MM_CDP_PORT: String(port), ...(process.env.MM_SKIP_ENGINE_TEST ? { MM_SKIP_ENGINE_TEST: '1' } : {}) }, reuseMachineInstall: false,
  launchArgs: [path.resolve(root, '../..'), '--disable-extensions', '--disable-workspace-trust', '--skip-welcome', '--skip-release-notes', `--remote-debugging-port=${port}`, '--user-data-dir=' + path.join(root, 'test-output/code-user'), '--extensions-dir=' + path.join(root, 'test-output/code-extensions')] });
