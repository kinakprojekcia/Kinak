"""
Konverzia .txt suborov na UTF-8 (bez BOM)
==========================================
Automaticky rozpozna, ci je subor uz v UTF-8, alebo v ANSI (Windows-1250),
a podla toho ho spravne prevedie. Vysledok je vzdy ciste UTF-8 bez BOM.

Potrebuje: Python 3 (staci standardna instalacia, ziadne extra kniznice)
"""

import shutil
from pathlib import Path

# Uprav cestu, ak su tvoje subory inde
FOLDER = Path(r"C:\Kinak\piesne")


def read_text_auto(path: Path):
    """Precita subor a vrati (text, nazov_povodneho_kodovania)."""
    raw = path.read_bytes()

    # UTF-8 s BOM
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw.decode("utf-8-sig"), "UTF-8 (s BOM)"

    # Skus cisty UTF-8
    try:
        text = raw.decode("utf-8")
        return text, "UTF-8"
    except UnicodeDecodeError:
        pass

    # Inak predpokladame ANSI = Windows-1250 (stredoeuropske Windows)
    text = raw.decode("cp1250")
    return text, "ANSI (Windows-1250)"


def main():
    if not FOLDER.exists():
        print(f"Priecinok '{FOLDER}' neexistuje. Skontroluj cestu.")
        return

    backup_folder = FOLDER / "_zaloha_original"
    backup_folder.mkdir(exist_ok=True)

    files = sorted(FOLDER.glob("*.txt"))
    total = len(files)
    print(f"Najdenych {total} suborov.\n")

    stats = {}
    chyby = []

    for i, file in enumerate(files, start=1):
        try:
            text, detected = read_text_auto(file)
            stats[detected] = stats.get(detected, 0) + 1

            # zaloha originalu (raw bajty, nezmenene)
            shutil.copy2(file, backup_folder / file.name)

            # zapis vzdy ako ciste UTF-8 bez BOM, newline='' aby sa
            # nezdvojili konce riadkov
            with open(file, "w", encoding="utf-8", newline="") as f:
                f.write(text)

            print(f"[{i}/{total}] {file.name}  (bolo: {detected})")

        except Exception as e:
            chyby.append((file.name, str(e)))
            print(f"[{i}/{total}] CHYBA pri {file.name}: {e}")

    print("\nZhrnutie povodnych kodovani:")
    for k, v in stats.items():
        print(f"  {k}: {v} suborov")

    print(f"\nHotovo! Vsetky subory su teraz v UTF-8 (bez BOM).")
    print(f"Originaly su zalohovane v: {backup_folder}")

    if chyby:
        print(f"\nSubory s chybou pri spracovani ({len(chyby)}):")
        for name, err in chyby:
            print(f"  - {name}: {err}")


if __name__ == "__main__":
    main()
