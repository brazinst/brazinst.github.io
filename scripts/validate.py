import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from typing import Dict, Any
import yaml

from scripts.common import StateManager, atomic_write_text, log


def audit_content_integrity(content_dir: Path) -> Dict[str, Any]:
    instruments_dir = content_dir / "instruments"
    by_family: Dict[str, int] = {}
    total_insts = 0
    missing_media = []
    total_media_count = 0
    total_bytes = 0

    if instruments_dir.exists():
        for family_dir in sorted(instruments_dir.iterdir()):
            if family_dir.is_dir():
                count = 0
                for md_file in sorted(family_dir.glob("*.md")):
                    count += 1
                    total_insts += 1
                    total_bytes += md_file.stat().st_size
                    try:
                        content = md_file.read_text(encoding="utf-8")
                        parts = content.split("---")
                        if len(parts) >= 3:
                            meta = yaml.safe_load(parts[1])
                            if isinstance(meta, dict):
                                for img in meta.get("images", []):
                                    total_media_count += 1
                                    rel_path = img.get("file")
                                    if rel_path:
                                        expected_path = content_dir / rel_path
                                        if not expected_path.exists() or expected_path.stat().st_size == 0:
                                            missing_media.append(f"{md_file.name}: {rel_path}")
                                        else:
                                            total_bytes += expected_path.stat().st_size
                            else:
                                missing_media.append(f"Frontmatter inválido em {md_file.name}")
                        else:
                            missing_media.append(f"Frontmatter ausente em {md_file.name}")
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
    last_updated = state.data.get("last_updated") or "N/A"

    md = [
        "# Relatório Final de Inventário e Integridade — Preservação LABEET",
        f"\n**Data da Auditoria:** {last_updated}",
        "\n## 1. Resumo Geral",
        f"- **Páginas e arquivos salvos no espelho bruto:** {len(visited)}",
        f"- **Falhas no espelho bruto:** {len(failed)}",
        f"- **Total de instrumentos preservados no Brazil Instrumentarium:** {content_audit['total_instruments']}",
        f"- **Total de fotos preservadas:** {content_audit['total_media_count']}",
        f"- **Fotos ausentes/corrompidas:** {content_audit['missing_media_count']}",
        f"- **Espaço total em disco (dados limpos):** {content_audit['total_bytes_mb']} MB",
        "\n## 2. Instrumentos por Família Organológica"
    ]

    for fam, count in sorted(content_audit["instruments_by_family"].items()):
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
    root_dir = Path(__file__).resolve().parent.parent
    b_dir = root_dir / "backup_full"
    c_dir = root_dir / "content_brazinst"
    rep = c_dir / "inventory_report.md"
    generate_inventory_report(b_dir, c_dir, rep)
