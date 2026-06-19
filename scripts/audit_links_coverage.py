"""READ-ONLY АУДИТ: покрытие гиперссылок + корректность резолва + атрибуция.
Ничего не меняет. Источники: final/{code}_structured.html + source/{src}.html.
Запуск:  python scripts/audit_links_coverage.py
Выводит сводку в stdout и собирает структуры для отчёта (см. результат в
global RESULT). Резолвер импортируется канон-скриптами 28/29/30/43.
"""
import io
import sys
import re
import json
from pathlib import Path
from collections import Counter, defaultdict
from bs4 import BeautifulSoup, NavigableString, Tag

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths

ROOT = paths.ROOT
FINAL = paths.FINAL
SRC = paths.SOURCE

CODES = json.loads(paths.CODES_JSON.read_text(encoding="utf-8"))
CODES = {k: v for k, v in CODES.items() if not k.startswith("_")}


def src_path(code):
    """Имя source-файла: поле source в codes.json (иначе {code}.html)."""
    name = CODES.get(code, {}).get("source") or f"{code}.html"
    return SRC / name

# реестр внешних актов: doc_id -> человекочитаемое имя (для PART 2 B)
DOC_NAMES = {
    "K2100000400": "Экологический кодекс",
    "K1400000235": "КоАП",
    "K2000000350": "АППК",
    "K1500000375": "Предпринимательский кодекс",
    "K1400000226": "Уголовный кодекс",
    "K1400000231": "УПК",
    "K1500000414": "Трудовой кодекс",
    "K2500000214": "Налоговый кодекс",
    "K940001000_": "Гражданский кодекс (Общая часть)",
    "K990000409_": "Гражданский кодекс (Особенная часть)",
    "K2300000224": "Социальный кодекс",
    "K030000442_": "Земельный кодекс",
    "K2500000171": "Бюджетный кодекс",
    "K1700000125": "О недрах и недропользовании",
}
# self doc_id по коду
SELF_DOC = {k: v["doc_id"] for k, v in CODES.items()}

# ── регексы кандидатов N_unlinked ───────────────────────────────────────
LINKMARK = " ⟦L⟧ "  # маркер вместо <a>...</a>
# стем «стат…» покрывает все падежи, включая род.мн. «статей» (без ь)
RE_ART = re.compile(r"(?i)\bстат(?:ь[а-яё]{0,3}|ей)\s+(\d+(?:-\d+)?)")
RE_SELF = re.compile(r"(?i)\bнастоящ[а-яё]+\s+(кодекс[а-яё]*|стать[а-яё]+|закон[а-яё]*)")
RE_EXT_KOD = re.compile(r"([А-ЯЁ][а-яё]+(?:им|ым|ого|ому|ом|ой|ий|ый))\s+кодекс[а-яё]{0,3}")
# Только КОНКРЕТНЫЙ именованный/датированный закон, чьё имя НЕ в <a> (не маркер ⟦L⟧):
# после кавычки идёт кириллическая заглавная (имя «О …») ИЛИ дата «от N».
RE_ZAKON = re.compile(
    r"Закон[а-яё]{0,3}\s+(?:Республики Казахстан|РК)\s*"
    r"(?:от\s+\d|[«\"„]\s*[А-ЯЁ])")
# Конституция как ДОКУМЕНТ (исключаем "Конституционный Суд/закон")
RE_KONST = re.compile(r"(?i)\bконституци(?:я|и|ю|ей|ею|е)\b")
# дженерик "законами/законах РК" — считаем отдельно как заведомый FP-класс
RE_ZAKON_GENERIC = re.compile(r"(?i)\bзакон(?:ами|ах|ов|а|е|ом)?\s+(?:Республики Казахстан|РК)")

# заголовок статьи (для резолва R) — гомоглиф-толерантно
C_HG = "[СCϹ]"
RE_ARTTITLE = re.compile(rf"^\s*{C_HG}тать[яиею]\s+(\d+(?:-\d+)?)\s*\.")


def content_root(soup):
    """Скоуп = все div[data-type]; ссылки в шапке/подвале вне их."""
    return soup.find_all("div", attrs={"data-type": True})


def in_link(node):
    return node.find_parent("a") is not None


