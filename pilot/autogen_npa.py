# -*- coding: utf-8 -*-
"""Автоген npa_mapping для пилота: закрыть невылинкованные внешние ссылки на
законы по названию (главный рычаг замечаний Анары).

Этап 1 (этот файл, --scan): реестр название→НГР + извлечение нужных названий из
82 _ready + сопоставление с реестром. Пишет:
  reports/pilot/npa_candidates.json  — name -> {ngr, freq, source, sample_phrase}
  reports/pilot/npa_unresolved.json  — name -> {freq, sample_phrase}  (нет в реестре)
Этап 2 (--apply): вливает ТОЛЬКО подтверждённые (реестр или fetch+<title>) в
maps/npa_mapping.json как ключ «bare «Название»» -> НГР (полный спан имени;
ловит и цепочки). Fetch-сверка — отдельно (--verify).

Правило CLAUDE.md §5: НГР добавляем только после сверки названия с целью.
"""
import csv
import io
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
FINAL = ROOT / "final"
REP = ROOT / "reports" / "pilot"

QUOTES = "«»\"“”„'"


def norm_name(s: str) -> str:
    s = re.sub(r"\s*[-–]\s*ИПС.*$", "", s or "")
    s = re.sub(r"\s*\(([^)]*кодекс[^)]*)\)\s*$", "", s, flags=re.I)  # хвост «(Налоговый кодекс)»
    s = s.strip().strip(QUOTES).strip()
    s = re.sub(r"\s+", " ", s)
    # трейлинг ГЕНИТИВ «Республики Казахстан» — стандартный суффикс имени акта;
    # снимаем, чтобы «…судей Республики Казахстан» == «…судей». НЕ трогаем
    # ЛОКАТИВ «в Республике Казахстан» (это часть имени, напр. «О языках в РК»).
    s = re.sub(r"\s+Республики\s+Казахстан$", "", s)
    return s


def build_registry() -> dict:
    """norm(name) -> НГР. Источники: codes.json titles, pool_new_meta titles."""
    reg = {}
    codes = json.loads((ROOT / "maps" / "codes.json").read_text(encoding="utf-8"))
    for k, v in codes.items():
        if k.startswith("_") or not isinstance(v, dict):
            continue
        t = norm_name(v.get("title", ""))
        did = v.get("doc_id", k)
        if len(t) >= 10 and t.startswith(("О ", "Об ", "О ")):
            reg.setdefault(t, did)
    meta = REP.parent  # placeholder
    pm = ROOT / "pilot" / "pool_new_meta.csv"
    if pm.exists():
        for r in csv.DictReader(pm.open(encoding="utf-8")):
            t = norm_name(r.get("title", ""))
            ngr = r.get("ngr", "")
            if len(t) >= 10 and t.startswith(("О ", "Об ")) and ngr:
                reg.setdefault(t, ngr)
    return reg


# «Название» в контексте закона/кодекса (акт-имя обычно с «О »/«Об »)
RE_QUOTED = re.compile(r"[«\"]([Оо][бБ]?\s[^»\"]{4,150})[»\"]")


def extract_names(slug: str):
    """Возвращает Counter(name) + пример полной фразы для НЕвылинкованных
    (вне <a>) упоминаний закон-имён в _ready данного слага."""
    p = FINAL / f"{slug}_ready.html"
    if not p.exists():
        return Counter(), {}
    soup = BeautifulSoup(p.read_text(encoding="utf-8", errors="replace"), "html.parser")
    for t in soup.find_all(["script", "style"]):
        t.decompose()
    cnt = Counter()
    sample = {}
    for tn in soup.find_all(string=True):
        if tn.find_parent("a"):
            continue
        s = str(tn)
        for m in RE_QUOTED.finditer(s):
            name = norm_name(m.group(0))
            cnt[name] += 1
            if name not in sample:
                sample[name] = s[max(0, m.start() - 30):m.end() + 5].strip()
    return cnt, sample


def main():
    slugs = [r["slug"] for r in csv.DictReader((ROOT / "pilot" / "pilot_audit.csv").open(encoding="utf-8"))]
    reg = build_registry()
    print(f"реестр название→НГР: {len(reg)} записей")

    total = Counter()
    samples = {}
    perslug = defaultdict(set)
    for s in slugs:
        c, smp = extract_names(s)
        for name, f in c.items():
            total[name] += f
            perslug[name].add(s)
            samples.setdefault(name, smp[name])

    print(f"уникальных цитируемых закон-имён в 82 _ready: {len(total)} "
          f"(вхождений: {sum(total.values())})")

    candidates, unresolved = {}, {}
    for name, freq in total.items():
        ngr = reg.get(name)
        if ngr:
            candidates[name] = {"ngr": ngr, "freq": freq, "docs": len(perslug[name]),
                                "sample": samples[name][:80]}
        else:
            unresolved[name] = {"freq": freq, "docs": len(perslug[name]),
                                "sample": samples[name][:80]}

    REP.mkdir(parents=True, exist_ok=True)
    (REP / "npa_candidates.json").write_text(
        json.dumps(candidates, ensure_ascii=False, indent=2), encoding="utf-8")
    (REP / "npa_unresolved.json").write_text(
        json.dumps(unresolved, ensure_ascii=False, indent=2), encoding="utf-8")

    cand_occ = sum(v["freq"] for v in candidates.values())
    unr_occ = sum(v["freq"] for v in unresolved.values())
    print(f"\nЗАКРЫВАЕМО из реестра (candidates): {len(candidates)} имён / {cand_occ} вхождений")
    print(f"UNRESOLVED (нет в реестре, нужен fetch): {len(unresolved)} имён / {unr_occ} вхождений")
    print("\nТОП-15 unresolved по частоте (что теряем без fetch):")
    for name, v in sorted(unresolved.items(), key=lambda kv: -kv[1]["freq"])[:15]:
        print(f"  {v['freq']:>3}× [{v['docs']}док] {name[:70]}")


if __name__ == "__main__":
    main()
