# -*- coding: utf-8 -*-
"""Реестр подзаконных актов — по ПЕРВОЙ БУКВЕ НГР (фасеты не равны типу, доказано в
reports/subordinate_recon.md: ПРОТ/СОГЛ отдают Z-законы, ПРАВ смешан, сумма фасетов >
всей базы). Фасет используем ТОЛЬКО как способ обхода листинга, тип берём из НГР.

Отсев: утратившие силу (span.status_yts) и поправки/отмены (заголовок «О внесении…»,
«О признании утратившими силу…»). Остаётся ДЕЙСТВУЮЩЕЕ СОДЕРЖАТЕЛЬНОЕ.

Полного обхода 225 тыс. актов НЕ делаем (это ~2200 запросов и нагрузка на сайт):
берём РАСПРЕДЕЛЁННУЮ выборку страниц, объёмы даём как оценку с явной пометкой.

  python pilot/sub_registry.py build        # собрать реестр (кэш в scratchpad)
  python pilot/sub_registry.py pick --n 100 # выбрать пилот-100 (S и V)
"""
import io, sys, os, re, json, time, random
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from pathlib import Path
from collections import Counter, defaultdict

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("REQUESTS_CA_BUNDLE", str(ROOT / "pilot" / "certs" / "adilet_chain.pem"))
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote

SCRATCH = Path(os.environ.get("RECON_DIR",
    r"C:\Users\user\AppData\Local\Temp\claude\C--Users-user-Desktop-ADILETkz"
    r"\05d2f495-4ada-4c40-8b28-90554cb40953\scratchpad\subordinate"))
CACHE = SCRATCH / "cache"; CACHE.mkdir(parents=True, exist_ok=True)
REG = SCRATCH / "registry.json"

H = {"User-Agent": "Mozilla/5.0 (ADILETkz registry; contact: team)"}
BASE = "https://adilet.zan.kz/rus/search/docs/"

# обходим фасетами, дающими S/V (приказы+постановления) — scope пилота
WALK = {"ПОСТ": 80586, "ПРИК": 31611, "НПОС": 467}
PAGES_PER = 40                      # распределённая выборка страниц на фасет

RE_AMEND = re.compile(r"^\s*О\s+внесени|внесении\s+изменени", re.I)
RE_REPEAL = re.compile(r"о\s+признании\s+утратив", re.I)
# «технические» заголовки, не нормы
RE_TECH = re.compile(r"^\s*(О проекте|Об объявлении|О созыве|О награжд|О присужд|"
                     r"О назначении|Об освобожд|О переводе|О выделении|О подписании|"
                     r"О ратификации|О заключении)", re.I)
TYPE_BY_PREFIX = {"S": "постановление", "V": "приказ", "U": "указ", "N": "распоряжение",
                  "H": "решение (маслихат/акимат)", "R": "решение", "P": "правила/решение",
                  "G": "решение", "B": "иное", "Z": "ЗАКОН (не подзаконный!)",
                  "K": "КОДЕКС (не подзаконный!)"}


def get(url, tag):
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
        cls = " ".join(st.get("class", [])) if st else ""
        out.append({"ngr": m.group(1), "title": a.get_text(" ", strip=True),
                    "repealed": "status_yts" in cls})
    return out


