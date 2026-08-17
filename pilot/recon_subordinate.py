# -*- coding: utf-8 -*-
"""ЭТАП 1 (РАЗВЕДКА) подзаконных актов — ТОЛЬКО ЧТЕНИЕ.

Ничего в репозитории не перезаписывает: HTML-выборка и промежуточные файлы идут в
scratchpad, единственный артефакт — reports/subordinate_recon.md (пишется отдельно).

Стадии:
  counts  — объёмы по фасетам va= + распределение первой буквы НГР (реальный тип акта)
  sample  — по каждому типу: доля утративших силу и доля поправок (выборка страниц)
  fetch   — скачать по N разных ДЕЙСТВУЮЩИХ содержательных актов каждого типа
  profile — структурный профиль скачанных: «Статья N»? пункты? приложения? якоря z?
  links   — на что ссылаются: законы (маппинг 654), подзаконные, внутренние

TLS: adilet отдаёт неполную цепочку — используем собранный бандл pilot/certs/adilet_chain.pem
(проверку НЕ отключаем).
"""
import io, sys, os, re, json, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("REQUESTS_CA_BUNDLE", str(ROOT / "pilot" / "certs" / "adilet_chain.pem"))
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote

SCRATCH = Path(os.environ.get("RECON_DIR",
    r"C:\Users\user\AppData\Local\Temp\claude\C--Users-user-Desktop-ADILETkz"
    r"\05d2f495-4ada-4c40-8b28-90554cb40953\scratchpad\subordinate"))
SCRATCH.mkdir(parents=True, exist_ok=True)
CACHE = SCRATCH / "cache"; CACHE.mkdir(exist_ok=True)
ACTS = SCRATCH / "acts"; ACTS.mkdir(exist_ok=True)

H = {"User-Agent": "Mozilla/5.0 (ADILETkz recon; contact: team)"}
BASE = "https://adilet.zan.kz/rus/search/docs/"

# фасеты подзаконных (проверено: мусорный код -> 0, значит va реально фильтрует).
# ВНИМАНИЕ: ПРОТ/СОГЛ дают Z-НГР (законы о ратификации) — это НЕ тип документа, они
# пересекаются с ЗАК; в подзаконный scope не берём.
SUB_FACETS = ["УКАЗ", "ПОСТ", "ПРИК", "РАСП", "РЕШ", "НПОС", "ПРАВ", "РЕГЛ"]
LAW_FACETS = ["ЗАК", "КОД", "КЗАК", "УЗАК", "УКОН"]

RE_AMEND = re.compile(r"^\s*О\s+внесени|внесении\s+изменени", re.I)
RE_REPEAL_TITLE = re.compile(r"о\s+признании\s+утратив", re.I)


def get(url, tag):
    """GET с файловым кэшем (разведку гоняем многократно — сайт не долбим)."""
    key = CACHE / (re.sub(r"[^\w]+", "_", tag)[:120] + ".html")
    if key.exists():
        return key.read_text(encoding="utf-8", errors="replace")
    for att in range(1, 4):
        try:
            r = requests.get(url, headers=H, timeout=45)
            if r.status_code == 200:
                key.write_text(r.text, encoding="utf-8")
                time.sleep(0.3)
                return r.text
        except requests.RequestException:
            time.sleep(2 * att)
    return ""


def listing(va, page):
    return get(f"{BASE}pagesize=100&page={page}&va={quote(va)}", f"L_{va}_{page}")


def total_of(html):
    b = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
    m = re.search(r"Найдено[:\s]*([\d\s]+?)\s", b)
    return int(m.group(1).replace(" ", "")) if m else 0


def rows_of(html):
    s = BeautifulSoup(html, "html.parser")
    out = []
    for ph in s.select("div.post_holder"):
        a = ph.select_one("h4.post_header a[href]")
        if not a:
            continue
        m = re.search(r"/rus/docs/([A-Z][0-9A-Za-z_]{5,})", a["href"])
        if not m:
            continue
        st = ph.select_one("span.status")
        out.append({"ngr": m.group(1), "title": a.get_text(" ", strip=True),
                    "repealed": "status_yts" in " ".join(st.get("class", []) if st else []),
                    "status": st.get_text(" ", strip=True) if st else ""})
    return out


