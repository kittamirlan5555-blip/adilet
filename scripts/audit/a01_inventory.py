# -*- coding: utf-8 -*-
"""АУДИТ ФАЗА 1: инвентаризация корпуса. READ-ONLY.

python scripts/audit/a01_inventory.py
-> data/reports/audit/01_inventory.md

Каждая цифра в отчёте воспроизводима этим скриптом (raw-подсчёты, без bs4).
"""
import re
import json
import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
FINAL = ROOT / "data" / "final"
SOURCE = ROOT / "data" / "source"
MAPS = ROOT / "data" / "maps"
CONFIG = ROOT / "config"
OUT = ROOT / "data" / "reports" / "audit"

# slug -> имя source-файла (где имена не совпадают)
SOURCE_NAME = {
    "grazhdanskiy_osob": "GKosobenniy.html",
    "informatizacii": "obINFORM.html",
}


def slugs():
    """Все документы по файлам data/final (без .bak)."""
    out = {}
    for p in sorted(FINAL.glob("*_ready.html")):
        out.setdefault(p.name[:-len("_ready.html")], set()).add("ready")
    for p in sorted(FINAL.glob("*_structured.html")):
        out.setdefault(p.name[:-len("_structured.html")], set()).add("structured")
    return out


def counts(path):
    raw = path.read_text(encoding="utf-8")
    return {
        "size": path.stat().st_size,
        "a_href": raw.count("<a href"),
        "ids": len(re.findall(r'id="[^"]+"', raw)),
        "names": len(re.findall(r'name="[^"]+"', raw)),
        "h3": raw.count("<h3"),
        "mtime": datetime.datetime.fromtimestamp(path.stat().st_mtime)
                 .strftime("%Y-%m-%d %H:%M"),
    }


def map_len(path):
    if not path.exists():
        return None
    return len(json.loads(path.read_text(encoding="utf-8")))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    cj = json.loads((CONFIG / "codes.json").read_text(encoding="utf-8"))
    code_ids = {k: v["doc_id"] for k, v in cj.items()
                if isinstance(v, dict) and "doc_id" in v}

    L = ["# АУДИТ 01 — Инвентаризация корпуса", "",
         f"Сгенерировано: scripts/audit/a01_inventory.py, {datetime.date.today()}",
         "", "Кодекс = есть форма `_ready`; закон = только `_structured`.", ""]
    hdr = ("| slug | doc_id | формы | размер ready/structured | <a href "
           "r/s | id+name r/s | article_map | subpoint_map | source (size) | mtime |")
    L += [hdr, "|" + "---|" * 10]

    docs = slugs()
    n_codes = n_laws = 0
    for slug, forms in sorted(docs.items()):
        is_code = "ready" in forms
        n_codes += is_code
        n_laws += not is_code
        c = {}
        for f in ("ready", "structured"):
            p = FINAL / f"{slug}_{f}.html"
            c[f] = counts(p) if p.exists() else None
        am = map_len(MAPS / f"article_map_{slug}.json")
        sm = map_len(MAPS / f"subpoint_map_{slug}.json")
        sname = SOURCE_NAME.get(slug, f"{slug}.html")
        sp = SOURCE / sname
        ssize = f"{sname} ({sp.stat().st_size:,})" if sp.exists() else f"**НЕТ** ({sname})"
        fmt = lambda f, k: (f"{c[f][k]:,}" if c[f] else "—")
        L.append(
            f"| {slug} | {code_ids.get(slug, '?')} | {'+'.join(sorted(forms))} "
            f"| {fmt('ready','size')} / {fmt('structured','size')} "
            f"| {fmt('ready','a_href')} / {fmt('structured','a_href')} "
            f"| {(str(c['ready']['ids']+c['ready']['names']) if c['ready'] else '—')} / "
            f"{(str(c['structured']['ids']+c['structured']['names']) if c['structured'] else '—')} "
            f"| {am if am is not None else '**НЕТ**'} "
            f"| {sm if sm is not None else '—'} "
            f"| {ssize} "
            f"| {(c['ready'] or c['structured'])['mtime']} |")

    L += ["",
          f"**Итого документов: {len(docs)} = {n_codes} кодексов (ready+structured) "
          f"+ {n_laws} законов (только structured).**",
          "",
          "## Расхождения с ожиданием",
          "",
          f"- Задание называет «14 кодексов + 10 законов» (=24). Фактически в data/final: "
          f"**{n_codes} + {n_laws} = {len(docs)}**. Лишних файлов нет; каких 3 документов "
          "не хватает до 24 — вопрос шефу (в FINAL.md).",
          "- В config/codes.json документов: "
          f"{len(code_ids)}; без файла в data/final: "
          f"{sorted(set(code_ids) - set(docs)) or 'нет'}; "
          f"файлы без записи в codes.json: {sorted(set(docs) - set(code_ids)) or 'нет'}.",
          "",
          "## Воспроизводимость",
          "```",
          "PYTHONIOENCODING=utf-8 python scripts/audit/a01_inventory.py",
          "```"]
    (OUT / "01_inventory.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
