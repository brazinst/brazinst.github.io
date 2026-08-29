import json
from pathlib import Path
import pytest
import requests
from scripts.common import (
    StateManager,
    atomic_write_text,
    atomic_write_bytes,
    fetch_url,
    log,
)


def test_atomic_write_text(tmp_path: Path):
    target = tmp_path / "subdir" / "test.txt"
    atomic_write_text(target, "olá mundo")
    assert target.exists()
    assert target.read_text(encoding="utf-8") == "olá mundo"


def test_atomic_write_bytes(tmp_path: Path):
    target = tmp_path / "subdir" / "test.bin"
    atomic_write_bytes(target, b"\x00\x01\x02\xff")
    assert target.exists()
    assert target.read_bytes() == b"\x00\x01\x02\xff"


def test_state_manager_resume(tmp_path: Path):
    state_file = tmp_path / "state.json"
    manager = StateManager(state_file)
    assert manager.is_completed("http://example.com/page1") is False

    manager.mark_completed(
        "http://example.com/page1", local_path="page1.html", bytes_count=123
    )
    assert manager.is_completed("http://example.com/page1") is True

    # Recarregar do disco e verificar persistência
    manager2 = StateManager(state_file)
    assert manager2.is_completed("http://example.com/page1") is True
    info = manager2.get_url_info("http://example.com/page1")
    assert info is not None
    assert info["status"] == "completed"
    assert info["bytes_count"] == 123


def test_state_manager_mark_failed(tmp_path: Path):
    state_file = tmp_path / "state.json"
    manager = StateManager(state_file)
    manager.mark_failed("http://example.com/page-err", error="404 Not Found", attempts=2)

    info = manager.get_url_info("http://example.com/page-err")
    assert info is not None
    assert info["status"] == "failed"
    assert info["error"] == "404 Not Found"
    assert info["attempts"] == 2

    # Transition from failed to completed
    manager.mark_completed("http://example.com/page-err", local_path="page-err.html", bytes_count=50)
    assert manager.is_completed("http://example.com/page-err") is True
    assert "http://example.com/page-err" not in manager.data["failed"]


def test_state_manager_corrupted_load(tmp_path: Path):
    state_file = tmp_path / "state.json"
    state_file.write_text("invalid json content", encoding="utf-8")
    manager = StateManager(state_file)
    assert manager.data["visited"] == {}
    assert manager.data["failed"] == {}


def test_log_output(capsys):
    log("Mensagem de teste", level="INFO")
    captured = capsys.readouterr()
    assert "[INFO] Mensagem de teste" in captured.out


def test_fetch_url_success():
    class MockResponse:
        def __init__(self, status_code=200, content=b"hello"):
            self.status_code = status_code
            self.content = content

    class MockSession:
        def __init__(self):
            self.calls = []

        def get(self, url, headers=None, timeout=None):
            self.calls.append((url, headers, timeout))
            return MockResponse(200, b"ok")

    session = MockSession()
    resp = fetch_url("http://example.com/test", session, max_retries=1, delay=0.0)
    assert resp.status_code == 200
    assert resp.content == b"ok"
    assert len(session.calls) == 1
    assert "User-Agent" in session.calls[0][1]


def test_fetch_url_retry_and_failure(monkeypatch):
    import time
    # Speed up backoff sleep in tests
    monkeypatch.setattr(time, "sleep", lambda s: None)

    class FailingSession:
        def __init__(self):
            self.attempts = 0

        def get(self, url, headers=None, timeout=None):
            self.attempts += 1
            raise requests.exceptions.ConnectionError("Connection refused")

    session = FailingSession()
    with pytest.raises(RuntimeError, match="Falha persistente"):
        fetch_url("http://example.com/fail", session, max_retries=2, delay=0.0)
    assert session.attempts == 2
