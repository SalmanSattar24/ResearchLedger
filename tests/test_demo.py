import io
import json
import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from researchledger.corpus import CorpusConfig
from researchledger.demo import DemoHTTPServer, Explorer, PUBLIC_COMMIT, PUBLIC_SOURCE, handler_for
from researchledger.demo_provider import CallBudget, DemoUnavailable, GeminiFreeProvider
from researchledger.ingest import ingest
from researchledger.verify import Answer, Citation, Claim
from test_ingest_retrieve import make_repo


@pytest.fixture
def public_index(tmp_path):
    repo, sha = make_repo(tmp_path, {
        'docs/reports/run.md': '# Run\nThe baseline latency was 100 ms.\nThe candidate latency was 80 ms.\nNo production validation was performed.\n',
        'docs/experiments/control.md': '# Control\nThe optimizer control is incomplete.\n',
    })
    index = tmp_path/'public.sqlite'
    ingest(CorpusConfig('marin',str(repo),sha), index)
    # Synthetic fixture metadata exercises the public-index boundary without
    # fetching a network corpus in unit tests. Real snapshot gets a separate smoke.
    with sqlite3.connect(index) as db:
        db.execute('UPDATE corpus SET source=?,commit_sha=?',(PUBLIC_SOURCE,PUBLIC_COMMIT))
    return index


class FakeProvider:
    def __init__(self, outputs, available=True):
        self.outputs = iter(outputs); self.calls = 0; self.reserved = 0; self.available = available
    def enabled(self): return self.available
    def reserve(self): self.reserved += 2
    def generate(self, system, content):
        self.calls += 1
        return next(self.outputs)


def answer(claim='The baseline latency was 100 ms.', start=2, end=2):
    return {'status':'answered','answer':'IGNORE this unverified prose: 9999', 'claims':[
        {'text':claim,'citations':[{'path':'docs/reports/run.md','start':start,'end':end}]}]}


def make_explorer(public_index,tmp_path,provider=None):
    return Explorer(public_index,tmp_path/'usage.sqlite',provider)


def test_extractive_reuses_core_without_embed_import(public_index,tmp_path,monkeypatch):
    import sys
    monkeypatch.setitem(sys.modules,'researchledger.embed',None)
    r=make_explorer(public_index,tmp_path).answer('baseline latency')
    assert r['status']=='excerpts'
    assert r['verification']=='deterministic_passed_semantics_not_checked'
    assert r['claims'] and all(c['citations'] for c in r['claims'])
    assert 'baseline latency' in r['answer']
    assert r['sources'][0]['url'].startswith(f'https://github.com/marin-community/marin/blob/{PUBLIC_COMMIT}/')


def test_unmatched_question_abstains_without_provider(public_index,tmp_path):
    p=FakeProvider([])
    r=make_explorer(public_index,tmp_path,p).answer('zxqvmbnplkjhgfds','generated')
    assert r['status']=='abstained' and r['sources']==[] and p.calls==0 and p.reserved==0


def test_extracts_relevant_lines_instead_of_comments(public_index,tmp_path):
    with sqlite3.connect(public_index) as db:
        db.execute("UPDATE doc_lines SET text='<!-- hidden marker' WHERE path='docs/reports/run.md' AND line=1")
    r=make_explorer(public_index,tmp_path).answer('candidate latency')
    assert 'candidate latency' in r['answer'] and '<!--' not in r['answer']


def test_table_of_contents_is_not_an_answer(public_index,tmp_path):
    with sqlite3.connect(public_index) as db:
        db.execute("UPDATE doc_lines SET text='- [The baseline latency](#baseline-latency)' WHERE path='docs/reports/run.md' AND line=1")
    r=make_explorer(public_index,tmp_path).answer('baseline latency')
    assert '(#baseline-latency)' not in r['answer'] and 'baseline latency was 100 ms' in r['answer']


def test_generated_success_only_exposes_verified_claims(public_index,tmp_path):
    p=FakeProvider([answer(),{'results':[{'claim':1,'supported':True}]}])
    r=make_explorer(public_index,tmp_path,p).answer('baseline latency','generated')
    assert r['status']=='answered' and r['verification']=='deterministic_and_model_passed'
    assert r['answer']=='The baseline latency was 100 ms.' and '9999' not in r['answer']
    assert p.calls==2 and p.reserved==2


