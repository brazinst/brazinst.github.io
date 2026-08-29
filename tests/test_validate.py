from pathlib import Path
import json
from scripts.validate import audit_content_integrity, generate_inventory_report


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
    assert report["total_media_count"] == 1
    assert report["total_bytes_mb"] >= 0


def test_audit_content_integrity_missing_and_corrupt_media(tmp_path: Path):
    content_dir = tmp_path / "content_brazinst"
    inst_dir = content_dir / "instruments" / "cordofones"
    inst_dir.mkdir(parents=True)
    media_dir = content_dir / "media" / "cordofones" / "berimbau"
    media_dir.mkdir(parents=True)

    # 0-byte file (corrupted)
    zero_file = media_dir / "empty.jpg"
    zero_file.write_bytes(b"")

    md_file = inst_dir / "berimbau.md"
    md_file.write_text("""---
title: "Berimbau"
family: "cordofones"
images:
  - file: "media/cordofones/berimbau/empty.jpg"
  - file: "media/cordofones/berimbau/nonexistent.jpg"
---
# Berimbau
""", encoding="utf-8")

    # Also add an unparseable markdown file
    bad_md = inst_dir / "bad.md"
    bad_md.write_text("""---
invalid_yaml: [ unclosed list
---
""", encoding="utf-8")

    report = audit_content_integrity(content_dir)
    assert report["total_instruments"] == 2
    assert report["missing_media_count"] == 3  # 2 missing/empty images + 1 parse error
    assert any("empty.jpg" in item for item in report["missing_media_details"])
    assert any("nonexistent.jpg" in item for item in report["missing_media_details"])
    assert any("bad.md" in item for item in report["missing_media_details"])


def test_generate_inventory_report(tmp_path: Path):
    backup_dir = tmp_path / "backup_full"
    backup_dir.mkdir(parents=True)
    state_file = backup_dir / "state.json"
    state_file.write_text(json.dumps({
        "last_updated": "2026-08-29T18:00:00Z",
        "visited": {"http://example.com/1": {"status": "completed"}},
        "failed": {}
    }), encoding="utf-8")

    content_dir = tmp_path / "content_brazinst"
    inst_dir = content_dir / "instruments" / "idiofones"
    inst_dir.mkdir(parents=True)
    media_dir = content_dir / "media" / "idiofones" / "agogo"
    media_dir.mkdir(parents=True)
    img_file = media_dir / "img_01.jpg"
    img_file.write_bytes(b"image data")

    md_file = inst_dir / "agogo.md"
    md_file.write_text("""---
title: "Agogô"
family: "idiofones"
images:
  - file: "media/idiofones/agogo/img_01.jpg"
---
# Agogô
""", encoding="utf-8")

    report_file = content_dir / "inventory_report.md"
    generate_inventory_report(backup_dir, content_dir, report_file)

    assert report_file.exists()
    report_text = report_file.read_text(encoding="utf-8")
    assert "Relatório Final de Inventário e Integridade" in report_text
    assert "Idiofones:" in report_text
    assert "100% das imagens vinculadas foram baixadas" in report_text
