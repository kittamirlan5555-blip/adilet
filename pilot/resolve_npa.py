# -*- coding: utf-8 -*-
"""Этап 2: разрешить UNRESOLVED имена через СОБСТВЕННЫЕ ссылки adilet в source/*.html
(adilet сам линкует «Закон РК «X»» -> /rus/docs/{НГР}), затем сверить <title> (CLAUDE.md §5).

--resolve : построить name->НГР из source-ссылок, сопоставить с unresolved, отчёт (без сети).
--verify  : для разрешённых скачать/прочитать-с-кэша страницу НГР, сверить <title> с именем;
            совпало -> verified, нет -> reject. Пишет npa_verified.json / npa_rejected.json.
"""
import csv
import io
import json
import os
import re
import sys
import time
from collections import Counter
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "source"
REP = ROOT / "reports" / "pilot"
QUOTES = "«»\"“”„'"
RE_QUOTED = re.compile(r"[«\"]([Оо][бБ]?\s[^»\"]{4,150})[»\"]")
RE_DOCID = re.compile(r"/docs/([A-Z][0-9A-Za-z_]{5,})")


def norm_name(s):
    s = re.sub(r"\s*[-–]\s*ИПС.*$", "", s or "")
    s = re.sub(r"\s*\(([^)]*кодекс[^)]*)\)\s*$", "", s, flags=re.I)
    s = s.strip().strip(QUOTES).strip()
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"\s+Республики\s+Казахстан$", "", s)
    return s


RE_ZAKON = re.compile(r"[Зз]акон|[Кк]одекс|[Кк]онституцион")


def adilet_link_registry():
    """name(norm) -> Counter(НГР) из СОБСТВЕННЫХ ссылок adilet в source. Два паттерна:
    (1) «Name» прямо в тексте ссылки docs/{НГР};
    (2) ОРФАН: <a docs/{НГР}>Законом…</a> Республики Казахстан «Name» — имя ПОСЛЕ ссылки
        (adilet линкует только слово «Закон», кавычки снаружи). Берём «Name» из ближайших
        ~200 символов текста после такой ссылки."""
    reg = {}
    for f in SOURCE.glob("*.html"):
        try:
            soup = BeautifulSoup(f.read_text(encoding="utf-8", errors="replace"), "html.parser")
        except Exception:
            continue
        for a in soup.find_all("a", href=True):
            m = RE_DOCID.search(a["href"])
            if not m:
                continue
            ngr = m.group(1)
            txt = a.get_text(" ", strip=True)
            for qm in RE_QUOTED.finditer(txt):
                reg.setdefault(norm_name(qm.group(0)), Counter())[ngr] += 1
            # (2) орфан: ссылка-«Закон…», имя в следующем тексте
            if RE_ZAKON.search(txt) and len(txt) < 60:
                tail = ""
                sib = a.next_sibling
                steps = 0
                while sib is not None and len(tail) < 200 and steps < 6:
                    tail += sib.get_text(" ") if hasattr(sib, "get_text") else str(sib)
                    if getattr(sib, "name", None) == "a":
                        break  # дошли до следующей ссылки — стоп
                    sib = sib.next_sibling
                    steps += 1
                qm = RE_QUOTED.search(tail[:120])
                if qm:
                    reg.setdefault(norm_name(qm.group(0)), Counter())[ngr] += 1
    return reg


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "--resolve"
    unresolved = json.loads((REP / "npa_unresolved.json").read_text(encoding="utf-8"))
    reg = adilet_link_registry()
    print(f"adilet-link реестр: {len(reg)} имён из source-ссылок")

    resolved = {}     # name -> ngr (кандидат из adilet-ссылок)
    still = {}
    for name, info in unresolved.items():
        c = reg.get(name)
        if c:
            ngr = c.most_common(1)[0][0]
            resolved[name] = {"ngr": ngr, **info}
        else:
            still[name] = info
    print(f"РАЗРЕШЕНО через adilet-ссылки: {len(resolved)} / {len(unresolved)} unresolved")
    print(f"осталось без НГР даже в adilet-ссылках: {len(still)}")

    if mode == "--resolve":
        (REP / "npa_resolved_candidates.json").write_text(
            json.dumps(resolved, ensure_ascii=False, indent=2), encoding="utf-8")
        print("\nразрешённые (кандидаты на fetch-сверку), топ по частоте:")
        for name, v in sorted(resolved.items(), key=lambda kv: -kv[1]["freq"])[:15]:
            print(f"  {v['freq']:>3}× {v['ngr']:14} {name[:60]}")
        print("\nСОВСЕМ без НГР (в отчёт unresolved), топ:")
        for name, v in sorted(still.items(), key=lambda kv: -kv[1]["freq"])[:10]:
            print(f"  {v['freq']:>3}× {name[:60]}")
        return

    if mode == "--verify":
        try:
            import requests
            os.environ.setdefault("REQUESTS_CA_BUNDLE", str(ROOT / "pilot" / "certs" / "adilet_chain.pem"))
        except ImportError:
            requests = None
        H = {"User-Agent": "Mozilla/5.0 (ADILETkz pilot; contact: team)"}
        verified, rejected = {}, {}
        for i, (name, v) in enumerate(resolved.items(), 1):
            ngr = v["ngr"]
            p = SOURCE / f"{ngr}.html"
            html = ""
            if p.exists():
                html = p.read_text(encoding="utf-8", errors="replace")
            elif requests:
                try:
                    r = requests.get(f"https://adilet.zan.kz/rus/docs/{ngr}", headers=H, timeout=30)
                    if r.status_code == 200:
                        html = r.text
                        p.write_text(html, encoding="utf-8")
                    time.sleep(1.2)
                except Exception:
                    pass
            title = ""
            repealed = False
            if html:
                soup = BeautifulSoup(html, "html.parser")
                for t in soup.find_all(["script", "style"]):
                    t.decompose()
                if soup.title and soup.title.string:
                    title = soup.title.string
                # §5: не линковать на МЁРТВУЮ редакцию — фин. «утратил силу» в шапке
                art = soup.find("article") or soup
                atext = art.get_text(" ", strip=True)
                am = re.search(r"Стать[яиею]\s+\d", atext)
                header = atext[:am.start()] if am else atext[:2000]
                repealed = bool(re.search(r"[Уу]тратил[аио]?\s+силу", header))
            tnorm = norm_name(title)
            # §5: <title> целевого НГР == имя в кавычках И акт НЕ отменён
            if tnorm and tnorm == name and not repealed:
                verified[name] = {"ngr": ngr, "freq": v["freq"], "title": title[:70]}
            else:
                reason = "repealed" if repealed else ("no-title" if not tnorm else "title!=name")
                rejected[name] = {"ngr": ngr, "freq": v["freq"],
                                  "title": title[:70], "reason": reason}
            if i % 20 == 0:
                print(f"  ...{i}/{len(resolved)} проверено", flush=True)
        (REP / "npa_verified.json").write_text(
            json.dumps(verified, ensure_ascii=False, indent=2), encoding="utf-8")
        (REP / "npa_rejected.json").write_text(
            json.dumps(rejected, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nVERIFIED (<title>==имя): {len(verified)} | REJECTED (не совпало): {len(rejected)}")
        print("verified sample:")
        for name, v in list(verified.items())[:8]:
            print(f"  {v['ngr']:14} {name[:55]}")
        print("rejected sample (НЕ добавляем — §5):")
        for name, v in list(rejected.items())[:8]:
            print(f"  {v['ngr']:14} имя={name[:40]!r} <title>={v['title'][:40]!r}")


if __name__ == "__main__":
    main()
