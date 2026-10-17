from researchledger.leakage import REDACTED, is_allowed, scan_lines

# Secret-shaped test values are assembled at runtime so no token-like string is ever committed.
HF_TOKEN = "hf" + "_" + "A1b2C3d4" * 5
PRIVATE_KEY = "-----BEGIN " + "RSA PRIVATE KEY-----"


def lines(*texts):
    return list(enumerate(texts, start=1))


def test_url_token_is_redacted_and_logged_without_its_value():
    url = "see [report](https://wandb.ai/r/x?accessToken=" + "abc123secretvalue" + "&view=1)"
    result = scan_lines("doc.md", lines("intro", url))
    assert result.findings == []
    assert result.lines[1][1] == "see [report](https://wandb.ai/r/x?accessToken=" + REDACTED + "&view=1)"
    assert [(r.line, r.param) for r in result.redactions] == [(2, "accesstoken")]
    assert "abc123secretvalue" not in repr(result.redactions)


def test_real_secrets_fail_with_line_and_kind_but_no_value():
    result = scan_lines("doc.md", lines("ok", "token: " + HF_TOKEN, PRIVATE_KEY))
    assert [(f.line, f.kind) for f in result.findings] == [(2, "Hugging Face token"), (3, "private key")]
    assert HF_TOKEN not in repr(result.findings)


def test_secret_assignment_fails():
    result = scan_lines("doc.md", lines("export WANDB_API_KEY=" + "0123456789abcdef"))
    assert [f.kind for f in result.findings] == ["secret assignment"]


def test_embedded_image_and_email_fail():
    result = scan_lines("doc.md", lines("![x](data:image/png;base64,iVBOR)", "mail me at a.person@example.org"))
    assert [f.kind for f in result.findings] == ["embedded image", "email address (person identifier)"]


def test_git_ssh_remote_is_not_an_email():
    assert scan_lines("doc.md", lines("git clone git@github.com:org/repo.git")).findings == []


def test_only_text_documents_are_allowed():
    assert is_allowed("docs/a.md") and is_allowed("paper/main.tex") and is_allowed("nb/x.ipynb")
    assert not is_allowed("data/labels.csv") and not is_allowed("fig.png") and not is_allowed("run.jsonl")
