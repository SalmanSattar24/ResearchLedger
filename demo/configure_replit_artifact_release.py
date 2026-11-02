"""Prepare an Agent workspace's web artifact for the Python production server.

New application-router workspaces use this manifest instead of root run/build.
Development Vite startup and artifact identity are preserved. Does not publish.
"""
from pathlib import Path
import json
import tomllib

workspace = Path.cwd().resolve()
backend = 'evidence-explorer-integrated-20261101'
manifest = workspace / 'artifacts/researchledger-evidence-explorer/.replit-artifact/artifact.toml'
source = manifest.read_text()
data = tomllib.loads(source)
assert data['kind'] == 'web' and len(data['services']) == 1
service = data['services'][0]
assert service['paths'] == ['/'] and (workspace/backend/'release.py').is_file()
backup = manifest.with_name('artifact.toml.before-evidence-python')
if service.get('production',{}).get('run',{}).get('args') == ['python3',f'{backend}/release.py','serve']:
    print('Python artifact release already configured')
else:
    assert not backup.exists(), 'Inspect existing artifact backup first'
    prefix = source.split('[[services]]',1)[0]
    # Match the generated API artifact's build/run/health contract. Replit runs
    # these commands from the workspace root. Keep the original public port.
    lines = [prefix.rstrip(),'', '[[services]]',
             'name = '+json.dumps(service['name']),
             'paths = '+json.dumps(service['paths']),
             'localPort = '+str(service['localPort']),
             '[services.development]',
             'run = '+json.dumps(service['development']['run']),
             '[services.production.build]',
             'args = '+json.dumps(['python3',f'{backend}/release.py','build']),
             '[services.production.run]',
             'args = '+json.dumps(['python3',f'{backend}/release.py','serve']),
             '[services.production.health.startup]', 'path = "/healthz"',
             '[services.env]']
    env = {**service.get('env',{}), 'PORT':str(service['localPort'])}
    lines.extend(k+' = '+json.dumps(str(v)) for k,v in env.items())
    updated = '\n'.join(lines)+'\n'
    result = tomllib.loads(updated)
    assert result['id'] == data['id']
    assert result['services'][0]['development'] == service['development']
    backup.write_text(source)
    manifest.write_text(updated)
    print(json.dumps({'artifact_production':result['services'][0]['production'],'published':False}))
