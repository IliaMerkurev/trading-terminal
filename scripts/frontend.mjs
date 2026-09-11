import { spawnSync } from 'node:child_process';
import { createRequire } from 'node:module';
import { dirname, join } from 'node:path';
const require = createRequire(import.meta.url);
const entry = (name, path) => join(dirname(require.resolve(`${name}/package.json`)), path);
const commands = process.argv[2] === 'build'
  ? [[entry('typescript', 'bin/tsc'), '--noEmit'], [entry('vite', 'bin/vite.js'), 'build']]
  : [];
if (!commands.length) throw new Error('Expected build');
for (const args of commands) {
  const result = spawnSync(process.execPath, args, { stdio: 'inherit' });
  if (result.error) throw result.error;
  if (result.status !== 0) process.exit(result.status ?? 1);
}
