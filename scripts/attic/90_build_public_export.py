# -*- coding: utf-8 -*-
"""Сборка ЧИСТОГО публичного экспорта репозитория ADILETkz.

НИЧЕГО не удаляет и не меняет в рабочем дереве. Создаёт sibling-папку
<Desktop>/adilet_public со структурой ready/ maps/ scripts/ source/ docs/.
Канонический скрипт 02 копируется с РЕДАКЦИЕЙ внутреннего IP.
В конце — сквозной анти-IP свип всего экспорта (падает, если что-то осталось).
"""
import json
import shutil
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT.parent / "adilet_public"
FINAL = ROOT / "data" / "final"

IP_RE = re.compile(r"85\.202\.192\.66(?::\d+)?")

LAW_KEYS = ["informatizacii", "notariat", "obrazovanie", "arbitrazh",
            "goszakup", "ocorrupt", "bezhenci", "zhilishniy"]

CANON_SCRIPTS = [
    "11_structure_html.py", "01_build_article_map.py", "07_add_subpoint_anchors.py",
    "02_fix_internal_links.py", "68_link_canon.py", "71_fullspan_wrap.py",
    # хвост §8: автоматизация ручной до-линковки (внешние акты, цепочки, свежесть кодов,
    # cross-code сверка). Read-only/инвентарь по умолчанию; --apply гейтится отдельно.
    "72_external_root_link.py", "73_fullspan_chains.py",
    "74_code_freshness_check.py", "75_crosscode_verify.py",
    "audit_links_coverage.py", "67_independent_verify.py", "64_final_verify.py",
    "69_sixcheck_laws.py", "chunk_npa.py",
]

# Синтетические юнит-тесты для скриптов 72-75 (не зависят от data/final).
TEST_FILES = ["test_link_scripts.py", "__init__.py"]

SOURCE_TXT = [
    "RAW_Word_Анары_все_кодексы.txt", "RAW_Excel_ТК.txt", "RAW_Excel_УК.txt",
]


def fresh(p):
    p.mkdir(parents=True, exist_ok=True)


def main():
    if OUT.exists():
        # пересобираем содержимое, но НЕ трогаем .git и РУЧНЫЕ файлы репо (README.md):
        # README.md ведётся вручную в публичном репо и НЕ генерится экспортом —
        # без этого исключения пересборка его бы стирала.
        PRESERVE = {".git", "README.md"}
        for child in OUT.iterdir():
            if child.name in PRESERVE:
                continue
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()
    fresh(OUT)
    log = []

    # ---- ready/codes : все *_ready.html (это кодексы) ----
    fresh(OUT / "ready" / "codes")
    code_ready = sorted(FINAL.glob("*_ready.html"))
    for f in code_ready:
        shutil.copy2(f, OUT / "ready" / "codes" / f.name)
    log.append(f"ready/codes: {len(code_ready)} файлов")

    # ---- ready/laws : *_structured.html для законов ----
    fresh(OUT / "ready" / "laws")
    nlaw = 0
    for k in LAW_KEYS:
        src = FINAL / f"{k}_structured.html"
        if src.exists():
            shutil.copy2(src, OUT / "ready" / "laws" / src.name)
            nlaw += 1
        else:
            log.append(f"  ! law missing: {src.name}")
    log.append(f"ready/laws: {nlaw} файлов (форма _structured = каноническая для законов)")

    # ---- maps : npa_mapping + codes + overrides + все article/subpoint maps ----
    fresh(OUT / "maps")
    for rel in ("config/npa_mapping.json", "config/codes.json",
                "config/manual_overrides.json"):
        shutil.copy2(ROOT / rel, OUT / "maps" / Path(rel).name)
    nmap = 0
    for f in sorted((ROOT / "data" / "maps").glob("*.json")):
        shutil.copy2(f, OUT / "maps" / f.name)
        nmap += 1
    log.append(f"maps: 3 config json + {nmap} anchor-map json")

    # ---- scripts : только канонические; 02 с редакцией IP ----
    fresh(OUT / "scripts")
    nsc = 0
    for name in CANON_SCRIPTS:
        src = ROOT / "scripts" / name
        if not src.exists():
            log.append(f"  ! script missing: {name}")
            continue
        text = src.read_text(encoding="utf-8")
        if IP_RE.search(text):
            text = IP_RE.sub("localhost:9096", text)
            log.append(f"  ~ redacted internal IP in {name}")
        (OUT / "scripts" / name).write_text(text, encoding="utf-8")
        nsc += 1
    log.append(f"scripts: {nsc} канонических")

    # ---- tests : синтетические юнит-тесты скриптов 72-75 (без data/final) ----
    fresh(OUT / "tests")
    ntest = 0
    for name in TEST_FILES:
        src = ROOT / "tests" / name
        if src.exists():
            shutil.copy2(src, OUT / "tests" / name)
            ntest += 1
        else:
            log.append(f"  ! test missing: {name}")
    log.append(f"tests: {ntest} файлов (синтетические, для скриптов 72-75)")

    # ---- source : текстовые выгрузки разметки Анары (IP-чистые) ----
    fresh(OUT / "source")
    nsrc = 0
    for name in SOURCE_TXT:
        src = ROOT / "brief" / name
        if src.exists():
            shutil.copy2(src, OUT / "source" / name)
            nsrc += 1
    log.append(f"source: {nsrc} текстовых выгрузок разметки Анары")

    # ---- docs : RUNBOOK + kit README ----
    fresh(OUT / "docs")
    shutil.copy2(ROOT / "law_kit" / "RUNBOOK.md", OUT / "docs" / "RUNBOOK.md")
    shutil.copy2(ROOT / "law_kit" / "README.md", OUT / "docs" / "pipeline_kit_README.md")
    log.append("docs: RUNBOOK.md + pipeline_kit_README.md")

    # ---- .gitignore ----
    (OUT / ".gitignore").write_text(
        "\n".join([
            "# secrets / creds", ".env", ".env.*", "secrets/", "credentials*",
            "*.key", "*.pem", "*.pfx", "*.p12", "id_rsa*", "*.ppk", "*.ovpn", "*.rdp",
            "", "# python", "__pycache__/", "*.pyc", "*.pyo", ".venv/", "venv/",
            "", "# node", "node_modules/",
            "", "# archives / dumps / scratch", "*.zip", "*.7z", "*.tar", "*.tar.gz",
            "tmp_*", "*~", ".DS_Store", "Thumbs.db", "",
        ]) + "\n", encoding="utf-8")
    log.append(".gitignore written")

    # ---- финальный анти-IP/секрет свип всего экспорта ----
    hits = []
    for f in OUT.rglob("*"):
        if not f.is_file() or f.suffix.lower() in (".zip", ".png", ".jpg", ".docx"):
            continue
        try:
            t = f.read_text(encoding="utf-8")
        except Exception:
            continue
        if IP_RE.search(t):
            hits.append(str(f.relative_to(OUT)))
    log.append("")
    log.append(f"ANTI-IP SWEEP: {'CLEAN (0 hits)' if not hits else 'HITS=' + repr(hits)}")
    assert not hits, f"IP leaked into export: {hits}"

    print("\n".join(log))
    print(f"\nEXPORT READY at: {OUT}")


if __name__ == "__main__":
    main()
