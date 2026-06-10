# -*- coding: utf-8 -*-
"""Регрессия скрипта 11 на ВСЕХ источниках — READ-ONLY по источникам.

Usage:
    python reg_11_all.py <outdir>

Прогоняет process_file из 11_structure_html.py по каждому data/source/*.html
и пишет результат в <outdir>/{code}_11.html. Печатает sha256 каждого файла.
"""
import sys
import hashlib
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "source"

# Импортируем модуль 11 (имя начинается с цифры — через importlib)
spec = importlib.util.spec_from_file_location(
    "mod11", str(Path(__file__).resolve().parent / "11_structure_html.py"))
mod11 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod11)


def main():
    outdir = Path(sys.argv[1])
    outdir.mkdir(parents=True, exist_ok=True)
    sources = sorted(SRC.glob("*.html"))
    print(f"sources: {len(sources)}  outdir: {outdir}")
    for s in sources:
        code = s.stem
        outp = outdir / f"{code}_11.html"
        mod11.process_file(str(s), str(outp))
        h = hashlib.sha256(outp.read_bytes()).hexdigest()[:16]
        print(f"  {code:18} {h}")


if __name__ == "__main__":
    main()
