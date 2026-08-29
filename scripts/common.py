import os
import sys
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional
import requests


def log(msg: str, level: str = "INFO"):
    now = datetime.now().strftime("%H:%M:%S")
    print(f"[{now}] [{level}] {msg}", flush=True)


def atomic_write_bytes(dest_path: Path, content: bytes):
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = dest_path.with_suffix(dest_path.suffix + ".tmp")
    with open(tmp_path, "wb") as f:
        f.write(content)
    os.replace(tmp_path, dest_path)


def atomic_write_text(dest_path: Path, content: str, encoding: str = "utf-8"):
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = dest_path.with_suffix(dest_path.suffix + ".tmp")
    with open(tmp_path, "w", encoding=encoding) as f:
        f.write(content)
    os.replace(tmp_path, dest_path)


class StateManager:
    def __init__(self, state_file: Path):
        self.state_file = state_file
        self.data: Dict[str, Any] = {
            "last_updated": None,
            "visited": {},
            "failed": {}
        }
        self.load()

    def load(self):
        if self.state_file.exists():
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
            except Exception as e:
                log(f"Aviso ao carregar {self.state_file}: {e}. Iniciando novo estado.", "WARN")

    def save(self):
        self.data["last_updated"] = datetime.now(timezone.utc).isoformat()
        atomic_write_text(self.state_file, json.dumps(self.data, indent=2, ensure_ascii=False))

    def is_completed(self, url: str) -> bool:
        item = self.data["visited"].get(url)
        return bool(item and item.get("status") == "completed")

    def mark_completed(self, url: str, local_path: str, bytes_count: int, http_code: int = 200, content_type: str = ""):
        self.data["visited"][url] = {
            "status": "completed",
            "http_code": http_code,
            "local_path": local_path,
            "bytes_count": bytes_count,
            "content_type": content_type,
            "completed_at": datetime.now(timezone.utc).isoformat()
        }
        if url in self.data["failed"]:
            del self.data["failed"][url]
        self.save()

    def mark_failed(self, url: str, error: str, attempts: int = 1):
        self.data["failed"][url] = {
            "status": "failed",
            "error": error,
            "attempts": attempts,
            "failed_at": datetime.now(timezone.utc).isoformat()
        }
        self.save()

    def get_url_info(self, url: str) -> Optional[Dict[str, Any]]:
        return self.data["visited"].get(url) or self.data["failed"].get(url)


def fetch_url(url: str, session: requests.Session, max_retries: int = 3, delay: float = 0.2) -> requests.Response:
    time.sleep(delay)
    last_err = None
    headers = {
        "User-Agent": "LabeetPreservationBot/1.0 (+http://labeet.ufpb.br)"
    }
    for attempt in range(1, max_retries + 1):
        try:
            resp = session.get(url, headers=headers, timeout=20)
            return resp
        except Exception as e:
            last_err = e
            backoff = attempt * 2
            log(f"Falha ao obter {url} (tentativa {attempt}/{max_retries}): {e}. Aguardando {backoff}s...", "WARN")
            time.sleep(backoff)
    raise RuntimeError(f"Falha persistente em {url} após {max_retries} tentativas: {last_err}")
