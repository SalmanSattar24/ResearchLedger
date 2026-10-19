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
