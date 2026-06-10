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

Использование:
    python scripts/run_pipeline.py socialnyy          # один кодекс
    python scripts/run_pipeline.py --all              # все кодексы из codes.json
    python scripts/run_pipeline.py socialnyy --keep   # не удалять промежуточные файлы
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
ROOT = SCRIPTS.parent


def load_codes():
    with open(ROOT / "config" / "codes.json", encoding="utf-8") as f:
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


def process_code(key, doc_id, keep=False):
    py = sys.executable
    src = ROOT / "data" / "source" / f"{key}.html"
    if not src.exists():
        print(f"[skip] Исходный файл не найден: {src}")
        return False

    print(f"\n{'='*60}\n  {key.upper()}  doc_id={doc_id}\n{'='*60}")

    maps = ROOT / "data" / "maps"
    final = ROOT / "data" / "final"
    reports = ROOT / "data" / "reports"
    for d in (maps, final, reports):
        d.mkdir(parents=True, exist_ok=True)

    art_map = maps / f"article_map_{key}.json"
    subp_map = maps / f"subpoint_map_{key}.json"

    interm = ROOT / "data" / "interm"
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
         "--codes-config", str(ROOT / "config" / "codes.json"),
         "--npa-map", str(ROOT / "config" / "npa_mapping.json"),
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
         "--npa-map", str(ROOT / "config" / "npa_mapping.json"),
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
        if process_code(key, info["doc_id"], keep=args.keep):
            ok += 1
    print(f"\n[OK] Готово: {ok}/{len(list(targets) if args.all else [args.code])} кодексов")


if __name__ == "__main__":
    main()
