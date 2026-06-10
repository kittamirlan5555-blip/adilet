import os
import csv
from pathlib import Path

# ===== НАСТРОЙКИ =====
BASE_DIR = Path(__file__).resolve().parent
DESKTOP = Path.home() / "Desktop"

POSSIBLE_MATCH_FILES = [
    BASE_DIR / "match_table.txt",
    DESKTOP / "match_table.txt",
]

SEARCH_ROOTS = [
    BASE_DIR,      # папка проекта ADILETkz
    DESKTOP,       # рабочий стол
]

OUTPUT_DIR = BASE_DIR / "video_check_result"

VIDEO_EXTENSIONS = {
    ".mp4", ".mts", ".mov", ".avi", ".mkv", ".m4v", ".wmv", ".flv", ".mpeg", ".mpg"
}

COMPRESSED_MARKERS = [
    "compress",
    "compressed",
]

def find_match_table():
    for path in POSSIBLE_MATCH_FILES:
        if path.exists():
            return path
    return None

def normalize_name(name: str) -> str:
    name = name.strip().strip('"').strip("'")
    stem = Path(name).stem
    return stem.lower().strip()

def is_video_file(filename: str) -> bool:
    return Path(filename).suffix.lower() in VIDEO_EXTENSIONS

def is_compressed_path(path_str: str) -> bool:
    low = path_str.lower()
    return any(marker in low for marker in COMPRESSED_MARKERS)

def load_expected_names(match_table_file: Path):
    expected = []
    seen = set()

    with open(match_table_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            parts = line.split("\t")
            raw_name = parts[0].strip()

            if not raw_name:
                continue

            norm = normalize_name(raw_name)
            if norm not in seen:
                expected.append({
                    "raw_name": raw_name,
                    "normalized_name": norm
                })
                seen.add(norm)

    return expected

def index_files(search_roots):
    index = {}

    for root in search_roots:
        if not root.exists():
            print(f"[WARN] Не существует путь: {root}")
            continue

        print(f"[INFO] Сканирую: {root}")

        for dirpath, dirnames, filenames in os.walk(root):
            if is_compressed_path(dirpath):
                dirnames[:] = []
                continue

            for filename in filenames:
                if not is_video_file(filename):
                    continue

                fullpath = os.path.join(dirpath, filename)

                if is_compressed_path(fullpath):
                    continue

                norm = normalize_name(filename)
                index.setdefault(norm, []).append(fullpath)

    return index

def write_csv(filepath: Path, rows: list, fieldnames: list):
    with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

def main():
    match_table_file = find_match_table()

    if not match_table_file:
        print("[ERROR] Файл match_table.txt не найден.")
        print("Создай его и положи либо:")
        print(f"  1) сюда: {BASE_DIR}")
        print(f"  2) либо сюда: {DESKTOP}")
        return

    print(f"[INFO] Использую match table: {match_table_file}")

    OUTPUT_DIR.mkdir(exist_ok=True)

    expected = load_expected_names(match_table_file)
    print(f"[INFO] В матч-таблице уникальных видео: {len(expected)}")

    index = index_files(SEARCH_ROOTS)
    print(f"[INFO] Уникальных видео-имен найдено: {len(index)}")

    found_rows = []
    missing_rows = []

    for item in expected:
        raw_name = item["raw_name"]
        norm = item["normalized_name"]
        matches = index.get(norm, [])

        if matches:
            found_rows.append({
                "match_table_name": raw_name,
                "normalized_name": norm,
                "found_count": len(matches),
                "found_paths": " | ".join(matches)
            })
        else:
            missing_rows.append({
                "match_table_name": raw_name,
                "normalized_name": norm
            })

    found_count = len(found_rows)
    missing_count = len(missing_rows)
    total_count = len(expected)

    found_csv = OUTPUT_DIR / "found_videos.csv"
    missing_csv = OUTPUT_DIR / "missing_videos.csv"
    summary_txt = OUTPUT_DIR / "summary.txt"

    write_csv(
        found_csv,
        found_rows,
        ["match_table_name", "normalized_name", "found_count", "found_paths"]
    )

    write_csv(
        missing_csv,
        missing_rows,
        ["match_table_name", "normalized_name"]
    )

    with open(summary_txt, "w", encoding="utf-8") as f:
        f.write(f"Всего видео из матч-таблицы: {total_count}\n")
        f.write(f"Найдено: {found_count}\n")
        f.write(f"Не найдено: {missing_count}\n")

    print("\n===== ГОТОВО =====")
    print(f"Всего видео из матч-таблицы: {total_count}")
    print(f"Найдено: {found_count}")
    print(f"Не найдено: {missing_count}")
    print(f"Результаты сохранены в: {OUTPUT_DIR}")

if __name__ == "__main__":
    main()