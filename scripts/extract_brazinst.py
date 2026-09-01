import sys
import re
import json
import shutil
import urllib.parse
from pathlib import Path
from typing import Dict, Any, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

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

CATEGORY_DIR_MAP = {
    "copy_of_idiofones": "idiofones",
    "copy_of_membranofones": "membranofones",
    "copy_of_cordofones": "cordofones",
    "copy_of_aerofones": "aerofones"
}

SLUG_OVERRIDES = {
    # Aerofones
    ("aerofones", "Afofie"): "afofie",
    ("aerofones", "Baixao"): "baixao",
    ("aerofones", "Berrante"): "berrante",
    ("aerofones", "Bore"): "bore",
    ("aerofones", "Botuto"): "botuto",
    ("aerofones", "Buzio"): "buzio",
    ("aerofones", "Cangoeira"): "cangoeira",
    ("aerofones", "Charamela"): "charamela",
    ("aerofones", "Trombeta"): "trombeta",
    ("aerofones", "copy_of_dasmae"): "matapu",
    ("aerofones", "copy_of_adjulona-s-m"): "pifano",
    ("aerofones", "copy_of_tarawi"): "pireu-xixi",
    ("aerofones", "copy_of_aidje"): "sacabuxa",
    ("aerofones", "copy_of_takwara"): "talapi",
    ("aerofones", "copy2_of_takwara"): "tule",
    ("aerofones", "copy5_of_araue"): "upawa",
    
    # Cordofones
    ("cordofones", "Berimbau-de-boca"): "berimbau-de-boca",
    ("cordofones", "Berimbau-de-lata"): "berimbau-de-lata",
    ("cordofones", "copy2_of_gualambo"): "bandolim",
    ("cordofones", "copy7_of_Viola de 10 cordas"): "cavaquinho",
    ("cordofones", "copy7_of_Viola%20de%2010%20cordas"): "cavaquinho",
    ("cordofones", "Marimbau Armorial"): "marimbau-armorial",
    ("cordofones", "Marimbau%20Armorial"): "marimbau-armorial",
    ("cordofones", "copy_of_Viola de 10 cordas"): "mbaraka",
    ("cordofones", "copy_of_Viola%20de%2010%20cordas"): "mbaraka",
    ("cordofones", "copy3_of_Viola de 10 cordas"): "rave",
    ("cordofones", "copy3_of_Viola%20de%2010%20cordas"): "rave",
    ("cordofones", "copy_of_gualambo"): "viola-angrense",
    ("cordofones", "copy8_of_Viola de 10 cordas"): "viola-de-buriti",
    ("cordofones", "copy8_of_Viola%20de%2010%20cordas"): "viola-de-buriti",
    ("cordofones", "copy5_of_Viola de 10 cordas"): "viola-de-cocho",
    ("cordofones", "copy5_of_Viola%20de%2010%20cordas"): "viola-de-cocho",
    ("cordofones", "Viola de 10 cordas"): "viola-de-dez-cordas",
    ("cordofones", "Viola%20de%2010%20cordas"): "viola-de-dez-cordas",
    ("cordofones", "copy6_of_Viola de 10 cordas"): "viola-dinamica",
    ("cordofones", "copy6_of_Viola%20de%2010%20cordas"): "viola-dinamica",
    ("cordofones", "copy4_of_Viola de 10 cordas"): "viola-machete",
    ("cordofones", "copy4_of_Viola%20de%2010%20cordas"): "viola-machete",
    ("cordofones", "copy9_of_Viola de 10 cordas"): "violao-de-sete-cordas",
    ("cordofones", "copy9_of_Viola%20de%2010%20cordas"): "violao-de-sete-cordas",
    
    # Idiofones
    ("idiofones", "copy_of_reco-reco"): "alemao",
    ("idiofones", "teste 478"): "bastoes-de-maculele",
    ("idiofones", "teste%20478"): "bastoes-de-maculele",
    ("idiofones", "copy2_of_araue"): "caixa-de-fosforo",
    ("idiofones", "copy_of_carutana"): "cajon",
    ("idiofones", "copy_of_chocalho_fieira"): "chocalho-fieira",
    ("idiofones", "copy5_of_araue"): "enxada",
    ("idiofones", "copy_of_araue"): "frigideira",
    ("idiofones", "guarara"): "guarara-idiofone",
    ("idiofones", "copy_of_maraca"): "maraca-de-lanca",
    ("idiofones", "copy_of_zuza"): "matraca-de-procissao",
    ("idiofones", "copy3_of_ytamyri"): "numiatoto",
    ("idiofones", "copy_of_paraca"): "pau-de-chuva",
    ("idiofones", "copy_of_caxixi"): "reco-gogo",
    ("idiofones", "copy_of_sansa"): "serrote-musical",
    ("idiofones", "copy_of_trocano"): "tamanco-do-trupe",
    ("idiofones", "tamaraca"): "tamaraca-idiofone",
    ("idiofones", "copy_of_triangulo"): "tambor-de-casco-de-tartaruga",
    ("idiofones", "copy2_of_triangulo"): "tubo-estampado",
    
    # Membranofones
    ("membranofones", "copy2_of_angua"): "andua",
    ("membranofones", "copy_of_tambor"): "atabaque-de-mina",
    ("membranofones", "copy_of_caixa"): "caixa-de-marabaixo",
    ("membranofones", "copy2_of_caixa"): "caixa-quadrada",
    ("membranofones", "guarara"): "guarara-membranofone",
    ("membranofones", "copy_of_pandeiro"): "mussum",
    ("membranofones", "copy3_of_caixa"): "surdo",
    ("membranofones", "tamaraca"): "tamaraca-membranofone",
    ("membranofones", "copy2_of_tambor"): "tambor-abata",
}


