#!/usr/bin/env python3
"""
Validador de integridade para contribuições de instrumentos no acervo Brazil Instrumentarium.
Verifica metadados YAML, arquivos de mídia, remissões e links internos.
"""

from dataclasses import dataclass
from pathlib import Path
import argparse
import os
import re
import sys

try:
    import yaml
except ImportError:
    venv_py = Path(__file__).resolve().parent.parent / ".venv" / "bin" / "python3"
    if venv_py.exists() and sys.executable != str(venv_py):
        import subprocess
        res = subprocess.run([str(venv_py), str(Path(__file__).resolve())] + sys.argv[1:])
        sys.exit(res.returncode)
    else:
        print("Erro: PyYAML não está instalado no ambiente Python atual.", file=sys.stderr)
        print("Instale via 'pip install PyYAML' ou ative o ambiente virtual: 'source .venv/bin/activate'.", file=sys.stderr)
        sys.exit(1)


VALID_FAMILIES = {"aerofones", "cordofones", "idiofones", "membranofones"}
DATE_REGEX = re.compile(r"^\d{4}-\d{2}-\d{2}$")
INTERNAL_LINK_REGEX = re.compile(r"\[([^\]]+)\]\((/instrumentos/([a-zA-Z0-9_\-]+))\)")


@dataclass
class ValidationIssue:
    file_path: str
    instrument_name: str
    category: str
    field: str
    severity: str  # "error" | "warning"
    message: str
    suggestion: str