def classify_href(href, self_doc):
    """internal | external | nav"""
    h = href.strip()
    if h.startswith("#"):
        return "internal", None
    if h.startswith("javascript") or h.startswith("mailto"):
        return "nav", None
    m = re.search(r"/docs/([A-Z]\d{6,}_?)", h)
    if m:
        doc = m.group(1)
        if doc == self_doc:
            return "internal", doc
        return "external", doc
    # прочий http (навигация adilet, gov, zqai...)
    return "nav", None


BLOCK_TAGS = {"p", "li", "div", "h1", "h2", "h3", "h4", "h5", "h6",
              "tr", "table", "blockquote", "ul", "ol"}


def flatten_lines(el):
    """Линеаризует текст элемента в «логические строки» (разрыв по <br> и
    блочным тегам). Каждое <a>...</a> → маркер ⟦L⟧ (число в <a> не клеится к
    слову снаружи). Захватывает ВЕСЬ текст независимо от обёртки (важно для
    УПК, где тело идёт прямо в div через <br>, а не в <p>)."""
    lines = []
    cur = []

    def flush():
        if cur:
            lines.append("".join(cur))
            cur.clear()

    def walk(node):
        for ch in node.children:
            if isinstance(ch, NavigableString):
                cur.append(str(ch))
            elif isinstance(ch, Tag):
                if ch.name == "a":
                    cur.append(LINKMARK)
                elif ch.name == "br":
                    flush()
                elif ch.name in BLOCK_TAGS:
                    flush(); walk(ch); flush()
                else:  # span, font, b, i, sup… — inline
                    walk(ch)

    walk(el)
    flush()
    return lines


def analyze_code(code):
    fpath = FINAL / f"{code}_structured.html"
    if not fpath.exists():
        return None
    self_doc = SELF_DOC.get(code, "")
    soup = BeautifulSoup(fpath.read_text(encoding="utf-8"), "html.parser")
    blocks = content_root(soup)

    # ---- N_linked ----
    n_int = n_ext = n_nav = 0
    ext_docs = Counter()
    # все <a href> внутри контента (берём из article-divs верхнего уровня,
    # чтобы не считать дважды вложенные div — используем soup-wide, но фильтр по data-type ancestor)
    seen = set()
    for a in soup.find_all("a", href=True):
        if not a.find_parent("div", attrs={"data-type": True}):
            continue
        if id(a) in seen:
            continue
        seen.add(id(a))
        kind, doc = classify_href(a["href"], self_doc)
        if kind == "internal":
            n_int += 1
        elif kind == "external":
            n_ext += 1
            ext_docs[doc] += 1
        else:
            n_nav += 1

    # ---- N_unlinked + примеры ----
    unl = Counter()
    examples = []
    # Тело берём из статья-div (лист контента) и линеаризуем — захватывает ВЕСЬ
    # текст (в т.ч. УПК с <br>), исключаем двойной счёт контейнеров глава/раздел.
    art_divs = [b for b in blocks if b.get("data-type") == "статья"]
    lines = []
    for div in art_divs:
        for ln in flatten_lines(div):
            # пропускаем строку-ЗАГОЛОВОК статьи («Статья N. Название»)
            if RE_ARTTITLE.match(ln.replace(LINKMARK, " ").strip()):
                continue
            lines.append(ln)

    # редакционно-сносочный контекст (ИЗПИ-пометки, история изменений) — не отсылки
    EDIT = ("вводится в действие", "действует до", "в редакции", "Заголовок",
            "Сноска", "изложен", "исключен", "исключён", "дополнен", "внесен",
            "внесён", "предусматривается в редакции", "приостанов")
    n_fp_edit = 0

    def is_editorial(ctx):
        return any(k in ctx for k in EDIT)

    def add_ex(ptype, m, txt, fp=False):
        s = max(0, m.start() - 45)
        e = min(len(txt), m.end() + 35)
        ctx = re.sub(r"\s+", " ", txt[s:e]).strip()
        examples.append((ptype, re.sub(r"\s+", " ", m.group(0)).strip(), ctx, fp))

    fp_generic_zakon = 0
    for txt in lines:
        for m in RE_ART.finditer(txt):
            unl["internal:статья N"] += 1
            ctx = txt[max(0, m.start() - 45):m.end() + 35]
            fp = is_editorial(ctx) or bool(re.match(
                r"(?i)\s*Стать[яиею]\s+\d+(?:-\d+)?\s+(вводится|действует|приостан)", txt[m.start():]))
            if fp:
                n_fp_edit += 1
            add_ex("internal:статья N", m, txt, fp)
        for m in RE_SELF.finditer(txt):
            unl["internal:настоящего Кодекса/статьи"] += 1
            add_ex("internal:настоящего", m, txt)
        for m in RE_EXT_KOD.finditer(txt):
            if m.group(1).lower().startswith("настоящ"):
                continue
            unl["external:<Прил> кодекс"] += 1
            add_ex("external:кодекс", m, txt)
        for m in RE_ZAKON.finditer(txt):
            unl["external:Закон РК (именован.)"] += 1
            ctx = txt[max(0, m.start() - 10):m.end() + 45]
            fp = bool(re.search(r"от\s+\d", m.group(0))) and is_editorial(ctx)
            if fp:
                n_fp_edit += 1
            add_ex("external:закон", m, txt, fp)
        for m in RE_KONST.finditer(txt):
            unl["external:Конституция"] += 1
            add_ex("external:конституция", m, txt)
        # дженерик-класс (НЕ входит в n_unl, считаем для FP-отчёта)
        fp_generic_zakon += len(RE_ZAKON_GENERIC.findall(txt))

    # настоящего Кодекса/статьи = генерик-самоотсылки (ни мы, ни adilet не линкуем)
    n_self_generic = unl.get("internal:настоящего Кодекса/статьи", 0)
    n_unl = sum(unl.values())
    n_unl_content = n_unl - n_self_generic  # без генерик-самоотсылок
    n_unl_real = n_unl_content - n_fp_edit  # ещё и без редакц./сносочных FP
    n_link = n_int + n_ext
    cov_lit = n_link / (n_link + n_unl) if (n_link + n_unl) else 0.0
    cov_content = n_link / (n_link + n_unl_content) if (n_link + n_unl_content) else 0.0
    cov_real = n_link / (n_link + n_unl_real) if (n_link + n_unl_real) else 0.0

    # ---- дубли id ----
    ids = [t.get("id") for t in soup.find_all(attrs={"id": True})]
    dup_ids = {k: v for k, v in Counter(ids).items() if v > 1}

    return {
        "code": code, "self_doc": self_doc,
        "n_int": n_int, "n_ext": n_ext, "n_nav": n_nav,
        "n_linked": n_link, "n_unlinked": n_unl,
        "n_unl_content": n_unl_content, "n_self_generic": n_self_generic,
        "n_unl_real": n_unl_real, "n_fp_edit": n_fp_edit,
        "fp_generic_zakon": fp_generic_zakon,
        "coverage": cov_lit, "coverage_content": cov_content, "coverage_real": cov_real,
        "unl_breakdown": dict(unl),
        "ext_docs": dict(ext_docs),
        "examples": examples,
        "dup_ids": dup_ids,
        "soup": soup,
    }