def clean_text(text: str) -> str:
    return re.sub(r'\s+', ' ', text).strip()


def parse_date_str(text: str) -> Optional[str]:
    m = re.search(r'(\d{2})/(\d{2})/(\d{4})', text)
    if m:
        d, mth, y = m.group(1), m.group(2), m.group(3)
        return f"{y}-{mth}-{d}"
    return None


def extract_mimo_code(text: str) -> Optional[str]:
    m = re.search(r'\b(?:MIMO|classifica(?:ção|-se)?(?:\s+como)?)\s*[:\s]?\s*([1-4](?:\.\d+)+|\d{3}(?:\.\d+)+)', text, re.IGNORECASE)
    if m:
        return m.group(1)
    # Check for standalone Sachs/Hornbostel code
    m2 = re.search(r'\b([1-4]\.\d+(?:\.\d+)+)\b', text)
    if m2:
        return m2.group(1)
    return None


def parse_verbete_html(html_content: str, source_url: str, local_dir: Optional[Path] = None) -> Dict[str, Any]:
    soup = BeautifulSoup(html_content, "html.parser")

    # Determinar família organológica pela URL ou local_dir
    family = "outros"
    for cat in CATEGORIES.keys():
        if cat in source_url:
            family = cat
            break
    if family == "outros" and local_dir:
        for k, v in CATEGORY_DIR_MAP.items():
            if k in str(local_dir):
                family = v
                break

    # Título
    title_tag = soup.find("h1", class_="documentFirstHeading")
    title = clean_text(title_tag.get_text()) if title_tag else "Sem Título"

    # Subtítulo
    subtitle_tag = soup.find("h2", class_="nitfSubtitle")
    subtitle = clean_text(subtitle_tag.get_text()) if subtitle_tag else None
    if not subtitle:
        subtitle = None

    # Descrição / Resumo
    desc_tag = soup.find("div", class_="documentDescription") or soup.find("p", class_="documentDescription")
    description = clean_text(desc_tag.get_text()) if desc_tag else None
    if not description:
        description = None

    # Slug
    raw_slug = Path(source_url.rstrip("/")).name
    unquoted_slug = urllib.parse.unquote(raw_slug)
    slug = SLUG_OVERRIDES.get((family, raw_slug), SLUG_OVERRIDES.get((family, unquoted_slug), unquoted_slug))

    # Metadados de autoria e datas
    byline = soup.find("div", class_="documentByLine") or soup.find("div", id="plone-document-byline")
    byline_text = byline.get_text() if byline else ""

    published_date = None
    pub_tag = soup.find("span", property="rnews:datePublished") or soup.find("span", class_="documentPublished")
    if pub_tag:
        published_date = parse_date_str(pub_tag.get_text())
    if not published_date and byline_text:
        published_date = parse_date_str(byline_text)

    modified_date = None
    mod_tag = soup.find("span", property="rnews:dateModified") or soup.find("span", class_="documentModified")
    if mod_tag:
        modified_date = parse_date_str(mod_tag.get_text())
    if not modified_date and "última modificação" in byline_text:
        sub_text = byline_text.split("última modificação")[-1]
        modified_date = parse_date_str(sub_text)

    # Autoria e Colaboradores
    author = None
    author_tag = soup.find("span", class_="documentAuthor") or soup.find("span", property="rnews:author")
    if author_tag:
        author = clean_text(author_tag.get_text())

    contributors = None
    contrib_tag = soup.find("div", class_="documentContributors") or soup.find("span", property="rnews:contributor")
    if contrib_tag:
        contributors = clean_text(contrib_tag.get_text().replace("Colaboradores:", ""))

    # Conteúdo principal (Plone NITF rnews:articleBody tem prioridade máxima)
    article = soup.find("article")
    body_div = None
    if article:
        body_div = article.find("div", property="rnews:articleBody")

    if not body_div:
        body_div = soup.find("div", id="parent-fieldname-text") or soup.find("div", id="content-core")

    image_urls = []
    image_metadata = []
    audio_video_links = []
    references = []
    body_paragraphs = []

    # Encontrar imagens no container de cabeçalho / carrossel NITF
    if article:
        img_container = article.find("div", class_="newsImageContainer")
        if img_container:
            for a in img_container.find_all("a", class_="parent-nitf-image"):
                rights = a.get("data-rights") or ""
                img = a.find("img")
                if img and img.get("src"):
                    src = img.get("src")
                    if "search_icon" not in src:
                        full_src = urljoin(source_url, src)
                        image_urls.append(full_src)
                        image_metadata.append({
                            "src": full_src,
                            "caption": img.get("alt") or "",
                            "rights": rights
                        })

    if body_div:
        # Encontrar imagens inline
        for img in body_div.find_all("img"):
            src = img.get("src")
            if src and "search_icon" not in src:
                full_src = urljoin(source_url, src)
                if full_src not in image_urls:
                    image_urls.append(full_src)
                    image_metadata.append({
                        "src": full_src,
                        "caption": img.get("title") or img.get("alt") or "",
                        "rights": ""
                    })

        # Encontrar links de áudio/vídeo e documentos
        for a in body_div.find_all("a"):
            href = a.get("href", "")
            text = clean_text(a.get_text())
            if any(k in href for k in ("youtube.com", "youtu.be", "soundcloud.com", "docs.google.com")):
                audio_video_links.append({
                    "title": text or "Registro Fonográfico / Audiovisual",
                    "url": href
                })

        # Processar texto elemento a elemento
        in_references = False
        for el in body_div.children:
            name = getattr(el, "name", None)
            if not name:
                continue
            text = clean_text(el.get_text())
            if not text:
                continue

            # Detectar seção de referências
            if "referência" in text.lower() and name in ("h2", "h3", "h4", "p", "strong"):
                in_references = True
                body_paragraphs.append(f"\n### Referências\n")
                continue

            if in_references and name in ("p", "li"):
                references.append(text)
                body_paragraphs.append(text)
                continue

            if name == "h2":
                body_paragraphs.append(f"\n## {text}\n")
            elif name == "h3":
                body_paragraphs.append(f"\n### {text}\n")
            elif name == "h4":
                body_paragraphs.append(f"\n#### {text}\n")
            elif name == "blockquote" or "callout" in el.get("class", []):
                body_paragraphs.append(f"> {text}")
            elif name in ("ul", "ol"):
                for li in el.find_all("li"):
                    li_text = clean_text(li.get_text())
                    if li_text:
                        body_paragraphs.append(f"- {li_text}")
            else:
                # Detectar assinatura de autoria no final
                if ("&" in text or "Lumi" in text or "Satomi" in text or "Gabriel" in text) and len(text) < 80 and not author:
                    if not any(k in text.lower() for k in ("aerofone", "cordofone", "idiofone", "membranofone", "instrumento")):
                        author = text
                body_paragraphs.append(text)

    # Se body_paragraphs ficou vazio (por exemplo, Plone sem tags padrão)
    if not body_paragraphs and body_div:
        raw_t = clean_text(body_div.get_text())
        if raw_t:
            body_paragraphs.append(raw_t)

    # Adicionar subtítulo / descrição no início do corpo se relevante
    body = "\n\n".join(body_paragraphs)

    # Código MIMO / Hornbostel-Sachs
    mimo_code = extract_mimo_code(body) or (extract_mimo_code(description) if description else None)

    return {
        "title": title,
        "slug": slug,
        "subtitle": subtitle,
        "description": description,
        "family": family,
        "author": author or contributors,
        "reviewer": "Alice L. Satomi",
        "mimo_code": mimo_code,
        "source_url": source_url,
        "published_date": published_date,
        "modified_date": modified_date,
        "image_urls": image_urls,
        "image_metadata": image_metadata,
        "audio_video_links": audio_video_links,
        "references": references,
        "body": body
    }


