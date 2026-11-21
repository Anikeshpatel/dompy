from email.message import Message
from io import BytesIO, StringIO
from urllib.error import HTTPError

import pytest

from dompy import Document, DompyParser


def test_binary_encoding_sniffing_and_overrides():
    assert (
        Document.fromString(b"<meta charset=windows-1252><p>caf\xe9").body.textContent
        == "café"
    )
    assert (
        Document.fromString("<p>BOM ☕".encode("utf-16")).body.textContent == "BOM ☕"
    )
    assert (
        Document.fromString(b"<p>caf\xe9", encoding="windows-1252").body.textContent
        == "café"
    )
    assert Document.fromString(bytearray(b"<p>ok")).body.textContent == "ok"
    assert (
        DompyParser.parseFragment(
            b"<tr><td>caf\xe9", "template", encoding="windows-1252"
        ).textContent
        == "café"
    )


def test_file_paths_streams_and_file_uri(tmp_path):
    path = tmp_path / "page name β.html"
    path.write_bytes(b"<meta charset=windows-1252><title>caf\xe9")
    assert Document.fromFile(path).title == "café"
    assert Document.fromFile(str(path)).title == "café"
    assert Document.fromURI(path.as_uri()).title == "café"
    assert (
        Document.fromURI(path.as_uri().replace("file:///", "file://localhost/")).title
        == "café"
    )
    with path.open("rb") as stream:
        assert Document.fromFile(stream).title == "café"
        assert not stream.closed
    stream = StringIO("<title>Unicode 🌻")
    assert Document.fromFile(stream).title == "Unicode 🌻"
    assert not stream.closed


def test_url_respects_http_charset_and_closes_response(monkeypatch):
    response = BytesIO(b"<title>caf\xe9</title><p>Pr\xe9sent")
    response.headers = Message()
    response.headers["Content-Type"] = "text/html; charset=windows-1252"

    def fetch(url, *, timeout):
        assert url == "https://example.test/page"
        assert timeout == 2
        return response

    monkeypatch.setattr("dompy.document.urlopen", fetch)
    doc = Document.fromURI("https://example.test/page", timeout=2)
    assert doc.title == "café"
    assert doc.body.textContent == "Présent"
    assert response.closed


def test_url_http_error_propagates(monkeypatch):
    def fetch(url, *, timeout):
        raise HTTPError(url, 404, "Not Found", {}, None)

    monkeypatch.setattr("dompy.document.urlopen", fetch)
    with pytest.raises(HTTPError) as error:
        Document.fromURL("http://example.test/missing")
    assert error.value.code == 404


@pytest.mark.parametrize(
    "uri", ["example.com", "ftp://example.com", "file://remote.example/path"]
)
def test_unsupported_url_schemes(uri):
    with pytest.raises(ValueError):
        Document.fromURL(uri)
    with pytest.raises(ValueError):
        Document.fromURI(uri)


def test_invalid_inputs():
    with pytest.raises(TypeError):
        Document.fromString(None)
    with pytest.raises(TypeError):
        DompyParser.parseFragment([], "template")
    with pytest.raises(TypeError):
        DompyParser.parseFragment("x", None)
    with pytest.raises(ValueError):
        Document().createElement("invalid name")
