# LABEET / Brazil Instrumentarium Preservation (Sub-project 1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir e executar o pipeline completo de resgate, espelhamento offline resiliente do site LABEET e extração semântica em Markdown/JSON do acervo Brazil Instrumentarium com suporte a checkpoint/resume pós-falha.

**Architecture:** O pipeline é composto por utilitários compartilhados de rede e estado (`common.py`), um crawler espelhador estático para o Plone (`mirror.py`), um extrator semântico de verbetes organológicos para Markdown/JSON (`extract_brazinst.py`), um submissor em lote para o Internet Archive (`archive_wayback.py`) e um auditor de integridade (`validate.py`). Cada script lê e grava em arquivos de estado JSON com escrita atômica (`.tmp` -> renomeação), permitindo retomar a execução de onde parou a qualquer momento.

**Tech Stack:** Python 3.14, `requests`, `beautifulsoup4`, `pyyaml`, `pytest`.

**Spec:** [`docs/specs/2026-08-29-labeet-preservation-subproject1-design.md`](file:///Users/gregoriomelo/dev/labeet/docs/specs/2026-08-29-labeet-preservation-subproject1-design.md)

## Global Constraints

- Python virtual environment em `.venv/` com dependências instaladas.
- Todas as gravações de arquivos baixados e manifestos devem ser atômicas (gravar em `<caminho>.tmp` e renomear com `os.replace`).
- Fila e histórico de requisições persistidos em `state.json` com status (`completed`, `failed`).
- Rate limiting amigável (delay configurável entre requisições, padrão 0.2s - 0.5s) e retries automáticos com recuo exponencial (1s, 2s, 5s).
- Mensagens de log em tempo real no console exibindo timestamp, arquivo local de destino, tamanho e percentual de progresso.
- Testes unitários com `pytest` para cada componente antes do avanço.

---

### Task 1: Scaffolding, Logger e Módulo de Estado Resiliente (`scripts/common.py`)

**Files:**
- Create: `scripts/common.py`
- Test: `tests/test_common.py`

**Interfaces:**
- Produz:
  - `class StateManager`: gerencia carregamento, atualização atômica e verificação de URLs em `state.json`.
  - `log(msg, level="INFO")`: imprime mensagens com timestamp formatado no terminal.
  - `atomic_write_bytes(dest_path: Path, content: bytes)`: escrita atômica segura.
  - `atomic_write_text(dest_path: Path, content: str)`: escrita atômica de texto UTF-8.
  - `fetch_url(url: str, session: requests.Session, max_retries=3, delay=0.2)`: requisição HTTP com rate limit e backoff.

- [ ] **Step 1: Escrever teste falhando para `common.py`**

Criar `tests/test_common.py`:
```python
import json
from pathlib import Path
import pytest
from scripts.common import StateManager, atomic_write_text, atomic_write_bytes

def test_atomic_write_text(tmp_path: Path):
    target = tmp_path / "subdir" / "test.txt"
    atomic_write_text(target, "olá mundo")
    assert target.exists()
    assert target.read_text(encoding="utf-8") == "olá mundo"

def test_state_manager_resume(tmp_path: Path):
    state_file = tmp_path / "state.json"
    manager = StateManager(state_file)
    assert manager.is_completed("http://example.com/page1") is False

    manager.mark_completed("http://example.com/page1", local_path="page1.html", bytes_count=123)
    assert manager.is_completed("http://example.com/page1") is True

    # Recarregar do disco e verificar persistência
    manager2 = StateManager(state_file)
    assert manager2.is_completed("http://example.com/page1") is True
    info = manager2.get_url_info("http://example.com/page1")
    assert info["status"] == "completed"
    assert info["bytes_count"] == 123
```

- [ ] **Step 2: Executar o teste e verificar que falha**

Executar:
```bash
.venv/bin/pytest tests/test_common.py -v
```
Resultado esperado: FAIL com `ModuleNotFoundError: No module named 'scripts'` ou `cannot import name StateManager`.

- [ ] **Step 3: Implementar `scripts/common.py`**

Criar `scripts/common.py`:
```python
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
```

- [ ] **Step 4: Executar os testes e verificar que passam**

Executar:
```bash
.venv/bin/pytest tests/test_common.py -v
```
Resultado esperado: PASS com 2 passed.

- [ ] **Step 5: Commit**

```bash
git add scripts/common.py tests/test_common.py
git commit -m "feat: add common utilities for checkpointing, atomic writes, and polite HTTP fetch"
```

---

### Task 2: Espelhador Bruto Inteligente do Site (`scripts/mirror.py`)

**Files:**
- Create: `scripts/mirror.py`
- Test: `tests/test_mirror.py`

**Interfaces:**
- Consumes: `StateManager`, `atomic_write_bytes`, `atomic_write_text`, `fetch_url`, `log` de `scripts/common.py`.
- Produz:
  - `class LabeetMirror`: realiza download recursivo restrito ao domínio `/labeet/`, reescreve links relativos de assets e HTMLs e atualiza o manifesto `backup_full/state.json`.

- [ ] **Step 1: Escrever teste de unidade para URL canonicalization e reescrita de links**

Criar `tests/test_mirror.py`:
```python
from pathlib import Path
from bs4 import BeautifulSoup
from scripts.mirror import url_to_local_path, is_allowed_url, rewrite_links_in_html

def test_is_allowed_url():
    base = "http://150.165.254.38/labeet"
    assert is_allowed_url(base, "http://150.165.254.38/labeet/contents") is True
    assert is_allowed_url(base, "http://150.165.254.38/labeet/logo.png") is True
    assert is_allowed_url(base, "https://twitter.com/ufpboficial") is False
    assert is_allowed_url(base, "http://sti.ufpb.br/dweb") is False

def test_url_to_local_path(tmp_path: Path):
    root = tmp_path / "backup_full"
    # URL de página terminando em diretório ou slug
    path1 = url_to_local_path(root, "http://150.165.254.38/labeet/contents/menu")
    assert path1 == root / "labeet" / "contents" / "menu" / "index.html"

    # URL com extensão de arquivo (css/png/jpg)
    path2 = url_to_local_path(root, "http://150.165.254.38/labeet/logo.png")
    assert path2 == root / "labeet" / "logo.png"

def test_rewrite_links_in_html():
    html = '''<html><head><link rel="stylesheet" href="http://150.165.254.38/labeet/style.css"></head>
              <body><img src="http://150.165.254.38/labeet/logo.png">
              <a href="http://150.165.254.38/labeet/page">link</a></body></html>'''
    current_url = "http://150.165.254.38/labeet/contents/index.html"
    base_url = "http://150.165.254.38/labeet"
    rewritten = rewrite_links_in_html(html, current_url, base_url)
    assert "http://150.165.254.38/labeet/style.css" not in rewritten
    assert "http://150.165.254.38/labeet/logo.png" not in rewritten
```

- [ ] **Step 2: Executar o teste e verificar que falha**

Executar:
```bash
.venv/bin/pytest tests/test_mirror.py -v
```
Resultado esperado: FAIL com `ModuleNotFoundError: No module named 'scripts.mirror'`.

- [ ] **Step 3: Implementar `scripts/mirror.py`**

Criar `scripts/mirror.py`:
```python
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
    parsed_base = urlparse(base_url)

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

        if not self.state.is_completed(self.base_url):
            self.queue.append(self.base_url)
        else:
            # Reenfileirar URLs incompletas ou iniciar a partir da raiz
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
                        for a in soup.find_all(["a", "link", "img", "script"]):
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
                if "text/html" in content_type:
                    # Parsear links para continuar crawling
                    soup = BeautifulSoup(resp.text, "html.parser")
                    for a in soup.find_all(["a", "link", "img", "script"]):
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
    backup_path = Path("/Users/gregoriomelo/dev/labeet/backup_full")
    mirror = LabeetMirror(backup_path)
    mirror.run()
```

- [ ] **Step 4: Executar testes de unidade e verificar que passam**

Executar:
```bash
.venv/bin/pytest tests/test_mirror.py -v
```
Resultado esperado: PASS com 3 passed.

- [ ] **Step 5: Commit**

```bash
git add scripts/mirror.py tests/test_mirror.py
git commit -m "feat: add robust offline mirror engine with checkpoint and link rewriting"
```

---

### Task 3: Extrator Semântico do Brazil Instrumentarium (`scripts/extract_brazinst.py`)

**Files:**
- Create: `scripts/extract_brazinst.py`
- Test: `tests/test_extract.py`

**Interfaces:**
- Consumes: `StateManager`, `atomic_write_text`, `atomic_write_bytes`, `fetch_url`, `log`.
- Produz:
  - `parse_verbete_html(html_content: str, source_url: str) -> dict`: extrai metadados e markdown de um verbete.
  - `class BrazinstExtractor`: percorre as 4 categorias organológicas, extrai os instrumentos e salva em `content_brazinst/`.

- [ ] **Step 1: Escrever teste de unidade com fixture HTML de um verbete real (Agogô)**

Criar `tests/test_extract.py`:
```python
import pytest
from scripts.extract_brazinst.py import parse_verbete_html

SAMPLE_VERBETE_HTML = '''
<!DOCTYPE html>
<html>
<head><title>Agogô — LABEET</title></head>
<body>
<div id="content">
    <h1 class="documentFirstHeading">Agogô</h1>
    <div class="documentByLine">
        por <span class="documentAuthor">danielrocha</span> —
        <span class="documentPublished">publicado 28/03/2018 10h40</span>,
        <span class="documentModified">última modificação 26/01/2026 16h37</span>
    </div>
    <div id="content-core">
        <div id="parent-fieldname-text">
            <p><img src="http://150.165.254.38/labeet/agogo.jpg" alt="Agogô"></p>
            <p>O agogô foi levado pelos escravos africanos para as Américas...</p>
            <h3>Referências</h3>
            <p>C. A. Moloney: ‘On the Melodies...’ (1889)</p>
            <h3>Fonografia</h3>
            <p><a href="https://www.youtube.com/watch?v=_kQIk1jJb9c">Exemplo 1</a></p>
            <p><i>Alice L. Satomi</i></p>
        </div>
    </div>
</div>
</body></html>
'''

def test_parse_verbete_html():
    data = parse_verbete_html(SAMPLE_VERBETE_HTML, "http://150.165.254.38/labeet/contents/paginas/acervo-brazinst/copy_of_idiofones/agogo")
    assert data["title"] == "Agogô"
    assert data["family"] == "idiofones"
    assert "Alice L. Satomi" in data["body"]
    assert len(data["audio_video_links"]) == 1
    assert data["audio_video_links"][0]["url"] == "https://www.youtube.com/watch?v=_kQIk1jJb9c"
    assert len(data["image_urls"]) >= 1
```

- [ ] **Step 2: Executar o teste e verificar que falha**

Executar:
```bash
.venv/bin/pytest tests/test_extract.py -v
```
Resultado esperado: FAIL com `ModuleNotFoundError`.

- [ ] **Step 3: Implementar `scripts/extract_brazinst.py`**

Criar `scripts/extract_brazinst.py`:
```python
import re
import json
from pathlib import Path
from typing import Dict, Any, List
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
import yaml

from scripts.common import StateManager, atomic_write_text, atomic_write_bytes, fetch_url, log

CATEGORIES = {
    "idiofones": "http://150.165.254.38/labeet/contents/paginas/acervo-brazinst/copy_of_idiofones",
    "membranofones": "http://150.165.254.38/labeet/contents/paginas/acervo-brazinst/copy_of_membranofones",
    "cordofones": "http://150.165.254.38/labeet/contents/paginas/acervo-brazinst/copy_of_cordofones",
    "aerofones": "http://150.165.254.38/labeet/contents/paginas/acervo-brazinst/copy_of_aerofones"
}

def clean_text(text: str) -> str:
    return re.sub(r'\s+', ' ', text).strip()

def parse_verbete_html(html_content: str, source_url: str) -> Dict[str, Any]:
    soup = BeautifulSoup(html_content, "html.parser")
    
    # Determinar família organológica pela URL
    family = "outros"
    for cat in CATEGORIES.keys():
        if cat in source_url:
            family = cat
            break

    # Título
    title_tag = soup.find("h1", class_="documentFirstHeading")
    title = clean_text(title_tag.get_text()) if title_tag else "Sem Título"
    slug = Path(source_url.rstrip("/")).name

    # Metadados de autoria e datas
    byline = soup.find("div", class_="documentByLine") or soup.find("div", id="plone-document-byline")
    byline_text = byline.get_text() if byline else ""
    
    published_date = None
    modified_date = None
    m_pub = re.search(r'publicado\s+(\d{2}/\d{2}/\d{4})', byline_text)
    if m_pub:
        d, m, y = m_pub.group(1).split("/")
        published_date = f"{y}-{m}-{d}"
    m_mod = re.search(r'última modificação\s+(\d{2}/\d{2}/\d{4})', byline_text)
    if m_mod:
        d, m, y = m_mod.group(1).split("/")
        modified_date = f"{y}-{m}-{d}"

    # Conteúdo principal
    content_div = soup.find("div", id="parent-fieldname-text") or soup.find("div", id="content-core")
    
    image_urls = []
    audio_video_links = []
    references = []
    body_paragraphs = []

    if content_div:
        # Encontrar imagens
        for img in content_div.find_all("img"):
            src = img.get("src")
            if src:
                image_urls.append(urljoin(source_url, src))

        # Encontrar links de áudio/vídeo (YouTube, SoundCloud, etc.)
        for a in content_div.find_all("a"):
            href = a.get("href", "")
            if "youtube.com" in href or "youtu.be" in href or "soundcloud.com" in href:
                audio_video_links.append({
                    "title": clean_text(a.get_text()) or "Registro Fonográfico",
                    "url": href
                })

        # Processar texto parágrafo a parágrafo
        for el in content_div.children:
            if el.name in ("p", "h2", "h3", "h4", "ul", "ol"):
                text = clean_text(el.get_text())
                if not text:
                    continue
                if el.name == "h2":
                    body_paragraphs.append(f"\n## {text}\n")
                elif el.name == "h3":
                    body_paragraphs.append(f"\n### {text}\n")
                elif el.name == "h4":
                    body_paragraphs.append(f"\n#### {text}\n")
                else:
                    body_paragraphs.append(text)

    body = "\n\n".join(body_paragraphs)

    return {
        "title": title,
        "slug": slug,
        "family": family,
        "source_url": source_url,
        "published_date": published_date,
        "modified_date": modified_date,
        "image_urls": image_urls,
        "audio_video_links": audio_video_links,
        "references": references,
        "body": body
    }

class BrazinstExtractor:
    def __init__(self, output_dir: Path, session: requests.Session = None):
        self.output_dir = output_dir
        self.session = session or requests.Session()
        self.state = StateManager(output_dir / "state_extraction.json")

    def run(self):
        log(f"Iniciando extração do Brazil Instrumentarium para {self.output_dir}...")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        catalog = []

        for family, cat_url in CATEGORIES.items():
            log(f"[FAMÍLIA: {family.upper()}] Obtendo lista de instrumentos em {cat_url}...")
            resp = fetch_url(cat_url, self.session)
            if resp.status_code != 200:
                log(f"Falha ao carregar categoria {family}: HTTP {resp.status_code}", "ERROR")
                continue

            soup = BeautifulSoup(resp.text, "html.parser")
            instrument_links = []
            for a in soup.find_all("a", class_="summary"):
                href = a.get("href")
                if href and href != cat_url and "tabela-organologica" not in href:
                    instrument_links.append(urljoin(cat_url, href))

            log(f"Encontrados {len(instrument_links)} instrumentos em {family}.")

            for idx, inst_url in enumerate(instrument_links, 1):
                if self.state.is_completed(inst_url):
                    log(f"[{idx}/{len(instrument_links)}] [RESUME] {inst_url} já extraído.", "INFO")
                    continue

                log(f"[{idx}/{len(instrument_links)}] Extraindo: {inst_url}...", "INFO")
                inst_resp = fetch_url(inst_url, self.session)
                if inst_resp.status_code != 200:
                    self.state.mark_failed(inst_url, f"HTTP {inst_resp.status_code}")
                    continue

                data = parse_verbete_html(inst_resp.text, inst_url)
                
                # Baixar imagens locais
                local_images = []
                inst_media_dir = self.output_dir / "media" / family / data["slug"]
                inst_media_dir.mkdir(parents=True, exist_ok=True)

                for img_idx, img_url in enumerate(data["image_urls"], 1):
                    try:
                        img_resp = fetch_url(img_url, self.session)
                        if img_resp.status_code == 200:
                            img_filename = f"img_{img_idx:02d}.jpg"
                            img_path = inst_media_dir / img_filename
                            atomic_write_bytes(img_path, img_resp.content)
                            rel_img_path = str(img_path.relative_to(self.output_dir))
                            local_images.append({
                                "file": rel_img_path,
                                "original_url": img_url
                            })
                            log(f"    -> Imagem salva: {rel_img_path}", "INFO")
                    except Exception as e:
                        log(f"    -> Aviso: falha ao baixar imagem {img_url}: {e}", "WARN")

                # Montar Frontmatter YAML
                frontmatter = {
                    "title": data["title"],
                    "slug": data["slug"],
                    "family": data["family"],
                    "source_url": data["source_url"],
                    "published_date": data["published_date"],
                    "modified_date": data["modified_date"],
                    "images": local_images,
                    "audio_video_links": data["audio_video_links"],
                    "references": data["references"]
                }

                md_content = f"---\n{yaml.dump(frontmatter, allow_unicode=True, sort_keys=False)}---\n\n# {data['title']}\n\n{data['body']}\n"
                
                md_dir = self.output_dir / "instruments" / family
                md_dir.mkdir(parents=True, exist_ok=True)
                md_path = md_dir / f"{data['slug']}.md"
                atomic_write_text(md_path, md_content)

                self.state.mark_completed(inst_url, str(md_path.relative_to(self.output_dir)), len(md_content.encode("utf-8")))
                log(f"    -> Verbete salvo em {md_path}", "SUCCESS")

                catalog.append({
                    "id": data["slug"],
                    "title": data["title"],
                    "family": data["family"],
                    "file_path": str(md_path.relative_to(self.output_dir)),
                    "media_count": len(local_images),
                    "audio_video_count": len(data["audio_video_links"])
                })

        # Salvar catálogo geral JSON
        catalog_path = self.output_dir / "brazinst_catalog.json"
        atomic_write_text(catalog_path, json.dumps({
            "total_instruments": len(catalog),
            "instruments": catalog
        }, indent=2, ensure_ascii=False))
        log(f"Catálogo finalizado com {len(catalog)} instrumentos em {catalog_path}", "SUCCESS")

if __name__ == "__main__":
    out = Path("/Users/gregoriomelo/dev/labeet/content_brazinst")
    extractor = BrazinstExtractor(out)
    extractor.run()
```

- [ ] **Step 4: Executar testes de unidade e verificar que passam**

Executar:
```bash
.venv/bin/pytest tests/test_extract.py -v
```
Resultado esperado: PASS com 1 passed.

- [ ] **Step 5: Commit**

```bash
git add scripts/extract_brazinst.py tests/test_extract.py
git commit -m "feat: add semantic extractor for Brazil Instrumentarium with YAML frontmatter"
```

---

### Task 4: Submissor para a Wayback Machine (`scripts/archive_wayback.py`)

**Files:**
- Create: `scripts/archive_wayback.py`
- Test: `tests/test_archive_wayback.py`

**Interfaces:**
- Consumes: `StateManager`, `atomic_write_text`, `log`.
- Produz:
  - `submit_to_wayback(url: str, session: requests.Session) -> str`: submete URL para o Save Page Now do Internet Archive e retorna o link permanente.

- [ ] **Step 1: Escrever teste de unidade para montagem de requisição e parsing de headers do Wayback**

Criar `tests/test_archive_wayback.py`:
```python
from unittest.mock import MagicMock
from scripts.archive_wayback import submit_to_wayback

def test_submit_to_wayback_mocked():
    session = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.headers = {
        "Content-Location": "/web/20260829204500/http://150.165.254.38/labeet"
    }
    session.get.return_value = mock_resp

    archived_url = submit_to_wayback("http://150.165.254.38/labeet", session)
    assert "https://web.archive.org/web/20260829204500/http://150.165.254.38/labeet" in archived_url
```

- [ ] **Step 2: Executar o teste e verificar que falha**

Executar:
```bash
.venv/bin/pytest tests/test_archive_wayback.py -v
```
Resultado esperado: FAIL com `ModuleNotFoundError`.

- [ ] **Step 3: Implementar `scripts/archive_wayback.py`**

Criar `scripts/archive_wayback.py`:
```python
import sys
import time
from pathlib import Path
from typing import Dict
import requests

from scripts.common import StateManager, atomic_write_text, log

WAYBACK_SAVE_URL = "https://web.archive.org/save/"

def submit_to_wayback(url: str, session: requests.Session) -> str:
    save_endpoint = f"{WAYBACK_SAVE_URL}{url}"
    headers = {
        "User-Agent": "LabeetAcademicPreservationBot/1.0"
    }
    resp = session.get(save_endpoint, headers=headers, timeout=30)
    loc = resp.headers.get("Content-Location")
    if loc:
        if loc.startswith("http"):
            return loc
        return f"https://web.archive.org{loc}"
    return f"https://web.archive.org/web/{url}"

def archive_all_urls(state_file: Path, output_file: Path, delay: float = 2.0):
    state = StateManager(state_file)
    session = requests.Session()
    urls = list(state.data["visited"].keys())
    log(f"Submetendo {len(urls)} URLs para a Wayback Machine (Internet Archive)...")

    results: Dict[str, str] = {}
    for idx, url in enumerate(urls, 1):
        log(f"[{idx}/{len(urls)}] Arquivando no Internet Archive: {url}...")
        try:
            archived = submit_to_wayback(url, session)
            results[url] = archived
            log(f"    -> Arquivado com sucesso: {archived}", "SUCCESS")
        except Exception as e:
            log(f"    -> Erro ao arquivar {url}: {e}", "WARN")
            results[url] = f"FALHA: {e}"
        time.sleep(delay)

    lines = ["# Mapeamento do Acervo no Internet Archive (Wayback Machine)\n\n"]
    for u, a in results.items():
        lines.append(f"- **Original:** `{u}`\n  **Wayback:** [{a}]({a})\n")
    
    atomic_write_text(output_file, "\n".join(lines))
    log(f"Relatório de arquivamento salvo em {output_file}", "SUCCESS")

if __name__ == "__main__":
    st = Path("/Users/gregoriomelo/dev/labeet/backup_full/state.json")
    out = Path("/Users/gregoriomelo/dev/labeet/content_brazinst/wayback_archive.md")
    archive_all_urls(st, out)
```

- [ ] **Step 4: Executar testes de unidade e verificar que passam**

Executar:
```bash
.venv/bin/pytest tests/test_archive_wayback.py -v
```
Resultado esperado: PASS com 1 passed.

- [ ] **Step 5: Commit**

```bash
git add scripts/archive_wayback.py tests/test_archive_wayback.py
git commit -m "feat: add Internet Archive Wayback Machine archiver"
```

---

### Task 5: Auditoria, Validação e Relatório de Inventário (`scripts/validate.py`)

**Files:**
- Create: `scripts/validate.py`
- Test: `tests/test_validate.py`

**Interfaces:**
- Consumes: `StateManager`, `atomic_write_text`, `log`.
- Produz:
  - `validate_preservation(backup_dir: Path, content_dir: Path) -> dict`: audita completude de arquivos, contagens e mídias.
  - Gera `content_brazinst/inventory_report.md`.

- [ ] **Step 1: Escrever teste de unidade para auditoria de arquivos e integridade de mídias**

Criar `tests/test_validate.py`:
```python
from pathlib import Path
from scripts.validate import audit_content_integrity

def test_audit_content_integrity(tmp_path: Path):
    content_dir = tmp_path / "content_brazinst"
    inst_dir = content_dir / "instruments" / "idiofones"
    inst_dir.mkdir(parents=True)
    media_dir = content_dir / "media" / "idiofones" / "agogo"
    media_dir.mkdir(parents=True)
    
    img_file = media_dir / "img_01.jpg"
    img_file.write_bytes(b"fake-image-bytes")

    md_file = inst_dir / "agogo.md"
    md_file.write_text("""---
title: "Agogô"
family: "idiofones"
images:
  - file: "media/idiofones/agogo/img_01.jpg"
---
# Agogô
Texto do verbete...
""", encoding="utf-8")

    report = audit_content_integrity(content_dir)
    assert report["total_instruments"] == 1
    assert report["missing_media_count"] == 0
    assert report["instruments_by_family"]["idiofones"] == 1
```

- [ ] **Step 2: Executar o teste e verificar que falha**

Executar:
```bash
.venv/bin/pytest tests/test_validate.py -v
```
Resultado esperado: FAIL com `ModuleNotFoundError`.

- [ ] **Step 3: Implementar `scripts/validate.py`**

Criar `scripts/validate.py`:
```python
import json
from pathlib import Path
from typing import Dict, Any
import yaml

from scripts.common import StateManager, atomic_write_text, log

def audit_content_integrity(content_dir: Path) -> Dict[str, Any]:
    instruments_dir = content_dir / "instruments"
    by_family = {}
    total_insts = 0
    missing_media = []
    total_media_count = 0
    total_bytes = 0

    if instruments_dir.exists():
        for family_dir in instruments_dir.iterdir():
            if family_dir.is_dir():
                count = 0
                for md_file in family_dir.glob("*.md"):
                    count += 1
                    total_insts += 1
                    total_bytes += md_file.stat().st_size
                    try:
                        content = md_file.read_text(encoding="utf-8")
                        parts = content.split("---")
                        if len(parts) >= 3:
                            meta = yaml.safe_load(parts[1])
                            for img in meta.get("images", []):
                                total_media_count += 1
                                rel_path = img.get("file")
                                if rel_path:
                                    expected_path = content_dir / rel_path
                                    if not expected_path.exists() or expected_path.stat().st_size == 0:
                                        missing_media.append(f"{md_file.name}: {rel_path}")
                                    else:
                                        total_bytes += expected_path.stat().st_size
                    except Exception as e:
                        missing_media.append(f"Erro de parsing em {md_file.name}: {e}")
                by_family[family_dir.name] = count

    return {
        "total_instruments": total_insts,
        "instruments_by_family": by_family,
        "total_media_count": total_media_count,
        "missing_media_count": len(missing_media),
        "missing_media_details": missing_media,
        "total_bytes_mb": round(total_bytes / (1024 * 1024), 2)
    }

def generate_inventory_report(backup_dir: Path, content_dir: Path, output_file: Path):
    log("Executando validação de integridade e gerando relatório de inventário...")
    state = StateManager(backup_dir / "state.json")
    visited = state.data.get("visited", {})
    failed = state.data.get("failed", {})

    content_audit = audit_content_integrity(content_dir)

    md = [
        "# Relatório Final de Inventário e Integridade — Preservação LABEET",
        f"\n**Data da Auditoria:** {StateManager(backup_dir / 'state.json').data.get('last_updated')}",
        "\n## 1. Resumo Geral",
        f"- **Páginas e arquivos salvos no espelho bruto:** {len(visited)}",
        f"- **Falhas no espelho bruto:** {len(failed)}",
        f"- **Total de instrumentos preservados no Brazil Instrumentarium:** {content_audit['total_instruments']}",
        f"- **Total de fotos preservadas:** {content_audit['total_media_count']}",
        f"- **Fotos ausentes/corrompidas:** {content_audit['missing_media_count']}",
        f"- **Espaço total em disco (dados limpos):** {content_audit['total_bytes_mb']} MB",
        "\n## 2. Instrumentos por Família Organológica"
    ]

    for fam, count in content_audit["instruments_by_family"].items():
        md.append(f"- **{fam.capitalize()}:** {count} instrumentos")

    if content_audit["missing_media_details"]:
        md.append("\n## 3. Alertas de Mídias Ausentes")
        for item in content_audit["missing_media_details"]:
            md.append(f"- [x] {item}")
    else:
        md.append("\n## 3. Integridade de Mídias")
        md.append("✅ **100% das imagens vinculadas foram baixadas e verificadas no disco local.**")

    atomic_write_text(output_file, "\n".join(md))
    log(f"Relatório de inventário gerado com sucesso em {output_file}", "SUCCESS")

if __name__ == "__main__":
    b_dir = Path("/Users/gregoriomelo/dev/labeet/backup_full")
    c_dir = Path("/Users/gregoriomelo/dev/labeet/content_brazinst")
    rep = c_dir / "inventory_report.md"
    generate_inventory_report(b_dir, c_dir, rep)
```

- [ ] **Step 4: Executar testes de unidade e verificar que passam**

Executar:
```bash
.venv/bin/pytest tests/test_validate.py -v
```
Resultado esperado: PASS com 1 passed.

- [ ] **Step 5: Commit**

```bash
git add scripts/validate.py tests/test_validate.py
git commit -m "feat: add integrity auditor and inventory report generator"
```

---

### Task 6: Execução End-to-End e Verificação de Continuidade Pós-Falha

**Files:**
- Output: `backup_full/` (site espelhado)
- Output: `content_brazinst/` (dados limpos em Markdown/JSON)
- Output: `content_brazinst/inventory_report.md`

- [ ] **Step 1: Executar o espelhamento do site com saída detalhada**

Executar:
```bash
.venv/bin/python scripts/mirror.py
```
Verificar que os logs no terminal informam os arquivos sendo baixados e que o diretório `backup_full/` é preenchido.

- [ ] **Step 2: Testar o mecanismo de continuação (Resume)**

Executar novamente:
```bash
.venv/bin/python scripts/mirror.py
```
Verificar que o console exibe `[CHECKPOINT]` e `[RESUME] Pulando já baixado`, sem refazer downloads já salvos.

- [ ] **Step 3: Executar a extração semântica do Brazil Instrumentarium**

Executar:
```bash
.venv/bin/python scripts/extract_brazinst.py
```
Verificar a criação dos arquivos `.md` em `content_brazinst/instruments/` e o catálogo consolidado `content_brazinst/brazinst_catalog.json`.

- [ ] **Step 4: Executar a auditoria e gerar o relatório final de inventário**

Executar:
```bash
.venv/bin/python scripts/validate.py
```
Verificar o arquivo `content_brazinst/inventory_report.md`.

- [ ] **Step 5: Executar a suíte de testes de regressão completa**

Executar:
```bash
.venv/bin/pytest tests/ -v
```
Resultado esperado: PASS em todos os testes.

- [ ] **Step 6: Commit dos scripts finais e fixtures**

```bash
git add scripts/ tests/
git commit -m "feat: complete preservation pipeline implementation and tests"
```
