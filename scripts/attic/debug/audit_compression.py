import os
import re
import csv
import json
import shutil
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DESKTOP = Path.home() / "Desktop"

MATCH_TABLE_FILE = BASE_DIR / "match_table.txt"
OUTPUT_DIR = BASE_DIR / "video_audit_result"

SEARCH_ROOTS = [
    BASE_DIR,
    DESKTOP,
]

VIDEO_EXTENSIONS = {
    ".mp4", ".mts", ".mov", ".avi", ".mkv", ".m4v", ".wmv", ".flv", ".mpeg", ".mpg"
}

COMPRESSED_MARKERS = [
    "compress",
    "compressed",
    "_compressed",
    "-compressed",
    " compress ",
    " - compress",
]

def normalize_name(name: str) -> str:
    name = name.strip().strip('"').strip("'")
    return Path(name).stem.lower().strip()

def canonical_name(name: str) -> str:
    """
    Убираем признаки compressed из имени,
    чтобы сравнивать варианты одного и того же ролика.
    """
    s = normalize_name(name)

    patterns = [
        r'[_\-\s]*compressed\b',
        r'[_\-\s]*compress\b',
        r'\bcompress[_\-\s]*\d+\b',
        r'\bcompressed[_\-\s]*\d+\b',
    ]
    for p in patterns:
        s = re.sub(p, '', s, flags=re.IGNORECASE)

    s = re.sub(r'\s+', ' ', s).strip()
    s = re.sub(r'[_\-]+$', '', s).strip()
    return s

def is_video_file(filename: str) -> bool:
    return Path(filename).suffix.lower() in VIDEO_EXTENSIONS

def contains_compressed_marker(text: str) -> bool:
    low = text.lower()
    return any(marker in low for marker in COMPRESSED_MARKERS)

def find_ffprobe():
    ffprobe = shutil.which("ffprobe")
    if ffprobe:
        return ffprobe

    common_paths = [
        r"C:\ffmpeg\bin\ffprobe.exe",
        r"C:\Program Files\ffmpeg\bin\ffprobe.exe",
        r"C:\Program Files (x86)\ffmpeg\bin\ffprobe.exe",
    ]
    for p in common_paths:
        if os.path.exists(p):
            return p
    return None

FFPROBE = find_ffprobe()

def probe_video(path: str):
    """
    Возвращает duration, width, height, bitrate_kbps.
    Если ffprobe нет — вернет None-поля.
    """
    result = {
        "duration_sec": None,
        "width": None,
        "height": None,
        "bitrate_kbps": None
    }

    if not FFPROBE:
        return result

    try:
        cmd = [
            FFPROBE,
            "-v", "error",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            path
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")
        if proc.returncode != 0:
            return result

        data = json.loads(proc.stdout)

        fmt = data.get("format", {})
        streams = data.get("streams", [])

        if "duration" in fmt:
            try:
                result["duration_sec"] = round(float(fmt["duration"]), 2)
            except:
                pass

        if "bit_rate" in fmt:
            try:
                result["bitrate_kbps"] = round(int(fmt["bit_rate"]) / 1000, 2)
            except:
                pass

        video_stream = None
        for s in streams:
            if s.get("codec_type") == "video":
                video_stream = s
                break

        if video_stream:
            result["width"] = video_stream.get("width")
            result["height"] = video_stream.get("height")

        return result
    except:
        return result

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
                    "normalized_name": norm,
                    "canonical_name": canonical_name(raw_name),
                })
                seen.add(norm)

    return expected

def scan_all_files(search_roots):
    files = []
    for root in search_roots:
        if not root.exists():
            print(f"[WARN] Не существует путь: {root}")
            continue

        print(f"[INFO] Сканирую: {root}")

        for dirpath, _, filenames in os.walk(root):
            for filename in filenames:
                if not is_video_file(filename):
                    continue

                fullpath = os.path.join(dirpath, filename)
                p = Path(fullpath)

                try:
                    size_bytes = p.stat().st_size
                except:
                    size_bytes = None

                files.append({
                    "fullpath": fullpath,
                    "filename": p.name,
                    "stem_norm": normalize_name(p.name),
                    "canonical": canonical_name(p.name),
                    "size_bytes": size_bytes,
                    "size_mb": round(size_bytes / (1024 * 1024), 2) if size_bytes is not None else None,
                    "has_compressed_marker": contains_compressed_marker(fullpath),
                })

    return files

def write_csv(filepath: Path, rows: list, fieldnames: list):
    with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