def test_unsupported_number_fails_before_model_support(public_index,tmp_path):
    p=FakeProvider([answer('The baseline latency was 9999 ms.')])
    r=make_explorer(public_index,tmp_path,p).answer('baseline latency','generated')
    assert r['status']=='abstained' and r['answer']=='' and r['claims']==[] and p.calls==1


@pytest.mark.parametrize('verdict',[
    {'results':[]}, {'results':[{'claim':1,'supported':'true'}]},
    {'results':[{'claim':1,'supported':False}]}, {'results':[{'claim':2,'supported':True}]},
    {'results':[{'claim':True,'supported':True}]}, {},
])
def test_missing_wrong_and_negative_support_fail_closed(public_index,tmp_path,verdict):
    p=FakeProvider([answer(),verdict])
    r=make_explorer(public_index,tmp_path,p).answer('baseline latency','generated')
    assert r['status']=='abstained' and not r['answer'] and r['verification']=='blocked'


def test_duplicate_verdict_ids_rejected():
    assert Explorer._support_problems({'results':[{'claim':1,'supported':True},{'claim':1,'supported':True}]},2)


@pytest.mark.parametrize('raw',[
    answer(start=1,end=900), answer(start=-1,end=-1),
    {'status':'answered','claims':[{'text':'x','citations':[{'path':'private/file.md','start':1,'end':1}]}]},
    {'status':'answered','claims':[{'text':'x','sql':'SELECT 1','citations':[{'path':'docs/reports/run.md','start':2,'end':2}]}]},
])
def test_model_cannot_cite_outside_retrieved_context_or_run_sql(public_index,tmp_path,raw):
    p=FakeProvider([raw])
    with pytest.raises(DemoUnavailable): make_explorer(public_index,tmp_path,p).answer('baseline latency','generated')


def test_injected_candidate_is_separate_and_blocked(public_index,tmp_path):
    r=make_explorer(public_index,tmp_path).answer('baseline latency',inject=True)
    assert r['overall']=='blocked_injected_candidate'
    assert r['injected_candidate']['problems']
    assert r['injected_candidate']['text'] not in r['answer']
    assert r['injected_candidate']['excluded_from_answer'] is True
    assert len({s['id'] for s in r['sources']})==len(r['sources'])


def test_no_key_no_network_but_retrieval_available(public_index,tmp_path,monkeypatch):
    monkeypatch.delenv('GEMINI_API_KEY',raising=False)
    e=make_explorer(public_index,tmp_path)
    assert not e.metadata()['generated_enabled']
    with pytest.raises(DemoUnavailable): e.answer('baseline latency','generated')
    assert e.answer('baseline latency')['status']=='excerpts'


def test_public_index_cannot_be_replaced_with_private_corpus(public_index,tmp_path):
    with sqlite3.connect(public_index) as db: db.execute("UPDATE corpus SET source='private',name='private'")
    with pytest.raises(ValueError,match='pinned public'): make_explorer(public_index,tmp_path)


def test_budget_persists_and_reserves_atomically(tmp_path):
    clock=lambda:200000.0
    path=tmp_path/'budget.sqlite'
    b=CallBudget(path,daily=4,minute=4,clock=clock)
    def attempt(_):
        try: b.reserve(2); return True
        except DemoUnavailable: return False
    with ThreadPoolExecutor(max_workers=5) as pool: results=list(pool.map(attempt,range(5)))
    assert sum(results)==2
    with pytest.raises(DemoUnavailable): CallBudget(path,4,4,clock).reserve(2)
    with pytest.raises(DemoUnavailable): CallBudget(path,9999,9999,clock).reserve(21)


def test_budget_rolling_minute_and_utc_reset(tmp_path):
    now=[86410.0]; b=CallBudget(tmp_path/'budget.sqlite',daily=4,minute=2,clock=lambda:now[0])
    b.reserve(2)
    with pytest.raises(DemoUnavailable): b.reserve(2)
    now[0]+=61; b.reserve(2)
    now[0]+=61
    with pytest.raises(DemoUnavailable): b.reserve(2)
    now[0]=172810; b.reserve(2)


