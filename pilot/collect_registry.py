# -*- coding: utf-8 -*-
"""BLOCK 2 — ПОЛНЫЙ реестр целевых актов РК с adilet (не BFS-выборка).

adilet отдаёт listing по ТИПУ: /rus/search/docs/pagesize=100&page=N&va=<ТИП>.
Каждая строка (div.post_holder): НГР+title, span.status (status_yts=Утративший силу /
status_upd|new|err=действует), <p> дескриптор (тип+дата+№). Классифицируем ИЗ LISTING —
без покачки каждого дока (вежливо, быстро). Кэш страниц listing на диске.

Типы: ЗАК(закон) КОД(кодекс) КЗАК(конституц.закон) — основной scope шефа;
      УЗАК/УКОН (указ силы закона/КЗ) — собираем, помечаем как edge (решение владельца).

Фильтр целей: status != Утративший силу  И  НЕ поправка (title «О внесении изменени…»).
Вычитаем «сделанное»: HEAD codes.json doc_ids + пилот (ingest_manifest) + prev_slugs.

Выход: maps/corpus_registry.json + reports/corpus_registry.md.
Запуск:  python pilot/collect_registry.py            # все типы, с кэшем
         python pilot/collect_registry.py --types КОД,КЗАК
"""
import csv, io, json, math, os, re, subprocess, sys, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from pathlib import Path
from urllib.parse import quote
from collections import Counter, OrderedDict
import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "source" / "_registry_cache"
CACHE.mkdir(parents=True, exist_ok=True)
H = {"User-Agent": "Mozilla/5.0 (ADILETkz corpus registry; contact: team)"}
os.environ.setdefault("REQUESTS_CA_BUNDLE", str(ROOT / "pilot" / "certs" / "adilet_chain.pem"))
SLEEP = 1.1
BASE = "https://adilet.zan.kz/rus/search/docs/"
TYPES = OrderedDict([("ЗАК", "Закон"), ("КОД", "Кодекс"), ("КЗАК", "Конституционный закон"),
                     ("УЗАК", "Указ, имеющий силу закона"), ("УКОН", "Указ, имеющий силу КЗ")])
SCOPE_MAIN = {"ЗАК", "КОД", "КЗАК"}       # основной scope шефа; УЗАК/УКОН — edge


def is_amendment(title):
    t = (title or "").lower()
    return "внесени" in t and ("измен" in t or "дополнен" in t)


# под-классификация действующих неамендмент законов: только substantive — цель линковки.
# ratification/budget/amnesty — «Закон» по типу, но не регуляторные акты со структурой.
KIND_PATS = [
    ("repealer",     re.compile(r"призн\w+\s+утратив\w+\s+силу|признании\s+утратив", re.I)),
    ("ratification", re.compile(r"ратификац|присоединени[еи]|денонсац|о\s+принятии\b|"
                                r"снятии\s+оговорк|о\s+выходе\s+из", re.I)),
    ("treaty",       re.compile(r"соглашени|конвенци|хартии|пакт\b|о\s+договоре", re.I)),
    ("budget",       re.compile(r"республиканском\s+бюджете|гарантированном\s+трансферте|"
                                r"бюджете\s+на\s+\d", re.I)),
    ("amnesty",      re.compile(r"амнист|помилован", re.I)),
]


def classify_kind(title):
    for name, rx in KIND_PATS:
        if rx.search(title or ""):
            return name
    return "substantive"


def fetch_page(va, page):
    key = CACHE / f"{va}_ps100_p{page}.html"
    if key.exists():
        return key.read_text(encoding="utf-8", errors="replace"), True
    url = f"{BASE}pagesize=100&page={page}&va={quote(va)}"
    for attempt in range(1, 4):
        try:
            r = requests.get(url, headers=H, timeout=45)
            if r.status_code == 200:
                key.write_text(r.text, encoding="utf-8")
                return r.text, False
        except requests.RequestException:
            time.sleep(2 * attempt)
    return "", False


def total_count(html):
    body = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
    m = re.search(r"Найдено[:\s]*([\d\s]+?)\s", body)
    return int(m.group(1).replace(" ", "")) if m else 0


def parse_rows(html, va):
    out = []
    soup = BeautifulSoup(html, "html.parser")
    for ph in soup.select("div.post_holder"):
        a = ph.select_one("h4.post_header a[href]")
        if not a:
            continue
        m = re.search(r"/rus/docs/([A-Z][0-9A-Za-z_]{5,})", a["href"])
        if not m:
            continue
        st = ph.select_one("span.status")
        scls = " ".join(st.get("class", [])) if st else ""
        stxt = st.get_text(" ", strip=True) if st else ""
        p = ph.find("p")
        out.append({"ngr": m.group(1), "type": va, "title": a.get_text(" ", strip=True),
                    "status": stxt, "status_cls": scls,
                    "descr": (p.get_text(" ", strip=True)[:120] if p else "")})
    return out