def find_disk_images_for_dir(d: Path) -> List[Dict[str, Any]]:
    """Encontra os arquivos de imagem reais no disco para um diretório de instrumento do backup."""
    images = []
    seen = set()

    # 1. Arquivos diretos de imagem
    for f in sorted(d.iterdir()):
        if f.is_file() and f.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"):
            if "search_icon" not in f.name and f.name not in seen:
                seen.add(f.name)
                images.append({
                    "path": f,
                    "name": f.name,
                    "caption": f.stem.replace("-", " ").replace("_", " ").title()
                })

    # 2. Subdiretórios que representam Plone image objects
    for sub in sorted(d.iterdir()):
        if sub.is_dir():
            orig = sub / "original.jpg"
            if orig.exists() and orig.stat().st_size > 0:
                if sub.name not in seen:
                    seen.add(sub.name)
                    images.append({
                        "path": orig,
                        "name": f"{sub.name}.jpg" if not sub.name.endswith(".jpg") else sub.name,
                        "caption": sub.name.replace(".jpg", "").replace("-", " ").title()
                    })
            else:
                imgs_dir = sub / "@@images"
                if imgs_dir.exists():
                    jpegs = sorted(imgs_dir.glob("*"), key=lambda x: x.stat().st_size, reverse=True)
                    if jpegs and sub.name not in seen:
                        seen.add(sub.name)
                        best_jpeg = jpegs[0]
                        images.append({
                            "path": best_jpeg,
                            "name": f"{sub.name}.jpg" if not sub.name.endswith(".jpg") else sub.name,
                            "caption": sub.name.replace(".jpg", "").replace("-", " ").title()
                        })

    return images


