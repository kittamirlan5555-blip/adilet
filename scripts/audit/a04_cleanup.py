# -*- coding: utf-8 -*-
"""АУДИТ ФАЗА 4: карта живости scripts/ + мусор в корне и data/. READ-ONLY.

python scripts/audit/a04_cleanup.py
-> data/reports/audit/04_repo_cleanup.md

НИЧЕГО НЕ ПЕРЕМЕЩАЕТ — только предложение (исполнение после «ок» шефа).
Живость скрипта = упомянут в CLAUDE.md / README / RUNBOOK / brief|чеклистах /
импортируется тестами или другими скриптами / входит в публичный экспорт (90).
"""
import re
import sys
import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import auditlib as al

ROOT = al.ROOT
SCRIPTS = ROOT / "scripts"

# канонические доки: упоминание = скрипт ЖИВ (рабочая память/инструкции).
# scripts/README.md НЕ входит — это каталог всего подряд, не сигнал живости.
CANON_DOCS = [ROOT / "CLAUDE.md", ROOT / "README.md",
              ROOT / "law_kit" / "RUNBOOK.md", ROOT / "law_kit" / "README.md"]
# исторические доки: упоминание = след ПРОШЛЫХ раундов (не повод держать в scripts/)
HIST_DOCS = [ROOT / "brief" / "00_СОСТОЯНИЕ_И_ПЛАН.md",
             ROOT / "brief" / "HANDOFF_ADILETkz_Фаза2.md",
             ROOT / "ANARA_03_MASTER_CHECKLIST.md",
             ROOT / "master_anara_remarks_since_13_may.md"]


def _read_all(paths):
    out = ""
    for p in paths:
        if p.exists():
            out += p.read_text(encoding="utf-8", errors="replace") + "\n"
    return out


def main():
    canon = _read_all(CANON_DOCS)
    hist = _read_all(HIST_DOCS)
    # код, который может ссылаться на другие скрипты (вкл. экспорт 90 и тесты)
    code_refs = ""
    for p in list(SCRIPTS.glob("*.py")) + list((ROOT / "tests").glob("*.py")) \
             + list((SCRIPTS / "audit").glob("*.py")):
        code_refs += p.read_text(encoding="utf-8", errors="replace")

    keep, attic = [], []
    for p in sorted(SCRIPTS.glob("*.py")):
        name = p.name
        in_canon = name in canon
        in_code = code_refs.count(name) > 1          # >1: не только сам себя
        in_hist = name in hist
        size = p.stat().st_size
        mtime = datetime.datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d")
        if in_canon or in_code:
            keep.append((name, size, mtime, in_canon, in_code))
        else:
            attic.append((name, size, mtime, in_hist))

    L = ["# АУДИТ 04 — чистота репозитория (ПРЕДЛОЖЕНИЕ, не исполнение)", "",
         f"Генератор: scripts/audit/a04_cleanup.py, {datetime.date.today()}. "
         "Критерий «жив»: упомянут в КАНОНИЧЕСКИХ доках (CLAUDE.md, README, "
         "RUNBOOK) ИЛИ на него ссылается код (скрипты/тесты/экспорт 90). "
         "Упоминание только в brief/чеклистах = след прошлых раундов, не повод "
         "держать в scripts/.", "",
         f"## scripts/*.py: всего {len(keep) + len(attic)}, КАНОНИЧЕСКИХ {len(keep)}, "
         f"кандидатов в attic {len(attic)}", "",
         "### ОСТАВИТЬ в scripts/ (канонические)", "",
         "| скрипт | размер | mtime | в доках | в коде |", "|---|---|---|---|---|"]
    for name, size, mtime, in_canon, in_code in keep:
        L.append(f"| {name} | {size:,} | {mtime} | {'да' if in_canon else ''} "
                 f"| {'да' if in_code else ''} |")
    L += ["", "### Кандидаты в scripts/attic/ (git mv, НЕ удалять)", "",
          "Одноразовые фиксы под конкретный документ/раунд, диагностика, дубли. "
          "`git mv` сохраняет историю; ничего не теряется.", "",
          "| скрипт | размер | mtime | упомянут в истории раундов |", "|---|---|---|---|"]
    for name, size, mtime, in_hist in attic:
        L.append(f"| {name} | {size:,} | {mtime} | {'да' if in_hist else ''} |")

    # подпапки и коллизии
    L += ["", "## Коллизии нумерации и подпапки", "",
          "- ФАКТ: номер 70 занят ДВАЖДЫ (`70_zhilishniy_deadlinks.py` — разовый "
          "фикс, и `70_anara_flags_driver.py` — драйвер флагов УПК-раунда); номер "
          "71 тоже (`71_fullspan_wrap.py` — канонический §7 п.6, и `71_gates.py` — "
          "гейты УПК-раунда). Предложение: `70_zhilishniy_deadlinks.py` -> attic "
          "(работа сделана), `71_gates.py` -> переименовать в `77_gates.py`, "
          "`70_anara_flags_driver.py` -> `76_anara_flags_driver.py` (после «ок»).",
          f"- `scripts/debug/` ({len(list((SCRIPTS / 'debug').glob('*.py')))} файлов) — "
          "целиком кандидат в attic (разовая диагностика).",
          f"- `scripts/_upk*.py`, `scripts/_offmap.py`, `scripts/_uk_rebuild_map.py` — "
          "подчёркнутые временные скрипты УПК-раунда: в attic после закрытия раунда.",
          "- `law_kit/scripts/` — снапшот пайплайна для передачи (дубль 8 канонических "
          "скриптов): оставить как есть (это поставляемый kit, не мусор).", "",
          "## Корень и data/: лишнее/осиротевшее", "",
          "- `data/final_backup_*` (16 папок, ~150MB) — уже в .gitignore; на диске "
          "оставить до приёмки, потом можно унести в archive/.",
          "- `data/final_pre_links/`, `data/final_pre_fix11_zhilishniy_structured.html` — "
          "пре-снапшоты, тот же статус.",
          "- `data/reports/` (старые отчёты раундов, ~9MB) — исторические; трогать "
          "не предлагаю (на них ссылаются чеклисты).",
          "- `data/maps/article_map_ugolovniy_rebuilt.json` — рабочая копия рядом с "
          "канонической `article_map_ugolovniy.json`: после приёмки УК-раунда слить "
          "в одну (вопрос шефу).",
          "- `data/anara_package/`, `data/chunks/`, `data/tree/` — производные "
          "артефакты чанкера; перегенерируемы, оставить.",
          "- Корень: `ADILETkz_гиперссылки_2026-06-02.zip` (в .gitignore), "
          "`session-export-*.zip` в brief/ — локальные архивы, в репо не идут.", "",
          "## Что НЕ вошло в публичную ветку (локально, §11)", "",
          "- 22 скрипта/отчёта с внутренним IP (см. .git/info/exclude),",
          "- 4 source-страницы (grazhdanskiy/nalog/trudovoy/ugolovniy) с IP в href,",
          "- brief/ТЗ-01, brief/HANDOFF, 22 CSV-отчёта с IP,",
          "- anara_review/ (160MB docx, ПДн), archive/ (352MB).", ""]

    al.AUDIT_OUT.mkdir(parents=True, exist_ok=True)
    (al.AUDIT_OUT / "04_repo_cleanup.md").write_text("\n".join(L) + "\n",
                                                     encoding="utf-8")
    print(f"живых: {len(keep)}, в attic: {len(attic)} -> 04_repo_cleanup.md")
    for name, *_ in keep:
        print("  KEEP", name)


if __name__ == "__main__":
    main()