def build():
    seen, rows = set(), []
    for va, tot in WALK.items():
        maxp = max(1, min(tot // 100, 100))
        pages = sorted(set(round(1 + i * (maxp - 1) / max(1, PAGES_PER - 1))
                           for i in range(PAGES_PER))) if maxp > 1 else [1]
        got = 0
        for p in pages:
            for r in rows_of(get(f"{BASE}pagesize=100&page={p}&va={quote(va)}", f"L_{va}_{p}")):
                if r["ngr"] in seen:
                    continue
                seen.add(r["ngr"])
                r["prefix"] = r["ngr"][0]
                r["kind_type"] = TYPE_BY_PREFIX.get(r["prefix"], "?")
                r["amend"] = bool(RE_AMEND.search(r["title"]))
                r["repeal_act"] = bool(RE_REPEAL.search(r["title"]))
                r["tech"] = bool(RE_TECH.search(r["title"]))
                r["substantive_active"] = not (r["repealed"] or r["amend"]
                                               or r["repeal_act"] or r["tech"])
                r["via_facet"] = va
                rows.append(r); got += 1
        print(f"  {va:6s} страниц={len(pages):3d} собрано новых={got:5d}")
    REG.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"\nвсего уникальных актов в реестре-выборке: {len(rows)}")
    print("\nПО ПЕРВОЙ БУКВЕ НГР (настоящий тип):")
    byp = defaultdict(lambda: [0, 0])
    for r in rows:
        byp[r["prefix"]][0] += 1
        if r["substantive_active"]:
            byp[r["prefix"]][1] += 1
    for pref, (n, act) in sorted(byp.items(), key=lambda x: -x[1][0]):
        print(f"   {pref}  {TYPE_BY_PREFIX.get(pref,'?'):28s} всего={n:5d}  действ.содержат.={act:5d}"
              f"  ({100*act/n:.0f}%)")
    print("\nОТСЕВ (почему выбывают):")
    print(f"   утратили силу : {sum(1 for r in rows if r['repealed'])}")
    print(f"   поправки      : {sum(1 for r in rows if r['amend'])}")
    print(f"   отмены        : {sum(1 for r in rows if r['repeal_act'])}")
    print(f"   технические   : {sum(1 for r in rows if r['tech'])}")
    print(f"   ОСТАЁТСЯ      : {sum(1 for r in rows if r['substantive_active'])}")
    # экстраполяция объёмов
    print("\nОЦЕНКА ПО ГЕНЕРАЛЬНОЙ СОВОКУПНОСТИ (доля выборки ×總):")
    for va, tot in WALK.items():
        sub = [r for r in rows if r["via_facet"] == va]
        if not sub:
            continue
        share = sum(1 for r in sub if r["substantive_active"]) / len(sub)
        print(f"   {va:6s} всего={tot:7,d} × {share*100:4.1f}% -> ~{int(tot*share):,} действ.содержательных")


def ngr_year(ngr):
    m = re.match(r"^[A-Z](\d{2})", ngr or "")
    if not m:
        return None
    y = int(m.group(1))
    return 1900 + y if y >= 90 else 2000 + y


def pick(n=100):
    """Пилот: V (приказы министров) + P (постановления Правительства), современные.
    S — это нормативные постановления Конституционного Совета, другая конструкция
    (толкование, без «Правил внутри»), в пилот не берём."""
    rows = json.loads(REG.read_text(encoding="utf-8"))
    pool = [r for r in rows if r["substantive_active"] and r["prefix"] in ("V", "P")
            and (ngr_year(r["ngr"]) or 0) >= 2015]
    random.seed(20260817)
    byp = defaultdict(list)
    for r in pool:
        byp[r["prefix"]].append(r)
    take = []
    for pref, want in (("V", n // 2), ("P", n - n // 2)):
        lst = byp.get(pref, [])
        random.shuffle(lst)
        take += lst[:want]
    for r in take:
        r["year"] = ngr_year(r["ngr"])
    (SCRATCH / "pilot100.json").write_text(json.dumps(take, ensure_ascii=False, indent=1),
                                           encoding="utf-8")
    print(f"пул действ.содержательных S+V: {len(pool)} -> выбрано {len(take)}")
    print(f"   по типу: {Counter(r['prefix'] for r in take)}")
    for r in take[:5]:
        print(f"   {r['ngr']:13s} {r['title'][:70]}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "build"
    if cmd == "build":
        build()
    else:
        n = int(sys.argv[sys.argv.index("--n") + 1]) if "--n" in sys.argv else 100
        pick(n)