def check_instrument_content(
    md_path: Path,
    all_slugs: dict[str, dict[str, str]],
    public_dir: Path
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    rel_path = str(md_path)
    file_slug = md_path.stem
    folder_family = md_path.parent.name

    try:
        raw_text = md_path.read_text(encoding="utf-8")
    except Exception as e:
        issues.append(
            ValidationIssue(
                file_path=rel_path,
                instrument_name=file_slug,
                category="Arquivo",
                field="encoding",
                severity="error",
                message=f"Falha ao ler o arquivo em UTF-8: {e}",
                suggestion="Salvar o arquivo em codificação UTF-8 sem BOM."
            )
        )
        return issues

    if not raw_text.startswith("---"):
        issues.append(
            ValidationIssue(
                file_path=rel_path,
                instrument_name=file_slug,
                category="Estrutura",
                field="frontmatter",
                severity="error",
                message="Arquivo sem cabeçalho de metadados YAML inicial.",
                suggestion="Incluir bloco de metadados delimitado por '---' no início do arquivo."
            )
        )
        return issues

    parts = raw_text.split("---", 2)
    if len(parts) < 3:
        issues.append(
            ValidationIssue(
                file_path=rel_path,
                instrument_name=file_slug,
                category="Estrutura",
                field="frontmatter",
                severity="error",
                message="Cabeçalho YAML sem delimitador de fechamento '---'.",
                suggestion="Fechar o bloco de metadados com '---' antes do corpo do texto."
            )
        )
        return issues

    frontmatter_raw = parts[1]
    body_text = parts[2].strip()

    try:
        fm = yaml.safe_load(frontmatter_raw)
        if not isinstance(fm, dict):
            raise ValueError("O frontmatter YAML deve ser um objeto chave-valor.")
    except Exception as e:
        issues.append(
            ValidationIssue(
                file_path=rel_path,
                instrument_name=file_slug,
                category="Sintaxe YAML",
                field="frontmatter",
                severity="error",
                message=f"Erro de sintaxe YAML: {e}",
                suggestion="Corrigir a indentação e o uso de aspas nos campos."
            )
        )
        return issues

    inst_title = str(fm.get("title") or file_slug)

    # 1. Título
    title = fm.get("title")
    if not title or not str(title).strip():
        issues.append(
            ValidationIssue(
                file_path=rel_path,
                instrument_name=inst_title,
                category="Metadados",
                field="title",
                severity="error",
                message="Campo 'title' ausente ou vazio.",
                suggestion="Preencher o nome do instrumento (ex: title: \"Agogô\")."
            )
        )

    # 2. Família
    family = fm.get("family")
    if not family:
        issues.append(
            ValidationIssue(
                file_path=rel_path,
                instrument_name=inst_title,
                category="Organologia",
                field="family",
                severity="error",
                message="Campo 'family' obrigatório ausente.",
                suggestion=f"Definir 'family: \"{folder_family}\"' correspondente à pasta."
            )
        )
    elif family not in VALID_FAMILIES:
        issues.append(
            ValidationIssue(
                file_path=rel_path,
                instrument_name=inst_title,
                category="Organologia",
                field="family",
                severity="error",
                message=f"Família '{family}' inválida.",
                suggestion="Usar uma das famílias permitidas: aerofones, cordofones, idiofones, membranofones."
            )
        )
    elif family != folder_family:
        issues.append(
            ValidationIssue(
                file_path=rel_path,
                instrument_name=inst_title,
                category="Estrutura de Pastas",
                field="family",
                severity="error",
                message=f"Família no frontmatter ('{family}') diverge da pasta ('{folder_family}').",
                suggestion=f"Mover o arquivo para 'web/src/content/instruments/{family}/' ou alterar o frontmatter para 'family: \"{folder_family}\"'."
            )
        )

    # 3. Slug
    fm_slug = fm.get("slug")
    if fm_slug and fm_slug != file_slug:
        issues.append(
            ValidationIssue(
                file_path=rel_path,
                instrument_name=inst_title,
                category="Metadados",
                field="slug",
                severity="warning",
                message=f"Campo 'slug' ('{fm_slug}') difere do nome do arquivo ('{file_slug}.md').",
                suggestion=f"Definir 'slug: \"{file_slug}\"' para manter consistência."
            )
        )

    # 4. Descrição
    description = fm.get("description")
    if not description or len(str(description).strip()) < 10:
        issues.append(
            ValidationIssue(
                file_path=rel_path,
                instrument_name=inst_title,
                category="Conteúdo",
                field="description",
                severity="warning",
                message="Campo 'description' ausente ou com menos de 10 caracteres.",
                suggestion="Adicionar descrição sucinta para indexação e metadados."
            )
        )

    # 5. Datas
    for date_field in ("published_date", "modified_date"):
        val = fm.get(date_field)
        if val and not DATE_REGEX.match(str(val)):
            issues.append(
                ValidationIssue(
                    file_path=rel_path,
                    instrument_name=inst_title,
                    category="Formato",
                    field=date_field,
                    severity="warning",
                    message=f"Data '{val}' fora do formato ISO AAAA-MM-DD.",
                    suggestion="Formatar como AAAA-MM-DD (ex: 2026-09-02)."
                )
            )

    # 6. Imagens
    images = fm.get("images")
    if images:
        if not isinstance(images, list):
            issues.append(
                ValidationIssue(
                    file_path=rel_path,
                    instrument_name=inst_title,
                    category="Mídias",
                    field="images",
                    severity="error",
                    message="Campo 'images' deve ser uma lista de objetos.",
                    suggestion="Estruturar como lista de itens com 'file' e 'caption'."
                )
            )
        else:
            for idx, img in enumerate(images, 1):
                if not isinstance(img, dict) or not img.get("file"):
                    issues.append(
                        ValidationIssue(
                            file_path=rel_path,
                            instrument_name=inst_title,
                            category="Mídias",
                            field=f"images[{idx}]",
                            severity="error",
                            message=f"Item #{idx} em 'images' sem propriedade 'file'.",
                            suggestion="Definir caminho relativo em 'file' (ex: 'media/idiofones/agogo/foto.jpg')."
                        )
                    )
                    continue

                img_rel = str(img.get("file")).lstrip("/")
                img_path = public_dir / img_rel
                if not img_path.is_file():
                    issues.append(
                        ValidationIssue(
                            file_path=rel_path,
                            instrument_name=inst_title,
                            category="Mídias",
                            field=f"images[{idx}]",
                            severity="error",
                            message=f"Arquivo de imagem não encontrado em 'web/public/{img_rel}'.",
                            suggestion=f"Adicionar o arquivo em 'web/public/{img_rel}' ou corrigir o caminho."
                        )
                    )
                elif img_path.stat().st_size == 0:
                    issues.append(
                        ValidationIssue(
                            file_path=rel_path,
                            instrument_name=inst_title,
                            category="Mídias",
                            field=f"images[{idx}]",
                            severity="error",
                            message=f"Arquivo de imagem 'web/public/{img_rel}' possui 0 bytes.",
                            suggestion="Substituir por arquivo de imagem válido."
                        )
                    )

                if not img.get("caption"):
                    issues.append(
                        ValidationIssue(
                            file_path=rel_path,
                            instrument_name=inst_title,
                            category="Acessibilidade",
                            field=f"images[{idx}].caption",
                            severity="warning",
                            message=f"Imagem '{img_rel}' sem legenda descritiva ('caption').",
                            suggestion="Incluir texto descritivo para leitores de tela."
                        )
                    )

    # 7. Remissões (related_instruments)
    related = fm.get("related_instruments")
    if related:
        if not isinstance(related, list):
            issues.append(
                ValidationIssue(
                    file_path=rel_path,
                    instrument_name=inst_title,
                    category="Remissões",
                    field="related_instruments",
                    severity="error",
                    message="Campo 'related_instruments' deve ser uma lista.",
                    suggestion="Formatar como lista de objetos com 'slug', 'title', 'family' e 'relation'."
                )
            )
        else:
            for idx, rel_item in enumerate(related, 1):
                if not isinstance(rel_item, dict):
                    continue
                r_slug = str(rel_item.get("slug", ""))
                r_fam = str(rel_item.get("family", ""))
                if not r_slug:
                    issues.append(
                        ValidationIssue(
                            file_path=rel_path,
                            instrument_name=inst_title,
                            category="Remissões",
                            field=f"related_instruments[{idx}]",
                            severity="error",
                            message=f"Item #{idx} em 'related_instruments' sem 'slug'.",
                            suggestion="Especificar o slug do instrumento relacionado."
                        )
                    )
                elif r_slug not in all_slugs:
                    issues.append(
                        ValidationIssue(
                            file_path=rel_path,
                            instrument_name=inst_title,
                            category="Remissões",
                            field=f"related_instruments[{idx}]",
                            severity="error",
                            message=f"Instrumento relacionado '{r_slug}' não encontrado no catálogo.",
                            suggestion="Verificar se o slug existe em 'web/src/content/instruments/'."
                        )
                    )
                elif r_fam and r_fam != all_slugs[r_slug]["family"]:
                    actual_fam = all_slugs[r_slug]["family"]
                    issues.append(
                        ValidationIssue(
                            file_path=rel_path,
                            instrument_name=inst_title,
                            category="Remissões",
                            field=f"related_instruments[{idx}].family",
                            severity="warning",
                            message=f"Família informada para '{r_slug}' ('{r_fam}') difere do catálogo ('{actual_fam}').",
                            suggestion=f"Ajustar para 'family: \"{actual_fam}\"'."
                        )
                    )

    # 8. Links internos no corpo
    for match in INTERNAL_LINK_REGEX.finditer(body_text):
        link_text, full_url, target_slug = match.groups()
        if target_slug not in all_slugs:
            issues.append(
                ValidationIssue(
                    file_path=rel_path,
                    instrument_name=inst_title,
                    category="Hiperlinks",
                    field="body",
                    severity="error",
                    message=f"Link '[{link_text}]({full_url})' aponta para slug inexistente ('{target_slug}').",
                    suggestion="Corrigir o link para um slug existente no catálogo."
                )
            )

    # 9. Corpo do texto
    if len(body_text) < 30:
        issues.append(
            ValidationIssue(
                file_path=rel_path,
                instrument_name=inst_title,
                category="Conteúdo",
                field="body",
                severity="warning",
                message="Corpo do verbete possui menos de 30 caracteres.",
                suggestion="Incluir texto descritivo sobre contexto organológico e musical."
            )
        )

    return issues


def run_validation(
    instruments_dir: Path,
    public_dir: Path,
    changed_files: list[str] | None = None
) -> tuple[int, list[ValidationIssue]]:
    all_slugs: dict[str, dict[str, str]] = {}
    all_files: list[Path] = []

    for md_path in instruments_dir.glob("**/*.md"):
        slug = md_path.stem
        family = md_path.parent.name
        all_slugs[slug] = {
            "family": family,
            "path": str(md_path)
        }
        all_files.append(md_path)

    files_to_check = all_files
    if changed_files:
        changed_set = {str(Path(f).resolve()) for f in changed_files if f.endswith(".md")}
        if changed_set:
            files_to_check = [f for f in all_files if str(f.resolve()) in changed_set]

    total_issues: list[ValidationIssue] = []
    for md_file in files_to_check:
        issues = check_instrument_content(md_file, all_slugs, public_dir)
        total_issues.extend(issues)

    return len(files_to_check), total_issues


def generate_markdown_report(checked_count: int, issues: list[ValidationIssue]) -> str:
    errors = [i for i in issues if i.severity == "error"]
    warnings = [i for i in issues if i.severity == "warning"]

    lines = []
    lines.append("# Validação de Integridade do Acervo")
    lines.append("")

    if not errors and not warnings:
        lines.append(f"Status: Aprovado ({checked_count} instrumentos verificados).")
        lines.append("")
        lines.append("- Metadados YAML validados.")
        lines.append("- Mídias locais verificadas.")
        lines.append("- Referências cruzadas e hiperlinks validados.")
        lines.append("- Classificação organológica conforme.")
        return "\n".join(lines)

    lines.append(f"Status: {len(errors)} erro(s), {len(warnings)} aviso(s) em {checked_count} instrumento(s).")
    lines.append("")

    if errors:
        lines.append("### Inconformidades (bloqueantes)")
        lines.append("")
        lines.append("| Arquivo | Campo | Inconformidade | Ação necessária |")
        lines.append("| :--- | :--- | :--- | :--- |")
        for err in errors:
            lines.append(f"| `{Path(err.file_path).name}` | `{err.field}` | {err.message} | {err.suggestion} |")
        lines.append("")

    if warnings:
        lines.append("### Avisos (não bloqueantes)")
        lines.append("")
        lines.append("| Arquivo | Campo | Detalhe | Sugestão |")
        lines.append("| :--- | :--- | :--- | :--- |")
        for w in warnings:
            lines.append(f"| `{Path(w.file_path).name}` | `{w.field}` | {w.message} | {w.suggestion} |")
        lines.append("")

    lines.append("### Próximos passos")
    lines.append("1. Corrigir os itens listados nos arquivos correspondentes.")
    lines.append("2. Executar localmente `npm --prefix web test` e `pytest`.")
    lines.append("3. Enviar novo commit para o branch do PR.")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Validador de integridade do catálogo de instrumentos.")
    parser.add_argument("--dir", default="web/src/content/instruments", help="Diretório dos instrumentos Markdown")
    parser.add_argument("--public-dir", default="web/public", help="Diretório de assets públicos")
    parser.add_argument("--summary-file", help="Arquivo de destino para o relatório Markdown")
    parser.add_argument("--changed-files", nargs="*", help="Lista de arquivos para validação pontual")
    args = parser.parse_args()

    instruments_dir = Path(args.dir)
    public_dir = Path(args.public_dir)

    if not instruments_dir.exists():
        print(f"Erro: diretório '{instruments_dir}' não encontrado.", file=sys.stderr)
        sys.exit(1)

    checked_count, issues = run_validation(instruments_dir, public_dir, args.changed_files)
    report = generate_markdown_report(checked_count, issues)

    print(report)

    summary_path = args.summary_file or os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        try:
            with open(summary_path, "a", encoding="utf-8") as f:
                f.write(f"\n{report}\n")
        except Exception as e:
            print(f"Aviso: falha ao gravar GITHUB_STEP_SUMMARY: {e}", file=sys.stderr)

    errors = [i for i in issues if i.severity == "error"]
    if errors:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