def cmd_counts():
    res = {}
    for va in LAW_FACETS + SUB_FACETS:
        h = listing(va, 1)
        tot = total_of(h)
        pref = Counter(r["ngr"][0] for r in rows_of(h))
        res[va] = {"total": tot, "ngr_prefix": dict(pref.most_common())}
        print(f"  {va:6s} {tot:8,d}  НГР-префиксы: {dict(pref.most_common(4))}")
    (SCRATCH / "counts.json").write_text(json.dumps(res, ensure_ascii=False, indent=1),
                                         encoding="utf-8")
    return res


def cmd_sample(pages=(1, 5, 20, 60)):
    """Доли утративших силу и поправок — по выборке страниц (не полный обход: 229к актов)."""
    out = {}
    for va in SUB_FACETS:
        tot = total_of(listing(va, 1))
        maxp = max(1, min(tot // 100, 100))
        use = [p for p in pages if p <= maxp] or [1]
        rr = []
        for p in use:
            rr += rows_of(listing(va, p))
        if not rr:
            continue
        rep = sum(1 for r in rr if r["repealed"])
        am = sum(1 for r in rr if RE_AMEND.search(r["title"]))
        rp = sum(1 for r in rr if RE_REPEAL_TITLE.search(r["title"]))
        out[va] = {"total": tot, "sampled": len(rr), "pages": use,
                   "repealed_pct": round(100 * rep / len(rr), 1),
                   "amend_pct": round(100 * am / len(rr), 1),
                   "repealtitle_pct": round(100 * rp / len(rr), 1),
                   "est_active_substantive": int(tot * (1 - rep / len(rr)) * (1 - (am + rp) / len(rr)))}
        o = out[va]
        print(f"  {va:6s} всего={tot:8,d} выборка={len(rr):4d} "
              f"утратили={o['repealed_pct']:5.1f}% поправки={o['amend_pct']:5.1f}% "
              f"-> оценка действ.содержательных ~{o['est_active_substantive']:,}")
    (SCRATCH / "sample.json").write_text(json.dumps(out, ensure_ascii=False, indent=1),
                                         encoding="utf-8")
    return out


def cmd_fetch(n=6):
    """По N ДЕЙСТВУЮЩИХ содержательных (не поправка, не отмена) актов каждого типа."""
    picked = {}
    for va in SUB_FACETS:
        cand = []
        for p in (1, 5, 20, 60):
            for r in rows_of(listing(va, p)):
                if r["repealed"] or RE_AMEND.search(r["title"]) or RE_REPEAL_TITLE.search(r["title"]):
                    continue
                cand.append(r)
            if len(cand) >= n * 3:
                break
        seen, take = set(), []
        for r in cand:                       # разные по первой букве НГР и по теме
            k = r["ngr"][0] + r["title"][:12]
            if k in seen:
                continue
            seen.add(k); take.append(r)
            if len(take) >= n:
                break
        picked[va] = take
        for r in take:
            html = get(f"https://adilet.zan.kz/rus/docs/{r['ngr']}", f"D_{r['ngr']}")
            if html:
                (ACTS / f"{va}__{r['ngr']}.html").write_text(html, encoding="utf-8")
        print(f"  {va:6s} скачано {len(take)}: {[r['ngr'] for r in take]}")
    (SCRATCH / "picked.json").write_text(json.dumps(picked, ensure_ascii=False, indent=1),
                                         encoding="utf-8")
    return picked


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "counts"
    print(f"=== {cmd} ===  (кэш: {CACHE})")
    {"counts": cmd_counts, "sample": cmd_sample, "fetch": cmd_fetch}[cmd]()
