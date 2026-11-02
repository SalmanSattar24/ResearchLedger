"""Regression for Agent artifact routing overriding root deployment commands."""
from pathlib import Path
import subprocess
import sys
import tomllib


def test_artifact_release_preserves_identity_routes_and_preview(tmp_path):
    backend=tmp_path/'evidence-explorer-integrated-20261101'
    backend.mkdir(); (backend/'release.py').write_text('# fixture')
    folder=tmp_path/'artifacts/researchledger-evidence-explorer/.replit-artifact'
    folder.mkdir(parents=True)
    manifest=folder/'artifact.toml'
    original='''kind = "web"
id = "artifact-identity"
title = "Evidence Explorer"
router = "path"
[[services]]
name = "web"
paths = ["/"]
localPort = 20396
[services.development]
run = "pnpm run dev"
[services.production]
build = ["pnpm", "run", "build"]
serve = "static"
publicDir = "old-prototype/dist"
[[services.production.rewrites]]
from = "/*"
to = "/index.html"
[services.env]
PORT = "20396"
BASE_PATH = "/"
'''
    manifest.write_text(original)
    helper=Path(__file__).resolve().parents[1]/'demo/configure_replit_artifact_release.py'
    subprocess.run([sys.executable,str(helper)],cwd=tmp_path,check=True,capture_output=True)
    final=tomllib.loads(manifest.read_text())
    service=final['services'][0]
    assert final['id']=='artifact-identity' and final['router']=='path'
    assert service['paths']==['/'] and service['localPort']==20396
    assert service['development']['run']=='pnpm run dev'
    assert service['production']['run']['args']==['python3','evidence-explorer-integrated-20261101/release.py','serve']
    assert service['production']['build']['args'][-1]=='build'
    assert service['production']['health']['startup']['path']=='/healthz'
    assert 'serve' not in service['production'] and 'rewrites' not in service['production']
    assert service['env']=={'PORT':'20396','BASE_PATH':'/'}
    assert manifest.with_name('artifact.toml.before-evidence-python').read_text()==original
    # A second preparation must preserve both the final config and the backup.
    subprocess.run([sys.executable,str(helper)],cwd=tmp_path,check=True,capture_output=True)
    assert tomllib.loads(manifest.read_text())==final
