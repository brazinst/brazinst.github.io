import os
import shutil
import re
import sys
from pathlib import Path
import yaml
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.common import log, atomic_write_text, StateManager

def fix_tmp_files(root_dir: Path):
    backup_dir = root_dir / "backup_full"
    content_dir = root_dir / "content_brazinst"
    state_file = backup_dir / "state.json"
    
    state = StateManager(state_file)
    tmp_files = list(backup_dir.rglob("*.tmp"))
    log(f"Encontrados {len(tmp_files)} arquivos temporários (.tmp) para resolução...")

    fixed_count = 0

    for tmp in tmp_files:
        dest_name = tmp.stem  # remove .tmp
        parent = tmp.parent
        dest = parent / dest_name

        # Encontrar a URL correspondente no state
        url_match = None
        for u, f in list(state.data.get("failed", {}).items()):
            if dest_name in u:
                url_match = u
                break

        if dest.is_dir():
            # Salvar como original dentro da pasta do objeto
            final_dest = dest / f"original{dest.suffix}"
            shutil.move(str(tmp), str(final_dest))
            fixed_count += 1
            log(f"Resolvido conflito: {tmp.name} -> {final_dest.relative_to(root_dir)}", "SUCCESS")
            
            # Se for imagem do Brazinst, copiar também para content_brazinst/media
            if "acervo-brazinst" in str(final_dest):
                link_to_brazinst_content(root_dir, final_dest)

            if url_match:
                state.mark_completed(
                    url_match,
                    str(final_dest.relative_to(backup_dir)),
                    final_dest.stat().st_size,
                    http_code=200,
                    content_type="image/jpeg"
                )
        else:
            shutil.move(str(tmp), str(dest))
            fixed_count += 1
            log(f"Renomeado: {tmp.name} -> {dest.relative_to(root_dir)}", "SUCCESS")
            if url_match:
                state.mark_completed(
                    url_match,
                    str(dest.relative_to(backup_dir)),
                    dest.stat().st_size,
                    http_code=200
                )

    log(f"Total de {fixed_count} arquivos .tmp restaurados com sucesso!", "SUCCESS")

def link_to_brazinst_content(root_dir: Path, img_file: Path):
    content_dir = root_dir / "content_brazinst"
    parts = img_file.parts
    
    # Identificar família e instrumento
    # ex: backup_full/labeet/contents/paginas/acervo-brazinst/copy_of_cordofones/berimbau-de-barriga/...
    family = None
    instrument_slug = None

    for idx, p in enumerate(parts):
        if p.startswith("copy_of_"):
            candidate_fam = p.replace("copy_of_", "").lower()
            if candidate_fam in ("idiofones", "membranofones", "cordofones", "aerofones"):
                family = candidate_fam
                if idx + 1 < len(parts):
                    instrument_slug = parts[idx + 1]
                    break

    if family and instrument_slug:
        # normalizar slug
        clean_slug = re.sub(r'[^\w\-_]', '_', instrument_slug).lower()
        target_media_dir = content_dir / "media" / family / clean_slug
        target_media_dir.mkdir(parents=True, exist_ok=True)
        target_file = target_media_dir / img_file.name

        shutil.copy2(str(img_file), str(target_file))
        log(f"Foto preservada no acervo limpo: {target_file.relative_to(root_dir)}", "INFO")

        # Atualizar markdown do instrumento se existir
        inst_md_dir = content_dir / "instruments" / family
        for md_path in inst_md_dir.glob("*.md"):
            if md_path.stem == clean_slug or md_path.stem == instrument_slug:
                try:
                    text = md_path.read_text(encoding="utf-8")
                    content_parts = text.split("---")
                    if len(content_parts) >= 3:
                        meta = yaml.safe_load(content_parts[1])
                        images = meta.get("images", [])
                        rel_target = str(target_file.relative_to(content_dir))
                        if not any(img.get("file") == rel_target for img in images):
                            images.append({
                                "file": rel_target,
                                "caption": img_file.parent.name
                            })
                            meta["images"] = images
                            new_text = f"---\n{yaml.dump(meta, allow_unicode=True, sort_keys=False)}---{content_parts[2]}"
                            atomic_write_text(md_path, new_text)
                            log(f"Frontmatter atualizado em {md_path.name} com a nova foto!", "SUCCESS")
                except Exception as e:
                    log(f"Aviso ao atualizar frontmatter de {md_path}: {e}", "WARN")

def main():
    root_dir = Path(__file__).resolve().parent.parent
    fix_tmp_files(root_dir)

    # Re-executar validação
    backup_dir = root_dir / "backup_full"
    content_dir = root_dir / "content_brazinst"
    report_file = content_dir / "inventory_report.md"

    from scripts.validate import generate_inventory_report
    generate_inventory_report(backup_dir, content_dir, report_file)

if __name__ == "__main__":
    main()
