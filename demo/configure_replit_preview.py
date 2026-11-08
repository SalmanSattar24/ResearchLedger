"""Bridge the existing Replit Vite preview to the standalone Python app.

Run from the Replit workspace root after extracting the public demo into
evidence-explorer-integrated-20261101 and installing requirements into vendor/.
This changes development startup only; it does not publish or configure keys.
"""
from pathlib import Path
import json
import sys

workspace = Path.cwd().resolve()
backend = workspace / 'evidence-explorer-integrated-20261101'
config = workspace / 'artifacts/researchledger-evidence-explorer/vite.config.ts'
assert (backend / 'researchledger/demo.py').is_file(), 'Public backend folder is missing'
assert (backend / 'vendor/pydantic/__init__.py').is_file(), 'Install the demo requirements into vendor/ first'
source = config.read_text()
marker = 'researchledger-public-python-bridge'
if marker in source:
    print('Public Python preview bridge is already configured')
else:
    assert '  server: {' in source and '  plugins: [' in source, 'Unexpected Vite config; refusing to overwrite'
    backup = config.with_name('vite.config.ts.before-public-python-bridge')
    assert not backup.exists(), 'An earlier backup exists; inspect before changing startup'
    backup.write_text(source)
    plugin = '''
    {
      name: 'researchledger-public-python-bridge',
      async configureServer(server) {
        const { spawn } = await import('node:child_process');
        const cwd = path.resolve(import.meta.dirname, '../../evidence-explorer-integrated-20261101');
        const child = spawn('python', ['-m', 'researchledger.demo', '--host', '127.0.0.1', '--port', '5002'], {
          cwd, env: { ...process.env, PYTHONPATH: path.join(cwd, 'vendor') }, stdio: 'inherit',
        });
        child.on('error', () => console.error('Public evidence backend could not start'));
        server.httpServer?.once('close', () => child.kill());
      },
    },
'''
    # Replit's Node workflow may have a different PATH from an interactive
    # shell. Capture the working Python 3 interpreter used to run this helper.
    assert sys.version_info.major == 3
    plugin = plugin.replace("spawn('python',", 'spawn(' + json.dumps(sys.executable) + ',')
    source = source.replace('  plugins: [', '  plugins: [' + plugin, 1)
    source = source.replace('  server: {', "  server: {\n    proxy: { '/': { target: 'http://127.0.0.1:5002', changeOrigin: false } },", 1)
    config.write_text(source)
    print('Installed public Python preview bridge; original Vite config retained beside it')
