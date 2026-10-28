import { build } from 'esbuild';
import { copyFile, mkdir } from 'node:fs/promises';
await mkdir('dist', { recursive: true });
await build({ entryPoints: ['web/viewer.js'], bundle: true, outfile: 'dist/viewer.js', format: 'iife', target: 'chrome128', minify: true, legalComments: 'linked' });
await copyFile('web/viewer.css', 'dist/viewer.css');
await copyFile('node_modules/three/LICENSE', 'dist/THREE-LICENSE.txt');