# ════════════════════════ PART 2 — КОРРЕКТНОСТЬ ════════════════════════
RE_ART_IN = re.compile(r"(?i)стат(?:ь[а-яё]{0,3}|ей)\s+(\d+(?:-\d+)?)")
RE_NUM_ONLY = re.compile(r"^\s*(\d+(?:-\d+)?)\s*\)?\s*$")
RE_ART_TAIL = re.compile(r"(?i)стать[а-яё]{0,3}\s*$")
RE_PUNKT_TAIL = re.compile(r"(?i)(пункт[а-яё]{0,3}|част[а-яё]{0,3}|подпункт[а-яё]{0,3})\s*$")


RE_ZID = re.compile(r"^z\d")


def build_id_to_art(soup):
    """Резолв id(zK) -> номер целевой статьи по СЕМАНТИКЕ adilet.

    Якоря adilet ставятся ПЕРЕД заголовком статьи, поэтому структуризатор
    «затягивает» якорь начала ст.N в контейнер предыдущей ст.(N-1).
    Поэтому резолвим прямым проходом по документу: если сразу за якорем идёт
    заголовок «Статья M.» (до любого тела) — цель = M; иначе — цель = статья,
    в теле которой стоит якорь (последний заголовок перед якорем).

    Возвращает (id2art_target, all_ids, art_numbers_set)."""
    events = []  # ('H',M) | ('B',) | ('BE',) редакц.-вставка | ('A',idval)
    all_ids = set()
    art_numbers = set()

    def is_note(t):
        # ИЗПИ/редакционные вставки, которые adilet ставит МЕЖДУ якорем начала
        # статьи и её заголовком — не настоящее тело, при резолве пропускаем.
        if t.startswith("Примечание") or t.startswith("Сноска") or t.startswith("См."):
            return True
        return bool(re.match(
            r"(?i)Стать[яи]\s+\d+(?:-\d+)?\s+(действует|вводит|приостан|исключ|изложен)", t))

    def walk(node):
        # документ-порядок: id-якоря и текстовые узлы вперемешку. Заголовки
        # «Статья N.» могут быть как в <p>/<h3>, так и ГОЛЫМ текстом (УПК).
        for ch in node.children:
            if isinstance(ch, NavigableString):
                t = str(ch).strip()
                if t:
                    mt = RE_ARTTITLE.match(t)
                    if mt:
                        events.append(("H", mt.group(1)))
                        art_numbers.add(mt.group(1))
                    elif is_note(t):
                        events.append(("BE",))
                    else:
                        events.append(("B",))
            elif isinstance(ch, Tag):
                iid = ch.get("id")
                if iid:
                    all_ids.add(iid)
                    if RE_ZID.match(iid):
                        events.append(("A", iid))
                walk(ch)

    walk(soup.body or soup)
    # last heading at/before each index
    n = len(events)
    last_h = [None] * n
    c = None
    for i, e in enumerate(events):
        if e[0] == "H":
            c = e[1]
        last_h[i] = c
    id2art = {}   # «телесный» резолв: где якорь физически стоит
    id2next = {}  # ближайший заголовок ПОСЛЕ якоря (для якорей-закладок начала статьи)
    for i, e in enumerate(events):
        if e[0] != "A":
            continue
        tgt = None
        nh = None
        for j in range(i + 1, n):
            if events[j][0] == "H":
                nh = events[j][1]
                if tgt is None:
                    tgt = events[j][1]
                break
            if events[j][0] == "B" and tgt is None:
                tgt = last_h[i]
                # не break: продолжаем искать ближайший заголовок для id2next
        if tgt is None:
            tgt = last_h[i]
        id2art[e[1]] = tgt
        id2next[e[1]] = nh
    # дополним номера статей из data-number (на случай статей без заголовка)
    for d in soup.find_all("div", attrs={"data-type": "статья"}):
        dn = d.get("data-number")
        if dn:
            art_numbers.add(dn)
    return id2art, all_ids, art_numbers, id2next


