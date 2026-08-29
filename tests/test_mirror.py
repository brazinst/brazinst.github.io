from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from bs4 import BeautifulSoup
from scripts.mirror import url_to_local_path, is_allowed_url, rewrite_links_in_html, LabeetMirror


def test_is_allowed_url():
    base = "http://150.165.254.38/labeet"
    assert is_allowed_url(base, "http://150.165.254.38/labeet/contents") is True
    assert is_allowed_url(base, "http://150.165.254.38/labeet/logo.png") is True
    assert is_allowed_url(base, "https://twitter.com/ufpboficial") is False
    assert is_allowed_url(base, "http://sti.ufpb.br/dweb") is False
    assert is_allowed_url(base, "javascript:void(0)") is False
    assert is_allowed_url(base, "mailto:info@ufpb.br") is False


def test_url_to_local_path(tmp_path: Path):
    root = tmp_path / "backup_full"
    # URL de página terminando em diretório ou slug
    path1 = url_to_local_path(root, "http://150.165.254.38/labeet/contents/menu")
    assert path1 == root / "labeet" / "contents" / "menu" / "index.html"

    # URL com extensão de arquivo (css/png/jpg)
    path2 = url_to_local_path(root, "http://150.165.254.38/labeet/logo.png")
    assert path2 == root / "labeet" / "logo.png"

    # URL raiz
    path3 = url_to_local_path(root, "http://150.165.254.38/labeet")
    assert path3 == root / "index.html"


def test_rewrite_links_in_html():
    html = '''<html><head><link rel="stylesheet" href="http://150.165.254.38/labeet/style.css"></head>
              <body><img src="http://150.165.254.38/labeet/logo.png">
              <a href="http://150.165.254.38/labeet/page">link</a>
              <a href="https://twitter.com/ufpboficial">external</a>
              <a href="#section">anchor</a>
              </body></html>'''
    current_url = "http://150.165.254.38/labeet/contents/index.html"
    base_url = "http://150.165.254.38/labeet"
    rewritten = rewrite_links_in_html(html, current_url, base_url)
    assert "http://150.165.254.38/labeet/style.css" not in rewritten
    assert "http://150.165.254.38/labeet/logo.png" not in rewritten
    assert "https://twitter.com/ufpboficial" in rewritten
    assert "#section" in rewritten


def test_labeet_mirror_run(tmp_path: Path):
    backup_dir = tmp_path / "backup_full"
    base_url = "http://150.165.254.38/labeet"
    mirror = LabeetMirror(backup_dir, base_url=base_url)

    html_root = '''<html><body>
        <a href="http://150.165.254.38/labeet/page1">Page 1</a>
        <img src="http://150.165.254.38/labeet/img.png">
    </body></html>'''

    html_page1 = '''<html><body>
        <a href="http://150.165.254.38/labeet/page2">Page 2</a>
    </body></html>'''

    html_page2 = '''<html><body>
        <p>End of chain</p>
    </body></html>'''

    def mock_fetch(url, session, **kwargs):
        resp = MagicMock()
        if url in (base_url, base_url + "/"):
            resp.status_code = 200
            resp.headers = {"Content-Type": "text/html; charset=utf-8"}
            resp.text = html_root
            resp.content = html_root.encode("utf-8")
        elif url == "http://150.165.254.38/labeet/page1":
            resp.status_code = 200
            resp.headers = {"Content-Type": "text/html; charset=utf-8"}
            resp.text = html_page1
            resp.content = html_page1.encode("utf-8")
        elif url == "http://150.165.254.38/labeet/page2":
            resp.status_code = 200
            resp.headers = {"Content-Type": "text/html; charset=utf-8"}
            resp.text = html_page2
            resp.content = html_page2.encode("utf-8")
        elif url == "http://150.165.254.38/labeet/img.png":
            resp.status_code = 200
            resp.headers = {"Content-Type": "image/png"}
            resp.content = b"fake-png-data"
        else:
            resp.status_code = 404
        return resp

    with patch("scripts.mirror.fetch_url", side_effect=mock_fetch):
        mirror.run(max_pages=10)

    assert mirror.state.is_completed(base_url)
    assert mirror.state.is_completed("http://150.165.254.38/labeet/page1")
    assert mirror.state.is_completed("http://150.165.254.38/labeet/page2")
    assert mirror.state.is_completed("http://150.165.254.38/labeet/img.png")

    # Check that resume skips already downloaded items
    with patch("scripts.mirror.fetch_url", side_effect=mock_fetch) as mock_f:
        mirror2 = LabeetMirror(backup_dir, base_url=base_url)
        mirror2.run(max_pages=10)
        # Should not fetch already completed items
        assert mock_f.call_count == 0
