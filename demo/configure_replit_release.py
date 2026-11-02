"""Prepare the existing workspace's Python deployment. Does not publish."""
from pathlib import Path
import json
import re
import tomllib

workspace = Path.cwd().resolve()
backend = 'evidence-explorer-integrated-20261101'
assert (workspace / backend / 'release.py').is_file(), 'Extract the release bundle first'
config = workspace / '.replit'
source = config.read_text()
backup = workspace / '.replit.before-evidence-release'
deployment = ('[deployment]\n'
              'deploymentTarget = "autoscale"\n'
              f'build = ["python3", "{backend}/release.py", "build"]\n'
              f'run = ["python3", "{backend}/release.py", "serve"]\n')
pattern = r'(?ms)^\[deployment\]\s*\n.*?(?=^\[(?!deployment(?:\]|\.))|\Z)'
updated, count = re.subn(pattern, deployment + '\n', source, count=1)
assert count == 1, 'Expected exactly one deployment section'
before = tomllib.loads(source)
after = tomllib.loads(updated)
assert {k:v for k,v in before.items() if k != 'deployment'} == {k:v for k,v in after.items() if k != 'deployment'}
if source != updated:
    assert not backup.exists(), 'A release backup exists; inspect it before changing configuration'
    backup.write_text(source)
    config.write_text(updated)
print(json.dumps({'prepared': after['deployment'], 'published': False}))
