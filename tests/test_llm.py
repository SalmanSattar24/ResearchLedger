import google.auth
import google.auth.exceptions
from google.oauth2 import credentials as user_credentials
from google.oauth2 import service_account

from researchledger import llm


def _fake_service_account():
    return service_account.Credentials.__new__(service_account.Credentials)


def test_only_a_persons_login_gets_the_quota_project(monkeypatch):
    person = user_credentials.Credentials(token="t", quota_project_id="some-course-project")
    monkeypatch.setattr(google.auth, "default", lambda scopes=None: (person, None))
    assert llm.credentials().quota_project_id == llm.PROJECT

    robot = _fake_service_account()
    monkeypatch.setattr(google.auth, "default", lambda scopes=None: (robot, None))
    assert llm.credentials() is robot  # no quota project: no extra Service Usage role needed


def test_configure_vertex_works_without_any_credentials(monkeypatch):
    def missing(scopes=None):
        raise google.auth.exceptions.DefaultCredentialsError("none")

    monkeypatch.setattr(google.auth, "default", missing)
    monkeypatch.setenv("GOOGLE_CLOUD_QUOTA_PROJECT", "stale")
    llm.configure_vertex()
    import os

    assert "GOOGLE_CLOUD_QUOTA_PROJECT" not in os.environ


def test_is_transient():
    import httpx
    from google.genai import errors

    assert llm.is_transient(errors.ClientError(499, {"error": {"code": 499, "status": "CANCELLED"}}))
    assert llm.is_transient(errors.ServerError(503, {"error": {"code": 503}}))
    assert llm.is_transient(httpx.ReadTimeout("slow"))
    assert not llm.is_transient(errors.ClientError(400, {"error": {"code": 400}}))
    assert not llm.is_transient(ValueError("bad JSON"))


def test_a_question_is_asked_again_after_a_transient_failure(monkeypatch):
    import asyncio

    import pytest
    from google.genai import errors

    from researchledger import agents
    from researchledger.verify import Answer

    calls = []

    async def once(index, question, client):
        calls.append(question)
        if len(calls) == 1:
            raise errors.ClientError(499, {"error": {"code": 499, "status": "CANCELLED"}})
        return agents.Result(question, Answer(status="abstained", reason="x"), 1, [], 0.0, {}, [])

    monkeypatch.setattr(agents, "_ask_once", once)
    r = asyncio.run(agents._ask_async(None, "q", None))
    assert len(calls) == 2 and r.usage["question_tries"] == 2

    async def bad(index, question, client):
        raise errors.ClientError(400, {"error": {"code": 400}})

    monkeypatch.setattr(agents, "_ask_once", bad)
    with pytest.raises(errors.ClientError):  # not transient: fails at once, as before
        asyncio.run(agents._ask_async(None, "q", None))
