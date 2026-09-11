import { spawnSync } from 'node:child_process';
const commands = process.argv[2] === 'build'
  ? [['node_modules/typescript/bin/tsc', '--noEmit'], ['node_modules/vite/bin/vite.js', 'build']]
  : [];
if (!commands.length) throw new Error('Expected build');
for (const args of commands) {
  const result = spawnSync(process.execPath, args, { stdio: 'inherit' });
  if (result.error) throw result.error;
  if (result.status !== 0) process.exit(result.status ?? 1);
}