def preceding_text(a, maxlen=60):
    buf = ""
    for sib in a.previous_siblings:
        buf = (sib.get_text(" ") if isinstance(sib, Tag) else str(sib)) + buf
        if len(buf) >= maxlen:
            break
    return re.sub(r"\s+", " ", buf)[-maxlen:]


def claimed_article(a):
    """Возвращает (kind, N): kind in ARTICLE|SELF|NONART."""
    lt = a.get_text(" ", strip=True)
    if re.search(r"(?i)настоящ\w+\s+стать", lt):
        return "SELF", None
    m = RE_ART_IN.search(lt)
    if m:
        return "ARTICLE", m.group(1)
    prev = preceding_text(a)
    if re.search(r"(?i)настоящ\w+\s+стать", prev[-25:]) and "стать" not in lt:
        return "SELF", None
    if RE_NUM_ONLY.match(lt):
        if RE_ART_TAIL.search(prev):
            return "ARTICLE", RE_NUM_ONLY.match(lt).group(1)
        if RE_PUNKT_TAIL.search(prev):
            return "NONART", None
    return "NONART", None


def analyze_correctness(r):
    code = r["code"]; soup = r["soup"]; self_doc = r["self_doc"]
    id2art, all_ids, art_numbers, id2next = build_id_to_art(soup)
    # источник: множество fragment-анкеров (zK), на которые ссылались в source
    src = src_path(code)
    src_frags = set()
    if src.exists():
        ssoup = BeautifulSoup(src.read_text(encoding="utf-8", errors="replace"), "html.parser")
        for sa in ssoup.find_all("a", href=True):
            fm = re.search(r"#(z\d+[\w-]*)", sa["href"])
            if fm:
                src_frags.add(fm.group(1))

    rows = {"OK": 0, "WRONG_TARGET": [], "WRONG_SUB": [], "BROKEN": [],
            "SELF_OK": 0, "SELF_WRONG": [], "NONART": 0}
    for a in soup.find_all("a", href=True):
        if not a.find_parent("div", attrs={"data-type": True}):
            continue
        kind, doc = classify_href(a["href"], self_doc)
        if kind != "internal":
            continue
        fm = re.search(r"#(z\d+[\w-]*)", a["href"])
        if not fm:  # внутренний, но без fragment (редко)
            continue
        zk = fm.group(1)
        host_art = None
        hd = a.find_parent("div", attrs={"data-type": "статья"})
        if hd is not None:
            for el in hd.find_all(["h2", "h3", "h4", "p"], recursive=True):
                mt = RE_ARTTITLE.match(el.get_text(" ", strip=True))
                if mt:
                    host_art = mt.group(1); break
            if host_art is None:
                host_art = hd.get("data-number")
        ck, cn = claimed_article(a)
        inherited = zk in src_frags
        if zk not in all_ids:
            rows["BROKEN"].append({
                "art": host_art, "text": a.get_text(" ", strip=True)[:40],
                "href": a["href"], "claimed": cn, "inherited": inherited})
            continue
        R = id2art.get(zk)
        Rn = id2next.get(zk)  # ближайший заголовок после якоря (закладка начала статьи)
        # множество приемлемых целей: «телесный» резолв + следующий заголовок
        # (якорь-закладка ставится перед заголовком, иногда с ИЗПИ-вставкой между)
        acc = {str(R), str(Rn)}
        if ck == "SELF":
            if str(host_art) in acc:
                rows["SELF_OK"] += 1
            else:
                rows["SELF_WRONG"].append({
                    "art": host_art, "text": a.get_text(" ", strip=True)[:40],
                    "href": a["href"], "resolved": R, "inherited": inherited})
        elif ck == "ARTICLE":
            cn_str = str(cn)
            if "-" in cn_str and cn_str not in art_numbers:
                # диапазон «A-B» (под-статьи A-B нет): корректно вести на начало A
                start = cn_str.split("-")[0]
                if start in acc:
                    rows["OK"] += 1
                else:
                    rows["WRONG_TARGET"].append({
                        "art": host_art, "text": a.get_text(" ", strip=True)[:40],
                        "href": a["href"], "claimed": cn, "resolved": R,
                        "inherited": inherited, "range": True})
            elif "-" in cn_str and cn_str in art_numbers and cn_str not in acc:
                # под-статья «A-B» существует, но ссылка ведёт на базовую A
                rows["WRONG_SUB"].append({
                    "art": host_art, "text": a.get_text(" ", strip=True)[:40],
                    "href": a["href"], "claimed": cn, "resolved": R,
                    "inherited": inherited})
            elif cn_str in acc:
                rows["OK"] += 1
            else:
                rows["WRONG_TARGET"].append({
                    "art": host_art, "text": a.get_text(" ", strip=True)[:40],
                    "href": a["href"], "claimed": cn, "resolved": R,
                    "inherited": inherited, "range": False})
        else:
            rows["NONART"] += 1

    # внешние: doc_id известен/неизвестен + сверка имени.
    # ВАЖНО: имя акта берём из ВИДИМОГО текста ссылки (+1-2 слова перед, если
    # текст — голый номер), НЕ из окружающей прозы (иначе «налог…» из тела НК
    # ложно срабатывает). Среди совпавших подсказок выбираем САМУЮ ДЛИННУЮ
    # (чтобы «уголовно-процессуальн» побеждал «уголовн»).
    ext = {"known": Counter(), "unknown": Counter(), "name_mismatch": []}
    NAME_HINTS = {  # ключ-слово в ИМЕНИ акта -> ожидаемый doc_id
        "экологическ": "K2100000400",
        "об административных правонарушени": "K1400000235",
        "административных правонарушени": "K1400000235",
        "административн": "K2000000350", "предпринимательск": "K1500000375",
        "уголовно-процессуальн": "K1400000231", "уголовн": "K1400000226",
        "трудов": "K1500000414", "налогов": "K2500000214",
        "социальн": "K2300000224", "земельн": "K030000442_",
        "бюджетн": "K2500000171", "о недрах": "K1700000125",
    }
    for a in soup.find_all("a", href=True):
        if not a.find_parent("div", attrs={"data-type": True}):
            continue
        kind, doc = classify_href(a["href"], self_doc)
        if kind != "external":
            continue
        if doc in DOC_NAMES:
            ext["known"][doc] += 1
        else:
            ext["unknown"][doc] += 1
        name = a.get_text(" ", strip=True).lower()
        if re.fullmatch(r"[\s\d).,;№-]*", name):  # голый номер/пусто — добавим слова перед
            name = (preceding_text(a, 60)[-60:] + " " + name).lower()
        best = None  # (длина_хинта, hint, exp)
        for hint, exp in NAME_HINTS.items():
            if hint in name and (best is None or len(hint) > best[0]):
                best = (len(hint), hint, exp)
        if best and doc in DOC_NAMES and doc != best[2]:
            ext["name_mismatch"].append({
                "art": (a.find_parent('div', attrs={'data-type': 'статья'}) or {}).get("data-number")
                if a.find_parent('div', attrs={'data-type': 'статья'}) else None,
                "hint": best[1], "expected": best[2], "actual": doc,
                "text": a.get_text(" ", strip=True)[:40]})

    r["correct"] = rows
    r["ext_audit"] = ext
    return r


