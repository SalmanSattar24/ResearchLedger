"""Build a public-only Replit import ZIP from an explicit source-file allowlist."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from researchledger.corpus import CorpusConfig, GitSource
from researchledger.ingest import ingest
from researchledger.demo import PUBLIC_COMMIT, PUBLIC_SOURCE, validate_public_index


def build():
    dest = ROOT / '.cache' / 'evidence-demo-bundle'
    dest.mkdir(parents=True, exist_ok=True)
    config = CorpusConfig.load(ROOT / 'corpora' / 'marin.yaml')
    source = GitSource(config, cache_dir=ROOT / '.cache' / 'corpora')
    assert config.source == PUBLIC_SOURCE and source.commit == PUBLIC_COMMIT
    index = dest / 'marin.sqlite'
    report = ingest(config, index, source=source)
    validate_public_index(index)
    (ROOT / 'demo' / 'data').mkdir(parents=True, exist_ok=True)
    # Local run uses the same fresh public-only bytes as the import bundle.
    (ROOT / 'demo' / 'data' / 'marin.sqlite').write_bytes(index.read_bytes())
    package = ['__init__.py','demo.py','demo_provider.py','tools.py','retrieve.py','verify.py','leakage.py']
    files = {f'researchledger/{n}': (ROOT/'researchledger'/n).read_bytes() for n in package}
    for name in ['index.html','app.js','style.css']:
        files[f'demo/web/{name}'] = (ROOT/'demo'/'web'/name).read_bytes()
    files['demo/data/marin.sqlite'] = index.read_bytes()
    files['requirements.txt'] = b'pydantic==2.14.1\n'
    files['.replit'] = b'run = "python3 release.py serve"\n\n[deployment]\ndeploymentTarget = "autoscale"\nbuild = ["python3", "release.py", "build"]\nrun = ["python3", "release.py", "serve"]\n\n[[ports]]\nlocalPort = 5000\nexternalPort = 80\n'
    files['.gitignore'] = b'.env\n.env.*\n.cache/\n__pycache__/\n*.pyc\n'
    files['README.md'] = (ROOT/'demo'/'README.md').read_bytes()
    files['configure_replit_preview.py'] = (ROOT/'demo'/'configure_replit_preview.py').read_bytes()
    files['configure_replit_release.py'] = (ROOT/'demo'/'configure_replit_release.py').read_bytes()
    files['configure_replit_artifact_release.py'] = (ROOT/'demo'/'configure_replit_artifact_release.py').read_bytes()
    files['release.py'] = (ROOT/'demo'/'release.py').read_bytes()
    files['PUBLISH_READY.md'] = (ROOT/'demo'/'PUBLISH_READY.md').read_bytes()
    files['PUBLIC_CORPUS_LICENSE.txt'] = source.read('LICENSE')
    # Include upstream NOTICE if present without guessing additional files.
    exists = subprocess.run(['git','-C',str(source.repo),'cat-file','-e',f'{PUBLIC_COMMIT}:NOTICE'],capture_output=True).returncode == 0
    if exists:
        files['PUBLIC_CORPUS_NOTICE.txt'] = source.read('NOTICE')
    files['corpus-manifest.json'] = json.dumps({'source':PUBLIC_SOURCE,'commit':PUBLIC_COMMIT,'index_sha256':hashlib.sha256(index.read_bytes()).hexdigest(),'ingestion':report},indent=2).encode()
    manifest = {n:hashlib.sha256(data).hexdigest() for n,data in files.items()}
    files['bundle-manifest.json'] = json.dumps(manifest,indent=2).encode()
    target = dest/'researchledger-public-demo.zip'
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as z:
        for name, data in files.items(): z.writestr(name,data)
    print(json.dumps({'zip':str(target),'bytes':target.stat().st_size,'files':len(files),'ingestion':report},indent=2))


if __name__ == '__main__':
    build()
