#!/usr/bin/env python3
"""
Validador de integridade para contribuições de instrumentos no acervo Brazil Instrumentarium (LABEET/UFPB).
Gera relatórios acolhedores, empáticos e educativos ("com carinho") orientando contribuidores sobre correções.
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
                message=f"Não foi possível ler o arquivo em UTF-8 ({e}).",
                suggestion="Salve o arquivo no formato de texto UTF-8 sem BOM."
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
                message="O arquivo não começa com o bloco de metadados YAML (delimitado por `---`).",
                suggestion="Adicione o bloco de metadados `---` no topo do arquivo conforme o modelo no README.md."
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
                message="O bloco de metadados YAML não foi fechado com `---`.",
                suggestion="Certifique-se de fechar os metadados com uma linha contendo apenas `---` antes do corpo do texto."
            )
        )
        return issues

    frontmatter_raw = parts[1]
    body_text = parts[2].strip()

    try:
        fm = yaml.safe_load(frontmatter_raw)
        if not isinstance(fm, dict):
            raise ValueError("O frontmatter YAML deve ser um dicionário/objeto com pares chave-valor.")
    except Exception as e:
        issues.append(
            ValidationIssue(
                file_path=rel_path,
                instrument_name=file_slug,
                category="Sintaxe YAML",
                field="frontmatter",
                severity="error",
                message=f"Erro de sintaxe no cabeçalho YAML: {e}",
                suggestion="Verifique a indentação e o uso correto de aspas nos campos de texto."
            )
        )
        return issues

    inst_title = str(fm.get("title") or file_slug)

    # 1. Validação de Título
    title = fm.get("title")
    if not title or not str(title).strip():
        issues.append(
            ValidationIssue(
                file_path=rel_path,
                instrument_name=inst_title,
                category="Metadados",
                field="title",
                severity="error",
                message="O campo `title` está ausente ou em branco.",
                suggestion="Informe o nome principal do instrumento (ex.: `title: \"Agogô\"`)."
            )
        )

    # 2. Validação de Família
    family = fm.get("family")
    if not family:
        issues.append(
            ValidationIssue(
                file_path=rel_path,
                instrument_name=inst_title,
                category="Organologia",
                field="family",
                severity="error",
                message="O campo `family` é obrigatório.",
                suggestion=f"Defina a família organológica do instrumento. Para este diretório, use `family: \"{folder_family}\"`."
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
                message=f"Família `{family}` não reconhecida.",
                suggestion=f"A família deve ser uma das 4 opções padronizadas: `aerofones`, `cordofones`, `idiofones` ou `membranofones`."
            )
        )
    elif family != folder_family:
        issues.append(
            ValidationIssue(
                file_path=rel_path,
                instrument_name=inst_title,
                category="Organização de Pastas",
                field="family",
                severity="error",
                message=f"A família `{family}` no cabeçalho diverge da pasta onde o arquivo está salvo (`{folder_family}`).",
                suggestion=f"Mova o arquivo para a pasta `web/src/content/instruments/{family}/` ou ajuste o campo `family: \"{folder_family}\"`."
            )
        )

    # 3. Validação de Slug
    fm_slug = fm.get("slug")
    if fm_slug and fm_slug != file_slug:
        issues.append(
            ValidationIssue(
                file_path=rel_path,
                instrument_name=inst_title,
                category="Metadados",
                field="slug",
                severity="warning",
                message=f"O campo `slug: \"{fm_slug}\"` difere do nome do arquivo `{file_slug}.md`.",
                suggestion=f"Recomendamos que o campo `slug` coincida exatamente com o nome do arquivo (`slug: \"{file_slug}\"`)."
            )
        )

    # 4. Validação de Descrição
    description = fm.get("description")
    if not description or len(str(description).strip()) < 10:
        issues.append(
            ValidationIssue(
                file_path=rel_path,
                instrument_name=inst_title,
                category="Conteúdo",
                field="description",
                severity="warning",
                message="A descrição introdutória (`description`) está muito curta ou ausente.",
                suggestion="Adicione uma frase-resumo sobre o instrumento para enriquecer os resultados de busca e redes sociais."
            )
        )

    # 5. Validação de Datas
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
                    message=f"O campo `{date_field}: \"{val}\"` não está no padrão ISO `AAAA-MM-DD`.",
                    suggestion="Utilize o formato de data no padrão Ano-Mês-Dia (exemplo: `2026-09-02`)."
                )
            )

    # 6. Validação de Imagens e Arquivos de Mídia
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
                    message="O campo `images` deve ser uma lista de imagens.",
                    suggestion="Defina `images` como uma lista com itens contendo `file: ...` e `caption: ...`."
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
                            message=f"A imagem #{idx} não possui a propriedade `file`.",
                            suggestion="Especifique o caminho da imagem relativo à pasta public (ex.: `file: \"media/idiofones/agogo/foto.jpg\"`)."
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
                            message=f"Arquivo de imagem `{img_rel}` não foi encontrado em `web/public/`.",
                            suggestion=f"Certifique-se de adicionar o arquivo de imagem em `web/public/{img_rel}`."
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
                            message=f"O arquivo de imagem `{img_rel}` está corrompido (tamanho de 0 bytes).",
                            suggestion="Substitua o arquivo por uma imagem válida com conteúdo."
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
                            message=f"A imagem `{img_rel}` não possui legenda descritiva (`caption`).",
                            suggestion="Adicionar legendas descritivas ajuda na acessibilidade para leitores de tela e contexto histórico."
                        )
                    )

    # 7. Validação de Referências Cruzadas (related_instruments)
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
                    message="O campo `related_instruments` deve ser uma lista.",
                    suggestion="Formate como uma lista de instrumentos: `- slug: ... \n  title: ... \n  family: ... \n  relation: ...`"
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
                            message=f"O item #{idx} em `related_instruments` não possui `slug` definido.",
                            suggestion="Indique o slug do instrumento correspondente (ex.: `slug: \"reco-reco\"`)."
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
                            message=f"Instrumento relacionado `{r_slug}` não existe no acervo.",
                            suggestion=f"Verifique se o slug `{r_slug}` está digitado corretamente conforme catalogado no acervo."
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
                            message=f"A família informada para `{r_slug}` foi `{r_fam}`, mas no acervo ele pertence a `{actual_fam}`.",
                            suggestion=f"Ajuste a família deste item para `family: \"{actual_fam}\"`."
                        )
                    )

    # 8. Validação de Links Internos no Corpo do Texto
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
                    message=f"O link interno `[{link_text}]({full_url})` aponta para um instrumento inexistente (`{target_slug}`).",
                    suggestion=f"Verifique o slug do instrumento ou utilize o nome exato registrado no acervo."
                )
            )

    # 9. Validação do Corpo do Verbete
    if len(body_text) < 30:
        issues.append(
            ValidationIssue(
                file_path=rel_path,
                instrument_name=inst_title,
                category="Conteúdo",
                field="body",
                severity="warning",
                message="O corpo do verbete está muito conciso.",
                suggestion="Enriqueça o verbete com informações sobre contexto musical, histórico, afinação ou modo de tocar."
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

    # Filtrar arquivos a validar se especificado
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


def generate_friendly_markdown(checked_count: int, issues: list[ValidationIssue]) -> str:
    errors = [i for i in issues if i.severity == "error"]
    warnings = [i for i in issues if i.severity == "warning"]

    lines = []
    lines.append("# 🌿 Validação da Contribuição — Brazil Instrumentarium (LABEET/UFPB)")
    lines.append("")
    lines.append("> *Muito obrigado por contribuir com a preservação da memória e da diversidade da música brasileira!* ✨")
    lines.append("")

    if not errors and not warnings:
        lines.append("### 🎉 Tudo perfeito e em conformidade!")
        lines.append(f"Analisamos **{checked_count}** instrumento(s) nesta contribuição e não encontramos nenhuma inconformidade.")
        lines.append("")
        lines.append("- ✅ Metadados YAML validados com sucesso.")
        lines.append("- ✅ Todas as imagens e mídias existem e estão íntegras.")
        lines.append("- ✅ Referências cruzadas e hiperlinks verificados.")
        lines.append("- ✅ Classificação organológica alinhada com as famílias.")
        lines.append("")
        lines.append("Seu verbete está pronto para compor o acervo permanente do **LABEET / UFPB**! 🇧🇷🎶")
        return "\n".join(lines)

    if errors:
        lines.append("### 💛 Identificamos alguns pequenos detalhes para ajustar")
        lines.append(f"Avaliamos **{checked_count}** instrumento(s). Encontramos **{len(errors)}** ponto(s) que precisam de ajuste e **{len(warnings)}** sugestão(ões) de melhoria.")
        lines.append("")
        lines.append("Não se preocupe! Criamos uma lista explicativa com orientações passo a passo para ajudar você:")
        lines.append("")
        lines.append("| Instrumento | Categoria / Campo | O que foi observado | Como ajustar com carinho 💡 |")
        lines.append("| :--- | :--- | :--- | :--- |")
        for err in errors:
            lines.append(f"| **{err.instrument_name}** (`{Path(err.file_path).name}`) | `{err.category}` / `{err.field}` | {err.message} | {err.suggestion} |")
        lines.append("")

    if warnings and not errors:
        lines.append("### 🌟 Seu conteúdo está válido, com algumas dicas opcionais!")
        lines.append(f"Nenhum erro impeditivo foi encontrado em **{checked_count}** instrumento(s). Temos apenas **{len(warnings)}** sugestão(ões) para deixar o verbete ainda mais completo:")
        lines.append("")
        lines.append("| Instrumento | Campo | Sugestão de Melhoria |")
        lines.append("| :--- | :--- | :--- |")
        for w in warnings:
            lines.append(f"| **{w.instrument_name}** | `{w.field}` | {w.suggestion} |")
        lines.append("")

    lines.append("---")
    lines.append("### 🛠️ O que fazer agora?")
    lines.append("1. Faça as correções indicadas nos arquivos no seu branch local.")
    lines.append("2. Execute `npm --prefix web test` e `pytest` para confirmar que tudo passou.")
    lines.append("3. Envie um novo commit (`git commit` & `git push`). Esta verificação rodará novamente de forma automática.")
    lines.append("")
    lines.append("Qualquer dúvida sobre a organologia ou classificação Hornbostel-Sachs, sinta-se à vontade para perguntar à equipe do **LABEET**! 🤝")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Validador acolhedor de contribuições de instrumentos.")
    parser.add_argument("--dir", default="web/src/content/instruments", help="Diretório dos instrumentos Markdown")
    parser.add_argument("--public-dir", default="web/public", help="Diretório de assets públicos")
    parser.add_argument("--summary-file", help="Arquivo onde gravar o relatório em Markdown (ex: GITHUB_STEP_SUMMARY)")
    parser.add_argument("--changed-files", nargs="*", help="Lista de arquivos modificados para checagem pontual")
    args = parser.parse_args()

    instruments_dir = Path(args.dir)
    public_dir = Path(args.public_dir)

    if not instruments_dir.exists():
        print(f"❌ Diretório de instrumentos '{instruments_dir}' não foi encontrado.", file=sys.stderr)
        sys.exit(1)

    checked_count, issues = run_validation(instruments_dir, public_dir, args.changed_files)
    md_report = generate_friendly_markdown(checked_count, issues)

    # Imprimir no terminal
    print(md_report)

    # Gravar em arquivo de summary do GitHub Actions se solicitado
    summary_path = args.summary_file or os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        try:
            with open(summary_path, "a", encoding="utf-8") as f:
                f.write(f"\n{md_report}\n")
        except Exception as e:
            print(f"Aviso: Não foi possível gravar no GITHUB_STEP_SUMMARY: {e}", file=sys.stderr)

    errors = [i for i in issues if i.severity == "error"]
    if errors:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
