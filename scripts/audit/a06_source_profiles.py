# -*- coding: utf-8 -*-
"""АУДИТ ФАЗА 6: структурные профили source-выгрузок. READ-ONLY.

python scripts/audit/a06_source_profiles.py
-> reports/audit/source_profiles.json + source_profiles.md

Для каждого source/*.html: число и последовательность статей (пропуски/дубли
по базовым номерам), счётчики иерархии (разделы/главы/параграфы), сноски,
и сверка числа статей с maps/article_map_{slug}.json (если карта есть).
Профиль — опора для гейтов «статьи не потеряны/не задвоены» и для чанкера.
"""
import json
import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parent))
import auditlib as al

OUT_JSON = al.AUDIT_OUT / "source_profiles.json"
OUT_MD = al.AUDIT_OUT / "source_profiles.md"

RE_ART = re.compile(r"^\s*Статья\s+(\d+(?:-\d+)*)\s*[.\s]")
RE_HIER = {
    "разделы": re.compile(r"^\s*РАЗДЕЛ\s+\d+", re.I),
    "главы": re.compile(r"^\s*Глава\s+\d+", re.I),
    "параграфы": re.compile(r"^\s*Параграф\s+\d+", re.I),
}


def slug_to_source():
    """slug -> имя source-файла: codes.json + исключения auditlib.SOURCE_NAME;
    плюс файлы вне codes.json (constitution, prezident — в холде)."""
    codes = json.loads(al.CONFIG.joinpath("codes.json").read_text(encoding="utf-8"))
    m = {}
    for slug in codes:
        if slug.startswith("_"):
            continue
        m[slug] = al.SOURCE_NAME.get(slug, f"{slug}.html")
    known = set(m.values())
    for p in sorted(al.SOURCE.glob("*.html")):
        if p.name not in known:
            m[p.stem] = p.name
    return m


def profile(fp: Path):
    text = BeautifulSoup(fp.read_text(encoding="utf-8"), "html.parser").get_text("\n")
    lines = text.split("\n")
    arts = [m.group(1) for line in lines if (m := RE_ART.match(line))]
    bases = sorted({int(a.split("-")[0]) for a in arts})
    missing = []
    if bases:
        missing = [n for n in range(bases[0], bases[-1] + 1) if n not in set(bases)]
    seen, dups = set(), []
    for a in arts:
        if a in seen:
            dups.append(a)
        seen.add(a)
    prof = {
        "file": fp.name,
        "kb": round(fp.stat().st_size / 1024),
        "статей": len(arts),
        "первая": arts[0] if arts else None,
        "последняя": arts[-1] if arts else None,
        "пропуски_баз": missing,
        "дубли": sorted(set(dups)),
        "сноски": sum(line.strip().startswith("Сноска.") for line in lines),
    }
    for key, rx in RE_HIER.items():
        prof[key] = sum(bool(rx.match(line)) for line in lines)
    return prof


def main():
    al.AUDIT_OUT.mkdir(parents=True, exist_ok=True)
    profiles = {}
    rows = []
    for slug, name in sorted(slug_to_source().items()):
        fp = al.SOURCE / name
        if not fp.exists():
            profiles[slug] = {"file": name, "error": "нет файла"}
            continue
        p = profile(fp)
        amap = al.MAPS / f"article_map_{slug}.json"
        if amap.exists():
            n_map = len(json.loads(amap.read_text(encoding="utf-8")))
            p["статей_в_карте"] = n_map
            p["дельта_карты"] = n_map - p["статей"]
        profiles[slug] = p
        rows.append((slug, p))
        print(f"{slug:20} статей={p['статей']:>4} глав={p['главы']:>3} "
              f"пропуски={len(p['пропуски_баз'])} дубли={len(p['дубли'])} "
              f"дельта_карты={p.get('дельта_карты', '—')}")

    OUT_JSON.write_text(json.dumps(profiles, ensure_ascii=False, indent=1),
                        encoding="utf-8")

    L = ["# Структурные профили source (read-only)", "",
         "Дубли базовых номеров статей в кодексах РК легальны (статьи «N-1», «N-2» — ",
         "вставные); «дубли» ниже — повтор ПОЛНОГО номера, это аномалия выгрузки.",
         "«дельта_карты» = статей в article_map минус в source: карта строится по",
         "якорям финального файла, расхождение — повод смотреть руками.", "",
         "| slug | файл | KB | статей | глав | параграфов | пропуски баз | дубли | сноски | в карте | дельта |",
         "|---|---|---|---|---|---|---|---|---|---|---|"]
    for slug, p in rows:
        L.append(f"| {slug} | {p['file']} | {p['kb']} | {p['статей']} | {p['главы']} "
                 f"| {p['параграфы']} | {len(p['пропуски_баз'])} | {len(p['дубли'])} "
                 f"| {p['сноски']} | {p.get('статей_в_карте', '—')} "
                 f"| {p.get('дельта_карты', '—')} |")
    L += ["", "Пропуски базовой нумерации (исключённые статьи — норма для действующих"]
    L += ["редакций; перечислены для контроля):", ""]
    for slug, p in rows:
        if p["пропуски_баз"]:
            L.append(f"- {slug}: {len(p['пропуски_баз'])} → "
                     f"{', '.join(map(str, p['пропуски_баз'][:25]))}"
                     + (" …" if len(p["пропуски_баз"]) > 25 else ""))
    OUT_MD.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"\n-> {OUT_JSON}\n-> {OUT_MD}")


if __name__ == "__main__":
    main()
