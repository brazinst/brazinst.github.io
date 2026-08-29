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
            if getattr(el, "name", None) in ("p", "h2", "h3", "h4", "ul", "ol"):
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
                slug = Path(inst_url.rstrip("/")).name
                md_dir = self.output_dir / "instruments" / family
                md_path = md_dir / f"{slug}.md"

                if self.state.is_completed(inst_url):
                    log(f"[{idx}/{len(instrument_links)}] [RESUME] {inst_url} já extraído.", "INFO")
                    if md_path.exists():
                        try:
                            raw_text = md_path.read_text(encoding="utf-8")
                            parts = raw_text.split("---", 2)
                            if len(parts) >= 3:
                                fm = yaml.safe_load(parts[1]) or {}
                                catalog.append({
                                    "id": fm.get("slug", slug),
                                    "title": fm.get("title", slug),
                                    "family": fm.get("family", family),
                                    "file_path": str(md_path.relative_to(self.output_dir)),
                                    "media_count": len(fm.get("images", [])),
                                    "audio_video_count": len(fm.get("audio_video_links", []))
                                })
                        except Exception as e:
                            log(f"Erro ao ler verbete existente {md_path}: {e}", "WARN")
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

                md_dir.mkdir(parents=True, exist_ok=True)
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