def main():
    order = ["nalog", "trudovoy", "grazhdanskiy", "grazhdanskiy_osob",
             "predprinimatel", "socialnyy", "ekologicheskiy", "zemelnyy",
             "upk", "koap", "appk", "byudzhet", "ugolovniy", "informatizacii",
             "notariat", "obrazovanie",
             "arbitrazh", "goszakup", "ocorrupt", "bezhenci", "zhilishniy"]
    # добор всех остальных кодов из codes.json (пропущенные + новые доки),
    # чтобы покрытие считалось по ВСЕМ 34, а не по застывшему списку
    order += [c for c in CODES if c not in order]
    results = []
    for code in order:
        r = analyze_code(code)
        if r:
            results.append(r)

    print("=" * 100)
    print("PART 1 — ПОКРЫТИЕ  (cov_lit = по ТЗ; cov_cont = без генерик-самоотсылок 'настоящего Кодекса')")
    print("=" * 100)
    print(f"{'код':18}{'LINKED':>8}{'UNL':>7}{'самоотс':>8}{'редФП':>7}"
          f"{'cov_lit':>9}{'cov_cont':>10}{'cov_real':>10}")
    tot_l = tot_u = tot_uc = tot_self = tot_ur = tot_fp = 0
    for r in results:
        tot_l += r["n_linked"]; tot_u += r["n_unlinked"]
        tot_uc += r["n_unl_content"]; tot_self += r["n_self_generic"]
        tot_ur += r["n_unl_real"]; tot_fp += r["n_fp_edit"]
        print(f"{r['code']:18}{r['n_linked']:>8}{r['n_unlinked']:>7}{r['n_self_generic']:>8}"
              f"{r['n_fp_edit']:>7}{r['coverage']*100:>8.1f}%"
              f"{r['coverage_content']*100:>9.1f}%{r['coverage_real']*100:>9.1f}%")
    cov_l = tot_l / (tot_l + tot_u) if (tot_l + tot_u) else 0
    cov_c = tot_l / (tot_l + tot_uc) if (tot_l + tot_uc) else 0
    cov_r = tot_l / (tot_l + tot_ur) if (tot_l + tot_ur) else 0
    print("-" * 100)
    print(f"{'ОБЩИЙ':18}{tot_l:>8}{tot_u:>7}{tot_self:>8}{tot_fp:>7}"
          f"{cov_l*100:>8.1f}%{cov_c*100:>9.1f}%{cov_r*100:>9.1f}%")

    print("\nРазбивка UNLINKED по паттернам (сумма по всем кодексам):")
    agg = Counter()
    for r in results:
        for k, v in r["unl_breakdown"].items():
            agg[k] += v
    for k, v in agg.most_common():
        print(f"  {k:42}{v:>7}")

    print("\nFP редакц./сносочные (Статья N вводится/действует; Закон от <дата>...): "
          f"{tot_fp} | генерик-самоотсылки: {tot_self}")

    print("\n15-20 СЫРЫХ примеров UNLINKED (разные коды/паттерны; [FP]=ложное):")
    pool = []
    for r in results:
        for ptype, ph, ctx, fp in r["examples"]:
            pool.append((r["code"], ptype, ph, ctx, fp))
    bykind = defaultdict(list)
    for code, ptype, ph, ctx, fp in pool:
        kk = ptype.split(":")[0] + ":" + ptype.split(":")[1]
        bykind[kk].append((code, ph, ctx, fp))
    rr = []
    keys = list(bykind.keys())
    idx = 0
    while len(rr) < 20 and any(bykind[k] for k in keys):
        k = keys[idx % len(keys)]
        if bykind[k]:
            rr.append((k, bykind[k].pop(0)))
        idx += 1
    for k, (code, ph, ctx, fp) in rr:
        tag = "[FP] " if fp else "     "
        print(f"  {tag}[{code:14}|{k:26}] «{ph}»  …{re.sub(chr(10),' ',ctx)}…")

    # ---- PART 2 ----
    for r in results:
        analyze_correctness(r)

    print("\n" + "=" * 100)
    print("PART 2 — КОРРЕКТНОСТЬ (внутр. <a href=#zK>: claimed N из текста vs резолв R=#zK→статья)")
    print("=" * 100)
    print(f"{'код':18}{'OK':>6}{'WRONG':>7}{'SUB':>5}{'BROKEN':>7}{'SELF_OK':>9}"
          f"{'SELF_W':>8}{'NONART':>8}{'dupID':>7}")
    T = Counter()
    for r in results:
        c = r["correct"]
        wt, ws, bk, sw = (len(c["WRONG_TARGET"]), len(c["WRONG_SUB"]),
                          len(c["BROKEN"]), len(c["SELF_WRONG"]))
        dup = len(r["dup_ids"])
        T["OK"] += c["OK"]; T["WT"] += wt; T["WS"] += ws; T["BK"] += bk
        T["SO"] += c["SELF_OK"]; T["SW"] += sw; T["NA"] += c["NONART"]; T["DUP"] += dup
        print(f"{r['code']:18}{c['OK']:>6}{wt:>7}{ws:>5}{bk:>7}{c['SELF_OK']:>9}{sw:>8}"
              f"{c['NONART']:>8}{dup:>7}")
    print("-" * 100)
    print(f"{'ИТОГО':18}{T['OK']:>6}{T['WT']:>7}{T['WS']:>5}{T['BK']:>7}{T['SO']:>9}"
          f"{T['SW']:>8}{T['NA']:>8}{T['DUP']:>7}")
    print("  (WRONG=ст.N ведёт не на N; SUB=под-статья N-K ведёт на базовую N; "
          "BROKEN=#z нет в документе)")

    print("\nВнешние ссылки: known doc_id vs unknown(NGR) + несоответствия имя↔doc_id:")
    for r in results:
        ea = r["ext_audit"]
        nk = sum(ea["known"].values()); nu = sum(ea["unknown"].values())
        mm = len(ea["name_mismatch"])
        print(f"  {r['code']:18} known={nk:>5} unknown/NGR={nu:>5} name_mismatch={mm}")

    print("\nWRONG_TARGET / WRONG_SUB / BROKEN / SELF_WRONG (детально, все коды):")
    for r in results:
        c = r["correct"]
        for w in c["WRONG_TARGET"]:
            print(f"  WRONG  [{r['code']}] ст.{w['art']} «{w['text']}» {w['href']} "
                  f"заявл={w['claimed']} резолв={w['resolved']} "
                  f"{'унасл' if w['inherited'] else 'НАШЕ'}")
        for w in c["WRONG_SUB"]:
            print(f"  SUB    [{r['code']}] ст.{w['art']} «{w['text']}» {w['href']} "
                  f"заявл={w['claimed']} резолв={w['resolved']} "
                  f"{'унасл' if w['inherited'] else 'НАШЕ'}")
        for w in c["BROKEN"]:
            print(f"  BROKEN [{r['code']}] ст.{w['art']} «{w['text']}» {w['href']} "
                  f"{'унасл' if w['inherited'] else 'НАШЕ'}")
        for w in c["SELF_WRONG"]:
            print(f"  SELFW  [{r['code']}] ст.{w['art']} «{w['text']}» {w['href']} "
                  f"резолв={w['resolved']} {'унасл' if w['inherited'] else 'НАШЕ'}")
    for r in results:
        for mm in r["ext_audit"]["name_mismatch"]:
            print(f"  WRONG_DOC [{r['code']}] ст.{mm['art']} «{mm['text']}» "
                  f"hint='{mm['hint']}' ожид={mm['expected']} факт={mm['actual']}")

    global RESULT
    RESULT = results
    return results


if __name__ == "__main__":
    main()
