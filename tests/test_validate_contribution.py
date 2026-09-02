from pathlib import Path
import pytest
from scripts.validate_contribution import (
    check_instrument_content,
    run_validation,
    generate_markdown_report,
    ValidationIssue
)


def test_validate_valid_instrument(tmp_path: Path):
    inst_dir = tmp_path / "web" / "src" / "content" / "instruments" / "idiofones"
    inst_dir.mkdir(parents=True)
    public_dir = tmp_path / "web" / "public"
    media_dir = public_dir / "media" / "idiofones" / "agogo"
    media_dir.mkdir(parents=True)

    img = media_dir / "agogo.jpg"
    img.write_bytes(b"image data")

    md_file = inst_dir / "agogo.md"
    md_file.write_text("""---
title: "Agogô"
slug: "agogo"
family: "idiofones"
description: "Instrumento idiofônico de metal de origem africana."
published_date: "2026-09-02"
images:
  - file: "media/idiofones/agogo/agogo.jpg"
    caption: "Agogô duplo de ferro"
---
# Agogô

O agogô é tocado com baqueta de ferro ou madeira.
""", encoding="utf-8")

    all_slugs = {"agogo": {"family": "idiofones", "path": str(md_file)}}
    issues = check_instrument_content(md_file, all_slugs, public_dir)
    errors = [i for i in issues if i.severity == "error"]
    assert len(errors) == 0


def test_validate_missing_fields_and_broken_image(tmp_path: Path):
    inst_dir = tmp_path / "web" / "src" / "content" / "instruments" / "cordofones"
    inst_dir.mkdir(parents=True)
    public_dir = tmp_path / "web" / "public"

    md_file = inst_dir / "berimbau.md"
    md_file.write_text("""---
title: ""
family: "idiofones" # Erro: pasta é cordofones
images:
  - file: "media/cordofones/berimbau/nao_existe.jpg"
related_instruments:
  - slug: "instrumento-inexistente"
    title: "Inexistente"
    family: "membranofones"
---
# Berimbau
Menção a [Inexistente](/instrumentos/outro-inexistente).
""", encoding="utf-8")

    all_slugs = {"berimbau": {"family": "cordofones", "path": str(md_file)}}
    issues = check_instrument_content(md_file, all_slugs, public_dir)
    
    error_messages = [i.message for i in issues if i.severity == "error"]
    assert any("title" in msg for msg in error_messages)
    assert any("diverge da pasta" in msg for msg in error_messages)
    assert any("não encontrado em" in msg for msg in error_messages)
    assert any("não encontrado no catálogo" in msg for msg in error_messages)
    assert any("aponta para slug inexistente" in msg for msg in error_messages)

    # Test markdown report generation
    report = generate_markdown_report(1, issues)
    assert "Validação de Integridade do Acervo" in report
    assert "Inconformidades (bloqueantes)" in report
    assert "Ação necessária" in report


def test_validate_invalid_yaml(tmp_path: Path):
    inst_dir = tmp_path / "web" / "src" / "content" / "instruments" / "membranofones"
    inst_dir.mkdir(parents=True)
    public_dir = tmp_path / "web" / "public"

    md_file = inst_dir / "zabumba.md"
    md_file.write_text("""---
title: "Zabumba"
family: [ unclosed list
---
""", encoding="utf-8")

    issues = check_instrument_content(md_file, {}, public_dir)
    errors = [i for i in issues if i.severity == "error"]
    assert len(errors) == 1
    assert "Erro de sintaxe YAML" in errors[0].message
