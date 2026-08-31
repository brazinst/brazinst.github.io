import shutil
from pathlib import Path

def sync():
    root = Path(__file__).resolve().parent.parent
    src_content = root / "content_brazinst" / "instruments"
    src_media = root / "content_brazinst" / "media"
    
    dest_content = root / "web" / "src" / "content" / "instruments"
    dest_media = root / "web" / "public" / "media"

    if src_content.exists():
        if dest_content.exists():
            shutil.rmtree(dest_content)
        dest_content.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(src_content, dest_content)
        print(f"Sincronizados verbetes para {dest_content}")
    else:
        print(f"[INFO] {src_content} não encontrado. Usando verbetes versionados em {dest_content}")

    if src_media.exists():
        if dest_media.exists():
            shutil.rmtree(dest_media)
        dest_media.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(src_media, dest_media)
        print(f"Sincronizadas mídias para {dest_media}")
    else:
        print(f"[INFO] {src_media} não encontrado. Usando mídias versionadas em {dest_media}")

if __name__ == "__main__":
    sync()
