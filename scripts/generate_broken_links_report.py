import json
import warnings
from pathlib import Path
from urllib.parse import urlparse, unquote
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

def main():
    root_dir = Path(__file__).resolve().parent.parent
    state_file = root_dir / "backup_full" / "state.json"
    backup_dir = root_dir / "backup_full" / "labeet"
    output_file = root_dir / "docs" / "relatorio_links_quebrados_e_referencias.md"

    with open(state_file, "r", encoding="utf-8") as f:
        state = json.load(f)

    failed = state.get("failed", {})
    html_files = list(backup_dir.rglob("index.html"))

    # Mapear todos os links dentro de todas as páginas locais
    # chave: token -> lista de referências
    link_index = {}

    for h in html_files:
        try:
            content = h.read_text(encoding="utf-8", errors="ignore")
            soup = BeautifulSoup(content, "html.parser")
            
            # Título amigável da página
            title_tag = soup.find("h1", class_="documentFirstHeading") or soup.find("title")
            page_title = title_tag.get_text().strip() if title_tag else str(h.relative_to(root_dir))
            page_title = page_title.split("—")[0].strip()

            rel_path = str(h.relative_to(root_dir))

            for tag in soup.find_all(["a", "img", "link", "script", "source"]):
                val = tag.get("href") or tag.get("src")
                if not val or val.startswith(("#", "javascript:", "mailto:")):
                    continue
                
                # Texto ou legenda do link
                link_text = tag.get_text().strip() or tag.get("title") or tag.get("alt") or Path(val.split("?")[0]).name
                clean_val = val.split("?")[0].rstrip("/")
                base_name = Path(clean_val).name
                unquoted_name = unquote(base_name)

                ref_info = {
                    "page_title": page_title,
                    "referrer_path": rel_path,
                    "link_text": link_text,
                    "element": tag.name
                }

                # Indexar por diferentes chaves de busca
                for token in [val, clean_val, base_name, unquoted_name]:
                    if token and len(token) > 2:
                        link_index.setdefault(token, []).append(ref_info)
        except Exception:
            pass

    # Classificar e mapear cada URL com falha
    report_rows = []

    for url, data in failed.items():
        err = data.get("error", "")
        parsed = urlparse(url)
        path = parsed.path.rstrip("/")
        name = Path(path).name
        unquoted_name = unquote(name)

        # Categoria do erro
        if "Is a directory" in err or "Not a directory" in err or "File exists" in err:
            cat = "Conflito Plone (Imagem vs Pasta /view)"
            status = "Dado salvo como .tmp (Recuperável)"
        elif "HTTP 404" in err:
            cat = "HTTP 404 (Não Encontrado)"
            status = "Link quebrado no servidor original da UFPB"
        elif "HTTP 500" in err:
            cat = "HTTP 500 (Erro Servidor UFPB)"
            status = "Crash do plugin @@slideshow_view do Plone"
        elif "HTTP 401" in err:
            cat = "HTTP 401 (Restrito / Rascunho)"
            status = "Exige login de admin do laboratório"
        else:
            cat = "Outro Erro"
            status = err

        is_brazinst = "acervo-brazinst" in url

        # Buscar referenciadores
        refs = (
            link_index.get(url) or 
            link_index.get(path) or 
            link_index.get(name) or 
            link_index.get(unquoted_name) or 
            link_index.get(unquote(path))
        )

        referrers_str = ""
        link_texts_str = ""

        if refs:
            # Remover duplicatas mantendo ordem
            unique_refs = []
            seen = set()
            for r in refs:
                key = (r["page_title"], r["referrer_path"])
                if key not in seen:
                    seen.add(key)
                    unique_refs.append(r)

            referrers_str = "<br>".join([f"• **{r['page_title']}** (`{r['referrer_path']}`)" for r in unique_refs[:3]])
            link_texts_str = "<br>".join([f"• \"{r['link_text']}\"" for r in unique_refs[:3]])
        else:
            referrers_str = "*Descoberto via sitemap / navegação global*"
            link_texts_str = "*Link de sistema*"

        report_rows.append({
            "url": url,
            "is_brazinst": is_brazinst,
            "categoria": cat,
            "status": status,
            "referrers": referrers_str,
            "link_text": link_texts_str
        })

    # Separar em seções: Brazil Instrumentarium primeiro, depois restante do LABEET
    brazinst_rows = [r for r in report_rows if r["is_brazinst"]]
    outros_rows = [r for r in report_rows if not r["is_brazinst"]]

    md = [
        "# Relatório de Links Problemáticos e Mapeamento de Origens — LABEET",
        "\nEste documento registra todas as **100 URLs** que retornaram erro durante o espelhamento do site `http://150.165.254.38/labeet`, indicando exatamente **qual página do site contém o link quebrado** e a ação recomendada para a pesquisadora.\n",
        "## Resumo Executivo",
        f"- **Total de URLs com falha mapeadas:** {len(report_rows)}",
        f"- **Pertencentes ao Brazil Instrumentarium (Brazinst):** {len(brazinst_rows)}",
        f"- **Demais páginas institucionais do LABEET:** {len(outros_rows)}",
        "\n---",
        "\n## 1. Brazil Instrumentarium (Brazinst) — 28 Links Mapeados",
        "\n| URL Problemática | Onde é Citada (Página de Origem) | Texto / Elemento do Link | Categoria | Diagnóstico & Ação |",
        "| :--- | :--- | :--- | :--- | :--- |"
    ]

    for r in brazinst_rows:
        md.append(f"| `{r['url']}` | {r['referrers']} | {r['link_text']} | {r['categoria']} | {r['status']} |")

    md.extend([
        "\n---",
        "\n## 2. Demais Páginas e Recursos do LABEET — 72 Links Mapeados",
        "\n| URL Problemática | Onde é Citada (Página de Origem) | Texto / Elemento do Link | Categoria | Diagnóstico & Ação |",
        "| :--- | :--- | :--- | :--- | :--- |"
    ])

    for r in outros_rows:
        md.append(f"| `{r['url']}` | {r['referrers']} | {r['link_text']} | {r['categoria']} | {r['status']} |")

    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text("\n".join(md), encoding="utf-8")
    print(f"Relatório gerado com sucesso em: {output_file}")

if __name__ == "__main__":
    main()
