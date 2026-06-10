# -*- coding: utf-8 -*-
"""Единая точка истины по путям проекта (дерево после Фазы A, см. MOVES.md).

Канонические скрипты обязаны брать пути отсюда:
    import sys; from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    import paths
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SOURCE = ROOT / "source"            # сырые HTML с adilet, read-only
FINAL = ROOT / "final"              # *_ready.html / *_structured.html
MAPS = ROOT / "maps"                # карты якорей + npa_mapping/codes/overrides
REPORTS = ROOT / "reports"          # аудиты, SDACHA, флаги, gap-отчёты
DELIVERABLES = ROOT / "deliverables"
CHUNKS = ROOT / "chunks"            # JSONL-чанки (производное chunk_npa)
TREE = ROOT / "tree"                # JSON-деревья (производное chunk_npa)
DOCS = ROOT / "docs"
AUDIT_OUT = REPORTS / "audit"
INTERM = ROOT / "interm"            # промежуточные файлы pipeline (удаляются без --keep)
BACKUPS = ROOT / "backups"          # бэкапы --apply-шагов (gitignore, в репо не идут)

CODES_JSON = MAPS / "codes.json"
NPA_MAPPING = MAPS / "npa_mapping.json"
MANUAL_OVERRIDES = MAPS / "manual_overrides.json"
