from pathlib import Path
from unittest.mock import MagicMock, patch
from scripts.archive_wayback import submit_to_wayback, archive_all_urls
from scripts.common import StateManager


def test_submit_to_wayback_relative_location():
    session = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.headers = {
        "Content-Location": "/web/20260829204500/http://150.165.254.38/labeet"
    }
    session.get.return_value = mock_resp

    archived_url = submit_to_wayback("http://150.165.254.38/labeet", session)
    assert archived_url == "https://web.archive.org/web/20260829204500/http://150.165.254.38/labeet"
    session.get.assert_called_once_with(
        "https://web.archive.org/save/http://150.165.254.38/labeet",
        headers={"User-Agent": "LabeetAcademicPreservationBot/1.0"},
        timeout=30,
    )


def test_submit_to_wayback_full_http_location():
    session = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.headers = {
        "Content-Location": "https://web.archive.org/web/20260829204500/http://150.165.254.38/labeet"
    }
    session.get.return_value = mock_resp

    archived_url = submit_to_wayback("http://150.165.254.38/labeet", session)
    assert archived_url == "https://web.archive.org/web/20260829204500/http://150.165.254.38/labeet"


def test_submit_to_wayback_no_location():
    session = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.headers = {}
    session.get.return_value = mock_resp

    archived_url = submit_to_wayback("http://150.165.254.38/labeet", session)
    assert archived_url == "https://web.archive.org/web/http://150.165.254.38/labeet"


def test_archive_all_urls_flow(tmp_path: Path):
    state_file = tmp_path / "state.json"
    output_file = tmp_path / "content_brazinst" / "wayback_archive.md"

    state = StateManager(state_file)
    state.mark_completed("http://150.165.254.38/labeet/page1.html", "page1.html", 100, 200)
    state.mark_completed("http://150.165.254.38/labeet/page2.html", "page2.html", 200, 200)

    with patch("scripts.archive_wayback.submit_to_wayback") as mock_submit:
        mock_submit.side_effect = [
            "https://web.archive.org/web/20260829204500/http://150.165.254.38/labeet/page1.html",
            Exception("Connection error"),
        ]

        archive_all_urls(state_file, output_file, delay=0.0)

    assert output_file.exists()
    content = output_file.read_text(encoding="utf-8")
    assert "# Mapeamento do Acervo no Internet Archive (Wayback Machine)" in content
    assert "page1.html" in content
    assert "https://web.archive.org/web/20260829204500/http://150.165.254.38/labeet/page1.html" in content
    assert "FALHA: Connection error" in content
