"""
Мастер-раннер: полный пайплайн для одного или всех кодексов.

Запускает последовательно:
    1. 01_build_article_map.py        статья → якорь
    2. 07_add_subpoint_anchors.py     якоря пунктов/подпунктов
    3. 10_cross_code_refs.py          cross-code ссылки (статья N Налогового кодекса)
    4. 02_fix_internal_links.py       внутренние ссылки (статья N настоящего Кодекса)
    5. 03_find_external_npa.py        голые названия НПА
    6. 06_finalize.py                 CSS/JS подсветка
    7. 13_cleanup_html.py             чистка вложенных <a>
    8. 76_mapping_gap_report.py       gap-отчёт маппинга (ОБЯЗАТЕЛЕН перед сдачей)

Использование:
    python scripts/pipeline/pipeline.py socialnyy          # один кодекс
    python scripts/pipeline/pipeline.py --all              # все кодексы из codes.json
    python scripts/pipeline/pipeline.py socialnyy --keep   # не удалять промежуточные файлы
    python scripts/pipeline/pipeline.py socialnyy --verify-only
        # read-only: только шаг 8 (76_mapping_gap_report), финальные файлы не трогаются
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

# Дочерние процессы должны выводить UTF-8, чтобы кириллица не падала на
# консолях с кодовой страницей cp1251 (стандартная Windows RU).
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


SCRIPTS = Path(__file__).resolve().parent

sys.path.insert(0, str(SCRIPTS.parent))
import paths

ROOT = paths.ROOT


def load_codes():
    with open(paths.CODES_JSON, encoding="utf-8") as f:
        cfg = json.load(f)
    return {k: v for k, v in cfg.items() if not k.startswith("_")}


def run(cmd, label):
    """Запускает скрипт; на ошибке прерывает пайплайн."""
    print(f"\n>> {label}")
    print(f"  $ {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=ROOT)
    if result.returncode != 0:
        print(f"  [FAIL] Ошибка на шаге '{label}' (код {result.returncode})")
        sys.exit(result.returncode)


def process_code(key, doc_id, keep=False, verify_only=False):
    py = sys.executable

    print(f"\n{'='*60}\n  {key.upper()}  doc_id={doc_id}\n{'='*60}")

    if verify_only:
        # read-only смоук: только gap-гейт по уже существующим финальным файлам
        run([py, str(SCRIPTS / "76_mapping_gap_report.py"), "--doc", key],
            "76_mapping_gap_report (verify-only)")
        return True

    src = paths.SOURCE / f"{key}.html"
    if not src.exists():
        print(f"[skip] Исходный файл не найден: {src}")
        return False

    maps = paths.MAPS
    final = paths.FINAL
    reports = paths.REPORTS
    for d in (maps, final, reports):
        d.mkdir(parents=True, exist_ok=True)

    art_map = maps / f"article_map_{key}.json"
    subp_map = maps / f"subpoint_map_{key}.json"

    interm = paths.INTERM
    interm.mkdir(parents=True, exist_ok=True)
    anchored = interm / f"{key}_anchored.html"
    xref     = interm / f"{key}_xref.html"
    fixed    = interm / f"{key}_fixed.html"
    npaed    = interm / f"{key}_npa.html"
    final_h  = final  / f"{key}_ready.html"
    report   = reports / f"report_{key}.csv"

    # 1. Article map
    run([py, str(SCRIPTS / "01_build_article_map.py"),
         "--input", str(src), "--output", str(art_map)],
        "01_build_article_map")

    # 2. Subpoint anchors
    run([py, str(SCRIPTS / "07_add_subpoint_anchors.py"),
         "--input", str(src), "--map", str(art_map),
         "--output", str(anchored),
         "--subpoint-map-output", str(subp_map)],
        "07_add_subpoint_anchors")

    # 3. Cross-code refs (combined links)
    run([py, str(SCRIPTS / "10_cross_code_refs.py"),
         "--input", str(anchored),
         "--output", str(xref),
         "--codes-config", str(paths.CODES_JSON),
         "--npa-map", str(paths.NPA_MAPPING),
         "--maps-dir", str(maps)],
        "10_cross_code_refs")

    # 4. Internal links (article N настоящего Кодекса)
    run([py, str(SCRIPTS / "02_fix_internal_links.py"),
         "--input", str(xref),
         "--map", str(art_map),
         "--subpoint-map", str(subp_map),
         "--doc-id", doc_id,
         "--output", str(fixed),
         "--report", str(report)],
        "02_fix_internal_links")

    # 5. External NPA names
    run([py, str(SCRIPTS / "03_find_external_npa.py"),
         "--input", str(fixed),
         "--npa-map", str(paths.NPA_MAPPING),
         "--output-html", str(npaed)],
        "03_find_external_npa")

    # 6. Finalize (CSS/JS)
    run([py, str(SCRIPTS / "06_finalize.py"),
         "--input", str(npaed),
         "--output", str(final_h)],
        "06_finalize")

    # 7. Cleanup (flatten nested <a>, normalize)
    run([py, str(SCRIPTS / "13_cleanup_html.py"),
         "--input", str(final_h),
         "--output", str(final_h)],
        "13_cleanup_html")

    # 8. Gap-отчёт маппинга — ОБЯЗАТЕЛЕН перед сдачей: plain/разорванные
    # правовые фразы + дыры npa_mapping (отчёт, пайплайн не прерывает)
    run([py, str(SCRIPTS / "76_mapping_gap_report.py"), "--doc", key],
        "76_mapping_gap_report")

    if not keep:
        for p in (anchored, xref, fixed, npaed):
            if p.exists():
                p.unlink()
        # Очищаем пустую папку interm если в ней ничего не осталось
        if interm.exists() and not any(interm.iterdir()):
            interm.rmdir()

    return True


def main():
    ap = argparse.ArgumentParser(description="Мастер-раннер полного пайплайна")
    ap.add_argument("code", nargs="?", help="Ключ кодекса (socialnyy, nalog, ...)")
    ap.add_argument("--all", action="store_true", help="Прогнать все кодексы из codes.json")
    ap.add_argument("--keep", action="store_true", help="Сохранить промежуточные файлы")
    ap.add_argument("--verify-only", action="store_true",
                    help="Read-only: только gap-гейт (шаг 8), без перестроения")
    args = ap.parse_args()

    codes = load_codes()
    if args.all:
        targets = codes.items()
    elif args.code:
        if args.code not in codes:
            print(f"Неизвестный код: {args.code}. Доступны: {sorted(codes)}")
            sys.exit(1)
        targets = [(args.code, codes[args.code])]
    else:
        ap.print_help()
        sys.exit(1)

    ok = 0
    for key, info in targets:
        if process_code(key, info["doc_id"], keep=args.keep,
                        verify_only=args.verify_only):
            ok += 1
    print(f"\n[OK] Готово: {ok}/{len(list(targets) if args.all else [args.code])} кодексов")


if __name__ == "__main__":
    main()
