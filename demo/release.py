"""Standalone public-only release: build, check, or serve. Never publishes."""
from pathlib import Path
import hashlib
import json
import os
import runpy
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'vendor'))
sys.path.insert(0, str(ROOT))


def verify_bundle():
    manifest = json.loads((ROOT / 'bundle-manifest.json').read_text())
    for name, expected in manifest.items():
        path = (ROOT / name).resolve()
        if not path.is_relative_to(ROOT) or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise RuntimeError('Release integrity check failed: ' + name)
    return len(manifest)


def check():
    count = verify_bundle()
    from researchledger.demo import Explorer
    from tempfile import TemporaryDirectory
    with TemporaryDirectory() as temp:
        explorer = Explorer(ROOT / 'demo/data/marin.sqlite', Path(temp) / 'usage.sqlite')
        meta = explorer.metadata()
        result = explorer.answer('Why did the 32B run switch to QK-Norm?', inject=True)
        assert meta['documents'] == 9 and meta['chunks'] == 179
        assert result['status'] == 'excerpts' and result['claims']
        assert result['injected_candidate']['problems']
        assert explorer.answer('zxqvmbnplkjhgfds')['status'] == 'abstained'
    print(json.dumps({'release_check': 'passed', 'hashed_files': count,
                      'documents': 9, 'chunks': 179, 'provider_calls': 0}))


def main():
    action = sys.argv[1] if len(sys.argv) == 2 else ''
    if action == 'build':
        verify_bundle()
        uv = shutil.which('uv')
        if not uv:
            raise RuntimeError('Install uv from its official distribution before building')
        subprocess.run([uv, 'pip', 'install', '--target', str(ROOT / 'vendor'),
                        '--upgrade', '-r', str(ROOT / 'requirements.txt')], check=True)
        check()
    elif action == 'check':
        check()
    elif action == 'serve':
        verify_bundle()
        os.chdir(ROOT)
        sys.argv = ['researchledger.demo', '--host', '0.0.0.0', '--port', os.environ.get('PORT', '5000')]
        runpy.run_module('researchledger.demo', run_name='__main__')
    else:
        raise SystemExit('Usage: python3 release.py build|check|serve')


if __name__ == '__main__':
    main()