def done_set():
    """НГР/doc_id всего, что уже сделано: HEAD codes.json + пилот + prev_slugs."""
    done = {}
    r = subprocess.run(["git", "show", "HEAD:maps/codes.json"], cwd=ROOT,
                       capture_output=True, text=True, encoding="utf-8")
    if r.returncode == 0:
        for k, v in json.loads(r.stdout).items():
            if k.startswith("_") or not isinstance(v, dict):
                continue
            for key in {k, v.get("doc_id", k)}:
                done[key.rstrip("_")] = "corpus"
    mf = ROOT / "pilot" / "ingest_manifest.csv"
    if mf.exists():
        for row in csv.DictReader(mf.open(encoding="utf-8")):
            done.setdefault(row["ngr"].rstrip("_"), "pilot")
    pf = ROOT / "pilot" / "prev_slugs.txt"
    if pf.exists():
        for l in pf.read_text(encoding="utf-8").split():
            done.setdefault(l.strip().rstrip("_"), "prev")
    return done


def main():
    types = TYPES
    if "--types" in sys.argv:
        want = sys.argv[sys.argv.index("--types") + 1].split(",")
        types = OrderedDict((k, TYPES[k]) for k in want if k in TYPES)

    acts = OrderedDict()          # ngr -> row (первый тип выигрывает)
    fetches = 0
    for va in types:
        html, cached = fetch_page(va, 1)
        if not cached:
            fetches += 1; time.sleep(SLEEP)
        if not html:
            print(f"  {va}: пусто/недоступно"); continue
        tot = total_count(html)
        pages = max(1, math.ceil(tot / 100))
        print(f"  va={va:5} Найдено={tot:5}  страниц={pages}")
        allrows = parse_rows(html, va)
        for p in range(2, pages + 1):
            h2, c2 = fetch_page(va, p)
            if not c2:
                fetches += 1; time.sleep(SLEEP)
            if h2:
                allrows += parse_rows(h2, va)
        for row in allrows:
            acts.setdefault(row["ngr"], row)     # тип по первому появлению
        print(f"          собрано строк={len(allrows)} (уник итого={len(acts)})  запросов={fetches}")

    # классификация + вычет сделанного
    done = done_set()
    for ngr, row in acts.items():
        repealed = ("status_yts" in row["status_cls"]) or ("утратив" in row["status"].lower())
        amend = is_amendment(row["title"])
        row["repealed"] = repealed
        row["amendment"] = amend
        d = done.get(ngr.rstrip("_"))
        row["done"] = d or ""
        row["kind"] = "" if (repealed or amend) else classify_kind(row["title"])
        if repealed:
            row["bucket"] = "repealed"
        elif amend:
            row["bucket"] = "amendment"
        elif d:
            row["bucket"] = "done"
        elif row["kind"] != "substantive":
            row["bucket"] = "nonsubst"             # ratif/budget/amnesty/repealer — вне цели
        elif row["type"] in SCOPE_MAIN:
            row["bucket"] = "TODO"                 # цель линковки (осн. scope)
        else:
            row["bucket"] = "edge"                 # УЗАК/УКОН субстантивные — решение владельца

    rows = list(acts.values())
    (ROOT / "maps" / "corpus_registry.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")

    # ── сводка ──
    def sub(pred):
        return [r for r in rows if pred(r)]
    main_rows = sub(lambda r: r["type"] in SCOPE_MAIN)
    bt = Counter(r["bucket"] for r in main_rows)
    by_type_todo = Counter(r["type"] for r in main_rows if r["bucket"] == "TODO")
    nonsub_kind = Counter(r["kind"] for r in main_rows if r["bucket"] == "nonsubst")
    edge = sub(lambda r: r["type"] not in SCOPE_MAIN and not r["repealed"] and not r["amendment"]
               and classify_kind(r["title"]) == "substantive")
    subst_total = bt["TODO"] + bt["done"]           # действующие СУБСТАНТИВНЫЕ (цель) в scope

    L = ["# Реестр корпуса РК — целевые акты (с adilet, по типам)", "",
         f"Собрано уникальных актов (все типы): **{len(rows)}** (listing `va=<ТИП>`, "
         f"status из строки — без покачки доков). Запросов к adilet: {fetches}.", "",
         "## Сверка с оценкой шефа (450-500)", "",
         f"«Все действующие законы» в сыром виде = **{len([r for r in main_rows if not r['repealed'] and not r['amendment']])}** "
         "действующих неамендмент актов — но это ВКЛЮЧАЕТ нерегуляторные:",
         f"- **ratification/treaty** (акты «О ратификации …» — 1-2 статьи, структуры нет): "
         f"**{nonsub_kind['ratification']+nonsub_kind['treaty']}**",
         f"- **республиканский бюджет** (ежегодные): **{nonsub_kind['budget']}**",
         f"- **repealer** («О признании утратившими силу …» — списки отмен, структуры нет): "
         f"**{nonsub_kind['repealer']}**",
         f"- **амнистия/помилование**: **{nonsub_kind['amnesty']}**", "",
         f"→ **СУБСТАНТИВНЫХ регуляторных актов (реальная цель линковки): {subst_total}** "
         f"(сделано {bt['done']} + осталось {bt['TODO']}).", "",
         f"**Вывод (честно):** субстантивных = **{subst_total}**, это НИЖЕ оценки шефа 450-500. "
         "Расхождение объясняется так: (1) сырых «действующих законов» действительно ~1700, из "
         f"них **{nonsub_kind['ratification']+nonsub_kind['treaty']} ратификаций/договоров** "
         "(формально «Закон», но 1-2 статьи — не линкуются), плюс бюджеты/амнистии/repealer; "
         "(2) оценка «38 кодексов сделано» сама завышена — на adilet ВСЕГО "
         f"{sum(1 for r in rows if r['type']=='КОД' and not r['repealed'])} действующих кодексов "
         "(остальные — отменённые старые редакции). Т.е. реальный субстантивный корпус ~300-370, "
         "а 450-500 — вероятно, широкий счёт (с ратификациями) или округление вверх. "
         "**Вопрос владельцу:** ратификации/бюджеты/edge-указы линкуем? (по умолчанию — нет).", "",
         "## Основной scope (Закон + Кодекс + Конституционный закон)", "",
         f"- всего собрано: **{len(main_rows)}**",
         f"- утратили силу (вон): **{bt['repealed']}**  |  поправки (вон): **{bt['amendment']}**",
         f"- нерегуляторные (ratif/budget/amnesty, вне цели): **{bt['nonsubst']}**",
         f"- уже сделано (корпус+пилот): **{bt['done']}**",
         f"- **ОСТАЛОСЬ (TODO, субстантивные действующие): {bt['TODO']}**", "",
         "| тип | TODO субстантивных |", "|---|--:|"]
    for va in SCOPE_MAIN:
        L.append(f"| {va} ({TYPES[va]}) | {by_type_todo.get(va,0)} |")
    n_edge = sum(1 for r in rows if r["bucket"] == "edge")
    L += ["", "## Edge-типы (Указ силы закона/КЗ) — решение владельца",
          f"- действующих субстантивных: **{n_edge}** (в scope НЕ включены; историч. "
          "акты силы закона, напр. «О столице РК»). Включать ли — вопрос владельца.", "",
          "## Разбивка всего собранного", "",
          "| тип | всего | repealed | amend | nonsubst | done | TODO |",
          "|---|--:|--:|--:|--:|--:|--:|"]
    for va in types:
        tr = sub(lambda r, va=va: r["type"] == va)
        c = Counter(r["bucket"] for r in tr)
        L.append(f"| {va} | {len(tr)} | {c['repealed']} | {c['amendment']} | {c['nonsubst']} "
                 f"| {c['done']} | {c['TODO']} |")
    L += ["", f"## TODO — субстантивные действующие ({bt['TODO']}), первые 40", "",
          "| НГР | тип | title |", "|---|---|---|"]
    shown = 0
    for r in main_rows:
        if r["bucket"] == "TODO" and shown < 40:
            L.append(f"| {r['ngr']} | {r['type']} | {r['title'][:70]} |"); shown += 1
    (ROOT / "reports" / "corpus_registry.md").write_text("\n".join(L) + "\n", encoding="utf-8")

    print("\n" + "=" * 64)
    print(f"ВСЕГО уникальных актов: {len(rows)} | запросов к adilet: {fetches}")
    print(f"scope repealed={bt['repealed']} amend={bt['amendment']} nonsubst={bt['nonsubst']} "
          f"done={bt['done']} TODO(subst)={bt['TODO']}")
    print(f"СУБСТАНТИВНЫХ действующих в scope (done+TODO)={subst_total}  (шеф 450-500)")
    print(f"из них ратификаций/договоров исключено: {nonsub_kind['ratification']+nonsub_kind['treaty']}, "
          f"бюджет: {nonsub_kind['budget']}, repealer: {nonsub_kind['repealer']}, амнистии: {nonsub_kind['amnesty']}")
    print(f"Edge (УЗАК/УКОН субстантивных): {sum(1 for r in rows if r['bucket']=='edge')}")
    print("-> maps/corpus_registry.json + reports/corpus_registry.md")


if __name__ == "__main__":
    main()