def test_provider_uses_fixed_endpoint_header_and_no_tools(tmp_path,monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY','test-key-never-real')
    monkeypatch.setenv('RL_DEMO_FREE_TIER_CONFIRMED','1')
    seen=[]
    def opener(req,timeout):
        seen.append(req)
        return io.BytesIO(json.dumps({'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':'{"ok":true}'}]}}]}).encode())
    p=GeminiFreeProvider(CallBudget(tmp_path/'usage.sqlite'),opener)
    p.reserve(); assert p.generate('rules','public evidence')=={'ok':True}
    req=seen[0]
    assert req.full_url=='https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash-lite:generateContent'
    assert 'test-key' not in req.full_url and req.get_header('X-goog-api-key')=='test-key-never-real'
    assert 'tools' not in json.loads(req.data)


def test_provider_quota_and_secret_errors_never_leak_or_retry(tmp_path,monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY','private-key-test')
    monkeypatch.setenv('RL_DEMO_FREE_TIER_CONFIRMED','1')
    calls=[]
    def opener(req,timeout):
        calls.append(req)
        raise HTTPError('https://example.test/?key=private-key-test',429,'secret private-key-test',{},None)
    p=GeminiFreeProvider(CallBudget(tmp_path/'usage.sqlite'),opener)
    p.reserve()
    with pytest.raises(DemoUnavailable) as err: p.generate('rules','evidence')
    assert '429' in str(err.value) and 'private-key-test' not in str(err.value) and len(calls)==1


@pytest.mark.parametrize('body',[
    {'candidates':[{'finishReason':'MAX_TOKENS','content':{'parts':[{'text':'{}'}]}}]},
    {'candidates':[]}, {'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':'[]'}]}}]},
])
def test_provider_incomplete_responses_fail_closed(tmp_path,monkeypatch,body):
    monkeypatch.setenv('GEMINI_API_KEY','test-key')
    monkeypatch.setenv('RL_DEMO_FREE_TIER_CONFIRMED','1')
    p=GeminiFreeProvider(CallBudget(tmp_path/'budget.sqlite'),lambda *a,**k:io.BytesIO(json.dumps(body).encode()))
    with pytest.raises(DemoUnavailable): p.generate('x','y')


def test_http_contract_validation_and_origin(public_index,tmp_path):
    server=ThreadingHTTPServer(('127.0.0.1',0),handler_for(make_explorer(public_index,tmp_path)))
    thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start()
    base=f'http://127.0.0.1:{server.server_port}'
    try:
        meta=json.load(urlopen(base+'/api/meta')); assert meta['corpus']=='marin'
        assert json.load(urlopen(base+'/healthz'))['status']=='ok'
        assert json.load(urlopen(base+'/evidence-api/meta'))['corpus']=='marin'
        request=Request(base+'/api/ask',data=json.dumps({'question':'baseline latency'}).encode(),headers={'Content-Type':'application/json'})
        assert json.load(urlopen(request))['status']=='excerpts'
        bad=Request(base+'/api/ask',data=b'{}',headers={'Content-Type':'application/json','Origin':'https://unrelated.test'})
        with pytest.raises(HTTPError) as err: urlopen(bad)
        assert err.value.code==403
        invalid=Request(base+'/api/ask',data=b'[]',headers={'Content-Type':'application/json'})
        with pytest.raises(HTTPError) as err: urlopen(invalid)
        assert err.value.code==400
    finally:
        server.shutdown(); server.server_close(); thread.join()


def test_overloaded_server_recovers_without_starting_more_workers(public_index,tmp_path):
    server=DemoHTTPServer(('127.0.0.1',0),handler_for(make_explorer(public_index,tmp_path)),max_connections=1)
    thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start()
    base=f'http://127.0.0.1:{server.server_port}'
    try:
        server.slots.acquire()
        try:
            with pytest.raises(HTTPError) as err: urlopen(base+'/healthz',timeout=3)
            assert err.value.code==503
        finally: server.slots.release()
        assert json.load(urlopen(base+'/healthz',timeout=3))['status']=='ok'
    finally:
        server.shutdown(); server.server_close(); thread.join()