class BrazinstExtractor:
    def __init__(self, output_dir: Path, session: requests.Session = None, backup_dir: Optional[Path] = None):
        self.output_dir = output_dir
        self.session = session or requests.Session()
        self.backup_dir = backup_dir or (output_dir.parent / "backup_full" / "labeet" / "contents" / "paginas" / "acervo-brazinst")
        self.state = StateManager(output_dir / "state_extraction.json")

    def run_offline(self):
        log(f"Iniciando extração OFFLINE do Brazil Instrumentarium a partir de {self.backup_dir}...")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        inst_dir = self.output_dir / "instruments"
        if inst_dir.exists():
            shutil.rmtree(inst_dir)
        inst_dir.mkdir(parents=True, exist_ok=True)
        catalog = []

        total_extracted = 0

        for folder_name, family in CATEGORY_DIR_MAP.items():
            cat_dir = self.backup_dir / folder_name
            if not cat_dir.exists():
                log(f"Diretório de categoria {cat_dir} não encontrado.", "WARN")
                continue

            subdirs = sorted([d for d in cat_dir.iterdir() if d.is_dir() and (d / "index.html").exists()])
            log(f"[FAMÍLIA: {family.upper()}] Encontradas {len(subdirs)} pastas em {folder_name}.")

            for d in subdirs:
                # Pular tabelas organológicas e pastas isoladas de imagem
                if "tabela" in d.name.lower() or d.name.endswith(".jpg") or d.name.endswith(".jpeg"):
                    continue

                html_path = d / "index.html"
                try:
                    html_content = html_path.read_text(encoding="utf-8")
                except Exception as e:
                    log(f"Erro ao ler {html_path}: {e}", "WARN")
                    continue

                source_url = f"http://150.165.254.38/labeet/contents/paginas/acervo-brazinst/{folder_name}/{d.name}"
                data = parse_verbete_html(html_content, source_url, local_dir=d)

                # Se não for instrumento (sem heading ou tabela)
                if not data["title"] or "tabela" in data["title"].lower():
                    continue

                slug = data["slug"]
                md_dir = self.output_dir / "instruments" / family
                md_path = md_dir / f"{slug}.md"
                inst_media_dir = self.output_dir / "media" / family / slug
                inst_media_dir.mkdir(parents=True, exist_ok=True)

                # Copiar fotos locais em disco
                local_images = []
                disk_imgs = find_disk_images_for_dir(d)
                for idx, item in enumerate(disk_imgs, 1):
                    src_file = item["path"]
                    # Sanitizar nome da imagem
                    ext = src_file.suffix or ".jpg"
                    if len(disk_imgs) == 1:
                        img_filename = f"{slug}{ext}"
                    else:
                        img_filename = f"img_{idx:02d}{ext}"
                    dest_file = inst_media_dir / img_filename
                    try:
                        shutil.copy2(str(src_file), str(dest_file))
                        rel_img_path = str(dest_file.relative_to(self.output_dir))
                        local_images.append({
                            "file": rel_img_path,
                            "caption": item.get("caption", ""),
                            "original_file": src_file.name
                        })
                    except Exception as e:
                        log(f"Erro ao copiar imagem {src_file}: {e}", "WARN")

                # Montar Frontmatter YAML
                frontmatter = {
                    "title": data["title"],
                    "slug": data["slug"],
                    "family": data["family"],
                    "subtitle": data["subtitle"],
                    "description": data["description"],
                    "mimo_code": data["mimo_code"],
                    "author": data["author"],
                    "reviewer": data["reviewer"],
                    "source_url": data["source_url"],
                    "published_date": data["published_date"],
                    "modified_date": data["modified_date"],
                    "images": local_images,
                    "audio_video_links": data["audio_video_links"],
                    "references": data["references"]
                }

                header_block = f"# {data['title']}\n"
                if data["subtitle"]:
                    header_block += f"\n*{data['subtitle']}*\n"
                if data["description"]:
                    header_block += f"\n> {data['description']}\n"

                md_content = f"---\n{yaml.dump(frontmatter, allow_unicode=True, sort_keys=False)}---\n\n{header_block}\n{data['body']}\n"

                md_dir.mkdir(parents=True, exist_ok=True)
                atomic_write_text(md_path, md_content)
                total_extracted += 1

                catalog.append({
                    "id": data["slug"],
                    "title": data["title"],
                    "family": data["family"],
                    "file_path": str(md_path.relative_to(self.output_dir)),
                    "media_count": len(local_images),
                    "audio_video_count": len(data["audio_video_links"]),
                    "has_body": len(data["body"].strip()) > 0
                })

        catalog_path = self.output_dir / "brazinst_catalog.json"
        atomic_write_text(catalog_path, json.dumps({
            "total_instruments": len(catalog),
            "instruments": catalog
        }, indent=2, ensure_ascii=False))
        log(f"Catálogo finalizado com {len(catalog)} instrumentos em {catalog_path}", "SUCCESS")
        return catalog

    def run(self):
        # Se o backup local existe, usar o modo offline completo
        if self.backup_dir.exists():
            return self.run_offline()

        log(f"Iniciando extração do Brazil Instrumentarium para {self.output_dir} via HTTP...")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        catalog = []

        for family, cat_url in CATEGORIES.items():
            resp = fetch_url(cat_url, self.session)
            if resp.status_code != 200:
                continue

            soup = BeautifulSoup(resp.text, "html.parser")
            instrument_links = []
            for a in soup.find_all("a", class_="summary"):
                href = a.get("href")
                if href and href != cat_url and "tabela-organologica" not in href:
                    instrument_links.append(urljoin(cat_url, href))

            for inst_url in instrument_links:
                slug = Path(inst_url.rstrip("/")).name
                md_dir = self.output_dir / "instruments" / family
                md_path = md_dir / f"{slug}.md"

                inst_resp = fetch_url(inst_url, self.session)
                if inst_resp.status_code != 200:
                    continue

                data = parse_verbete_html(inst_resp.text, inst_url)
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
                    except Exception as e:
                        log(f"Falha ao baixar imagem {img_url}: {e}", "WARN")

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

                catalog.append({
                    "id": data["slug"],
                    "title": data["title"],
                    "family": data["family"],
                    "file_path": str(md_path.relative_to(self.output_dir)),
                    "media_count": len(local_images),
                    "audio_video_count": len(data["audio_video_links"])
                })

        catalog_path = self.output_dir / "brazinst_catalog.json"
        atomic_write_text(catalog_path, json.dumps({
            "total_instruments": len(catalog),
            "instruments": catalog
        }, indent=2, ensure_ascii=False))
        return catalog


if __name__ == "__main__":
    root_dir = Path(__file__).resolve().parent.parent
    out = root_dir / "content_brazinst"
    extractor = BrazinstExtractor(out)
    extractor.run()
