"""Check the exact import archive and production startup without model calls."""
from pathlib import Path
import hashlib
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def verify(archive):
    checks = []
    with tempfile.TemporaryDirectory(prefix='rl-release-') as folder:
        target = Path(folder)
        with zipfile.ZipFile(archive) as bundle:
            assert bundle.testzip() is None
            assert all((target/n).resolve().is_relative_to(target) for n in bundle.namelist())
            assert not any(n.endswith(('.env','.pem','.key')) or 'vendor/' in n for n in bundle.namelist())
            bundle.extractall(target)
        checks.append('ZIP integrity and safe paths')
        env = os.environ.copy()
        env.pop('GEMINI_API_KEY',None)
        env.pop('PYTHONPATH',None)
        env['RL_DEMO_FREE_TIER_CONFIRMED']='0'
        subprocess.run([sys.executable,str(target/'release.py'),'check'],cwd=target,env=env,check=True)
        checks.append('manifest hashes and pinned public corpus')
        with socket.socket() as s:
            s.bind(('127.0.0.1',0)); port=s.getsockname()[1]
        env['PORT']=str(port)
        process=subprocess.Popen([sys.executable,str(target/'release.py'),'serve'],cwd=target,env=env,
                                 stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        base=f'http://127.0.0.1:{port}'
        try:
            for _ in range(100):
                try:
                    health=json.load(urlopen(base+'/healthz',timeout=1)); break
                except (URLError,TimeoutError):
                    assert process.poll() is None, 'Production server exited early'
                    time.sleep(.1)
            else: raise RuntimeError('Production readiness timed out')
            assert health['status']=='ok'
            meta=json.load(urlopen(base+'/evidence-api/meta'))
            assert meta['documents']==9 and meta['chunks']==179 and not meta['generated_enabled']
            checks.append('production startup, PORT, health, metadata, disabled generation')
            for path,mime in [('/','text/html'),('/app.js','text/javascript'),('/style.css','text/css')]:
                with urlopen(base+path) as response:
                    assert mime in response.headers['Content-Type']
                    assert response.headers['Content-Security-Policy']
                    assert response.read()
            checks.append('HTML, JavaScript, CSS and response headers')
            def ask(data):
                return json.load(urlopen(Request(base+'/evidence-api/ask',data=json.dumps(data).encode(),headers={'Content-Type':'application/json'})))
            found=ask({'question':'Why did the 32B run switch to QK-Norm?','inject':True})
            assert found['status']=='excerpts' and found['claims'] and found['sources']
            assert found['injected_candidate']['problems'] and found['injected_candidate']['excluded_from_answer']
            assert '987654321' not in found['answer']
            assert ask({'question':'zxqvmbnplkjhgfds'})['status']=='abstained'
            checks.append('real retrieval, line citations, abstention, separate rejected claim')
            for path in ['/.env','/vendor/pydantic/__init__.py','/.cache/demo-usage.sqlite','/../release.py']:
                try: urlopen(base+path)
                except HTTPError as error: assert error.code==404
                else: raise AssertionError('Unexpected public file: '+path)
            try: ask({'question':'QK-Norm','mode':'generated'})
            except HTTPError as error: assert error.code==503
            else: raise AssertionError('Generation unexpectedly enabled')
            checks.append('private filesystem routes unavailable and absent-key fail closed')
        finally:
            process.terminate()
            process.communicate(timeout=10)
        # The release must reject modification before it starts serving.
        (target/'demo/web/app.js').write_text('modified')
        tamper=subprocess.run([sys.executable,str(target/'release.py'),'check'],cwd=target,env=env,capture_output=True)
        assert tamper.returncode != 0 and b'integrity check failed' in tamper.stderr
        checks.append('tampered release fails integrity check')
    return {'status':'passed','archive':str(archive),'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),
            'checks':checks,'provider_calls':0}


if __name__=='__main__':
    archive=ROOT/'.cache/evidence-demo-bundle/researchledger-public-demo.zip'
    report=verify(archive)
    (archive.parent/'release-verification.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
