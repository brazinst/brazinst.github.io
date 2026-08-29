import sys
import re
import os
from pathlib import Path
from urllib.parse import urlparse, urljoin, urldefrag
from collections import deque
import requests
from bs4 import BeautifulSoup

from scripts.common import StateManager, atomic_write_bytes, atomic_write_text, fetch_url, log

BASE_URL = "http://150.165.254.38/labeet"


def is_allowed_url(base_url: str, url: str) -> bool:
    parsed_base = urlparse(base_url)
    parsed_url = urlparse(url)
    if parsed_url.scheme not in ("http", "https"):
        return False
    if parsed_url.netloc != parsed_base.netloc:
        return False
    return parsed_url.path.startswith(parsed_base.path)


def url_to_local_path(backup_root: Path, url: str) -> Path:
    parsed = urlparse(url)
    path = parsed.path.lstrip("/")
    if not path or path == "labeet" or path == "labeet/":
        return backup_root / "index.html"

    # Extrair extensão
    name = Path(path).name
    if "." in name and not name.endswith((".html", ".htm")):
        return backup_root / path
    else:
        # Se for página HTML sem extensão ou terminada com barra
        return backup_root / path / "index.html"


def rewrite_links_in_html(html_content: str, current_page_url: str, base_url: str) -> str:
    soup = BeautifulSoup(html_content, "html.parser")

    def rewrite_attr(tag, attr):
        val = tag.get(attr)
        if not val or val.startswith(("#", "javascript:", "mailto:")):
            return
        abs_url = urljoin(current_page_url, val)
        if is_allowed_url(base_url, abs_url):
            parsed_target = urlparse(abs_url)
            # Converter para caminho relativo ao diretório da página atual
            current_path = urlparse(current_page_url).path.strip("/")
            target_path = parsed_target.path.strip("/")

            # Calcular profundidade
            curr_parts = [p for p in current_path.split("/") if p]
            targ_parts = [p for p in target_path.split("/") if p]

            rel_prefix = "../" * (len(curr_parts) - 1 if curr_parts else 0)
            tag[attr] = rel_prefix + "/".join(targ_parts)

    for tag in soup.find_all(["a", "link"]):
        rewrite_attr(tag, "href")
    for tag in soup.find_all(["img", "script", "source"]):
        rewrite_attr(tag, "src")

    return str(soup)


class LabeetMirror:
    def __init__(self, backup_dir: Path, base_url: str = BASE_URL):
        self.backup_dir = backup_dir
        self.base_url = base_url
        self.state = StateManager(backup_dir / "state.json")
        self.session = requests.Session()
        self.queue = deque()

    def run(self, max_pages: int = 1000):
        log(f"Iniciando espelhamento em {self.backup_dir} a partir de {self.base_url}...")
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        # Verificar estado anterior
        completed_count = len([v for v in self.state.data["visited"].values() if v.get("status") == "completed"])
        log(f"[CHECKPOINT] {completed_count} URLs já registradas como completas no manifesto.", "INFO")

        self.queue.append(self.base_url)
        seen = set(self.queue)
        processed_count = 0

        while self.queue and processed_count < max_pages:
            url = self.queue.popleft()
            url, _ = urldefrag(url)

            local_path = url_to_local_path(self.backup_dir, url)
            if self.state.is_completed(url) and local_path.exists() and local_path.stat().st_size > 0:
                log(f"[RESUME] Pulando já baixado: {url} -> {local_path.name}", "INFO")
                # Se for HTML local, apenas descobrir novos links locais para a fila
                if local_path.suffix == ".html":
                    try:
                        content = local_path.read_text(encoding="utf-8", errors="ignore")
                        soup = BeautifulSoup(content, "html.parser")
                        for a in soup.find_all(["a", "link", "img", "script", "source"]):
                            link = a.get("href") or a.get("src")
                            if link:
                                abs_link, _ = urldefrag(urljoin(url, link))
                                if is_allowed_url(self.base_url, abs_link) and abs_link not in seen:
                                    seen.add(abs_link)
                                    self.queue.append(abs_link)
                    except Exception:
                        pass
                continue

            processed_count += 1
            log(f"[{processed_count}] Baixando: {url}...", "INFO")
            try:
                resp = fetch_url(url, self.session)
                if resp.status_code != 200:
                    self.state.mark_failed(url, f"HTTP {resp.status_code}")
                    continue

                content_type = resp.headers.get("Content-Type", "")
                if "text/html" in content_type or "application/xhtml+xml" in content_type:
                    # Parsear links para continuar crawling
                    soup = BeautifulSoup(resp.text, "html.parser")
                    for a in soup.find_all(["a", "link", "img", "script", "source"]):
                        link = a.get("href") or a.get("src")
                        if link:
                            abs_link, _ = urldefrag(urljoin(url, link))
                            if is_allowed_url(self.base_url, abs_link) and abs_link not in seen:
                                seen.add(abs_link)
                                self.queue.append(abs_link)

                    # Reescrever HTML para uso offline
                    rewritten_html = rewrite_links_in_html(resp.text, url, self.base_url)
                    atomic_write_text(local_path, rewritten_html)
                    bytes_len = len(rewritten_html.encode("utf-8"))
                else:
                    # Mídia, imagem, PDF, CSS, JS
                    atomic_write_bytes(local_path, resp.content)
                    bytes_len = len(resp.content)

                self.state.mark_completed(url, str(local_path.relative_to(self.backup_dir)), bytes_len, resp.status_code, content_type)
                log(f"    -> Salvo em {local_path} ({bytes_len / 1024:.1f} KB)", "SUCCESS")

            except Exception as e:
                log(f"Erro ao baixar {url}: {e}", "ERROR")
                self.state.mark_failed(url, str(e))

        log("Espelhamento finalizado ou fila esgotada.", "SUCCESS")


if __name__ == "__main__":
    backup_path = Path(__file__).resolve().parent.parent / "backup_full"
    mirror = LabeetMirror(backup_path)
    mirror.run()
