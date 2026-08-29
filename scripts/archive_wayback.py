import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
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


def archive_all_urls(state_file: Path, output_file: Path, delay: float = 2.0) -> None:
    state = StateManager(state_file)
    session = requests.Session()
    urls = list(state.data.get("visited", {}).keys())
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
    root_dir = Path(__file__).resolve().parent.parent
    st = root_dir / "backup_full" / "state.json"
    out = root_dir / "content_brazinst" / "wayback_archive.md"
    archive_all_urls(st, out)