def classify_candidate(candidate, group_files):
    """
    Логика:
    1) Если в имени/пути есть compress/compressed -> likely_compressed
    2) Если среди файлов той же canonical-группы этот самый большой
       и в имени нет compressed -> likely_original
    3) Иначе uncertain
    """
    reason = []
    status = "uncertain"

    if candidate["has_compressed_marker"]:
        status = "likely_compressed"
        reason.append("marker_in_name_or_path")

    sizes = [f["size_bytes"] for f in group_files if f["size_bytes"] is not None]
    max_size = max(sizes) if sizes else None

    if max_size is not None and candidate["size_bytes"] is not None:
        if candidate["size_bytes"] == max_size and not candidate["has_compressed_marker"]:
            status = "likely_original"
            reason.append("largest_in_group_no_compressed_marker")
        elif candidate["size_bytes"] < max_size and not candidate["has_compressed_marker"]:
            if status != "likely_compressed":
                status = "uncertain"
            reason.append("smaller_than_other_variant")

    return status, ";".join(reason) if reason else "no_clear_signal"

def main():
    if not MATCH_TABLE_FILE.exists():
        print(f"[ERROR] Не найден файл: {MATCH_TABLE_FILE}")
        return

    OUTPUT_DIR.mkdir(exist_ok=True)

    expected = load_expected_names(MATCH_TABLE_FILE)
    print(f"[INFO] В match_table уникальных видео: {len(expected)}")

    all_files = scan_all_files(SEARCH_ROOTS)
    print(f"[INFO] Всего видеофайлов найдено: {len(all_files)}")

    exact_index = {}
    canonical_index = {}

    for f in all_files:
        exact_index.setdefault(f["stem_norm"], []).append(f)
        canonical_index.setdefault(f["canonical"], []).append(f)

    found_rows = []
    missing_rows = []

    count_likely_original = 0
    count_likely_compressed = 0
    count_uncertain = 0

    for item in expected:
        raw_name = item["raw_name"]
        norm = item["normalized_name"]
        canon = item["canonical_name"]

        exact_matches = exact_index.get(norm, [])
        canon_group = canonical_index.get(canon, [])

        if not exact_matches:
            missing_rows.append({
                "match_table_name": raw_name,
                "normalized_name": norm,
                "canonical_name": canon,
                "canonical_group_variants_found": len(canon_group)
            })
            continue

        for m in exact_matches:
            meta = probe_video(m["fullpath"])
            status, reason = classify_candidate(m, canon_group)

            if status == "likely_original":
                count_likely_original += 1
            elif status == "likely_compressed":
                count_likely_compressed += 1
            else:
                count_uncertain += 1

            found_rows.append({
                "match_table_name": raw_name,
                "matched_filename": m["filename"],
                "matched_path": m["fullpath"],
                "size_mb": m["size_mb"],
                "duration_sec": meta["duration_sec"],
                "width": meta["width"],
                "height": meta["height"],
                "bitrate_kbps": meta["bitrate_kbps"],
                "compressed_marker_in_name_or_path": m["has_compressed_marker"],
                "same_canonical_group_count": len(canon_group),
                "compression_status": status,
                "reason": reason
            })

    found_csv = OUTPUT_DIR / "audit_found_videos.csv"
    missing_csv = OUTPUT_DIR / "audit_missing_videos.csv"
    summary_txt = OUTPUT_DIR / "audit_summary.txt"

    write_csv(
        found_csv,
        found_rows,
        [
            "match_table_name",
            "matched_filename",
            "matched_path",
            "size_mb",
            "duration_sec",
            "width",
            "height",
            "bitrate_kbps",
            "compressed_marker_in_name_or_path",
            "same_canonical_group_count",
            "compression_status",
            "reason"
        ]
    )

    write_csv(
        missing_csv,
        missing_rows,
        [
            "match_table_name",
            "normalized_name",
            "canonical_name",
            "canonical_group_variants_found"
        ]
    )

    total_expected = len(expected)
    total_found_matches = len(found_rows)
    total_missing = len(missing_rows)

    with open(summary_txt, "w", encoding="utf-8") as f:
        f.write(f"Всего видео в match_table: {total_expected}\n")
        f.write(f"Всего найденных совпадений: {total_found_matches}\n")
        f.write(f"Не найдено: {total_missing}\n")
        f.write("\nКлассификация найденных:\n")
        f.write(f"likely_original: {count_likely_original}\n")
        f.write(f"likely_compressed: {count_likely_compressed}\n")
        f.write(f"uncertain: {count_uncertain}\n")
        f.write("\nПримечание:\n")
        f.write("Это эвристика. 100% точность невозможна, если compressed был перезаписан тем же именем.\n")

    print("\n===== ГОТОВО =====")
    print(f"Результаты: {OUTPUT_DIR}")
    print(f"Найдено совпадений: {total_found_matches}")
    print(f"Не найдено: {total_missing}")
    print(f"likely_original: {count_likely_original}")
    print(f"likely_compressed: {count_likely_compressed}")
    print(f"uncertain: {count_uncertain}")

if __name__ == "__main__":
    main()