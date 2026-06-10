"""
ТЗ-Ф2 (Трудовой кодекс) — классификация + фикс 82 пунктов.
v2: правильная детекция «ссылка уже есть» по факту наличия <a href="#zN..."> или
    <a href="...doc_id..."> внутри диапазона статьи.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HTML = ROOT / "data" / "final" / "trudovoy_structured.html"
CODES_JSON = ROOT / "config" / "codes.json"
MISSING_LOG = ROOT / "data" / "reports" / "TZ05_missing_anchors.json"

codes_cfg = json.loads(CODES_JSON.read_text(encoding="utf-8"))
DOC = {k: v["doc_id"] for k, v in codes_cfg.items() if not k.startswith("_")}

# Doc_id внешних законов (уже встречаются в корпусе)
LAW_DOC = {
    "акционерных_обществах":        "Z030000415_",
    "противодействии_коррупции":    "Z1500000410",
    "воздушного_пространства":      "Z2000000321",
    "регулировании_финансового":    "Z030000474_",
    "военном_положении":            "Z030000391_",
    "чрезвычайном_положении":       "Z030000387_",
    "исполнительном_производстве":  "Z2000000349",
    "обязательном_страховании":     "Z050000030_",
    "респ_бюджете":                 "Z2500000239",
}

text = HTML.read_text(encoding="utf-8")
orig_text = text

# ── индекс статей ────────────────────────────────────────────────────
ARTICLE_RE = re.compile(
    r'<div class="article" data-number="([^"]+)" data-type="статья" id="w_z[^"]+">'
)
article_spans = {}
_m = list(ARTICLE_RE.finditer(text))
for i, m in enumerate(_m):
    n = m.group(1)
    s = m.start()
    e = _m[i + 1].start() if i + 1 < len(_m) else len(text)
    if n not in article_spans:
        article_spans[n] = (s, e)

ANCHOR_SET = set(re.findall(r'\b(?:id|name)\s*=\s*"(z[0-9][0-9a-zA-Z_-]*)"', text))

# ── результаты ───────────────────────────────────────────────────────
results = []
missing_anchors = []
new_links_added = 0


def log(item_id, locator, ref, kind, before, after, snippet=""):
    results.append({"id": item_id, "locator": locator, "ref": ref,
                    "type": kind, "before": before, "after": after,
                    "snippet": snippet[:160]})


def get_range(num):
    return article_spans.get(str(num))


def is_inside_anchor(haystack, pos):
    snip = haystack[:pos]
    lo = max(snip.rfind("<a "), snip.rfind("<a\n"))
    lc = snip.rfind("</a>")
    return lo > lc


# ── проверить, есть ли ссылка в статье ───────────────────────────────
def has_internal_link(article_num, target_anchor):
    rng = get_range(article_num)
    if not rng:
        return False, None
    snip = text[rng[0]:rng[1]]
    m = re.search(
        rf'<a[^>]+href="#{re.escape(target_anchor)}(?:_[A-Za-z0-9_-]+)?"[^>]*>([^<]+)</a>',
        snip,
    )
    if m:
        return True, m.group(0)[:140]
    return False, None


def has_external_link(article_num, doc_id):
    rng = get_range(article_num)
    if not rng:
        return False, None
    snip = text[rng[0]:rng[1]]
    m = re.search(
        rf'<a[^>]+href="https?://[^"]*docs/{re.escape(doc_id)}[^"]*"[^>]*>([^<]+)</a>',
        snip,
    )
    if m:
        return True, m.group(0)[:140]
    return False, None


# ── классификация одного пункта ──────────────────────────────────────
def check_internal(item_id, locator, article_num, ref_phrase, target_anchor):
    """Внутренняя ссылка. Если уже есть <a href=#z<anchor>...> в статье → DONE."""
    if target_anchor not in ANCHOR_SET:
        missing_anchors.append({"item": item_id, "anchor": target_anchor,
                                "locator": locator})
        log(item_id, locator, ref_phrase, "internal",
            "MISSING", "MISSING-anchor-absent",
            f"якорь #{target_anchor} отсутствует")
        return
    ok, example = has_internal_link(article_num, target_anchor)
    if ok:
        log(item_id, locator, ref_phrase, "internal", "DONE", "DONE", example)
    else:
        # MISSING: пытаемся обернуть плотный паттерн ref_phrase в статье
        rng = get_range(article_num)
        if not rng:
            log(item_id, locator, ref_phrase, "internal", "MISSING",
                "NO-ARTICLE", f"статья {article_num} не найдена")
            return
        snip = text[rng[0]:rng[1]]
        idx = snip.find(ref_phrase)
        if idx == -1:
            log(item_id, locator, ref_phrase, "internal", "MISSING",
                "NOT-FOUND-IN-ARTICLE",
                f"фраза не найдена в ст.{article_num} (для оборачивания)")
            return
        abs_pos = rng[0] + idx
        if is_inside_anchor(text, abs_pos):
            log(item_id, locator, ref_phrase, "internal", "DONE",
                "DONE-overlapping", "вхождение уже внутри <a>")
            return
        new_html = f'<a href="#{target_anchor}">{ref_phrase}</a>'
        _apply_replace(abs_pos, len(ref_phrase), new_html)
        log(item_id, locator, ref_phrase, "internal", "MISSING", "FIXED",
            f"обёрнуто → #{target_anchor}")


def check_external(item_id, locator, article_num, ref_phrase, doc_id):
    """Внешняя ссылка. Если уже есть <a href=...doc_id...> в статье → DONE."""
    ok, example = has_external_link(article_num, doc_id)
    if ok:
        log(item_id, locator, ref_phrase, "external", "DONE", "DONE", example)
    else:
        # MISSING — обернуть
        rng = get_range(article_num)
        if not rng:
            log(item_id, locator, ref_phrase, "external", "MISSING",
                "NO-ARTICLE", f"статья {article_num} не найдена")
            return
        snip = text[rng[0]:rng[1]]
        idx = snip.find(ref_phrase)
        if idx == -1:
            log(item_id, locator, ref_phrase, "external", "MISSING",
                "NOT-FOUND-IN-ARTICLE", "фраза не найдена для оборачивания")
            return
        abs_pos = rng[0] + idx
        if is_inside_anchor(text, abs_pos):
            log(item_id, locator, ref_phrase, "external", "DONE",
                "DONE-overlapping", "уже внутри <a>")
            return
        new_html = (f'<a href="https://adilet.zan.kz/rus/docs/{doc_id}">'
                    f'{ref_phrase}</a>')
        _apply_replace(abs_pos, len(ref_phrase), new_html)
        log(item_id, locator, ref_phrase, "external", "MISSING", "FIXED",
            f"обёрнуто → {doc_id}")


def _apply_replace(pos, length, new_html):
    global text, new_links_added
    text = text[:pos] + new_html + text[pos + length:]
    new_links_added += 1
    # пересобираем article_spans, т.к. длина изменилась
    _rebuild_spans()


def _rebuild_spans():
    global article_spans
    matches = list(ARTICLE_RE.finditer(text))
    article_spans = {}
    for i, m in enumerate(matches):
        n = m.group(1)
        s = m.start()
        e = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        if n not in article_spans:
            article_spans[n] = (s, e)


# ── проверка наличия якоря (для TKX) ─────────────────────────────────
def verify_anchor(item_id, locator, target_anchor, article_num=None):
    if target_anchor in ANCHOR_SET:
        log(item_id, locator, f"якорь #{target_anchor}", "anchor-check",
            "EXISTS", "DONE", f'id="{target_anchor}" найден')
        return
    # альтернатива: статья с таким data-number существует — найдём её
    # внутренний z-якорь (например, ст.182-1 → z1156)
    if article_num is not None:
        rng = get_range(article_num)
        if rng:
            snip = text[rng[0]:rng[0] + 400]
            m = re.search(r'id="(z\d+(?:-\d+)?)"', snip)
            if m:
                log(item_id, locator,
                    f"якорь #{target_anchor} (альтернатива #{m.group(1)})",
                    "anchor-check", "ALT", "DONE",
                    f'статья {article_num} имеет якорь #{m.group(1)}')
                return
    log(item_id, locator, f"якорь #{target_anchor}", "anchor-check",
        "MISSING", "MISSING-anchor", f'id="{target_anchor}" отсутствует')


# ── проверка: в сноске нет <a> ──────────────────────────────────────
def verify_note_no_link(item_id, locator, article_num, hint=""):
    rng = get_range(article_num)
    if rng is None:
        log(item_id, locator, hint, "note-strip", "ERROR", "NO-ARTICLE",
            f"статья {article_num} не найдена")
        return
    snip = text[rng[0]:rng[1]]
    # ищем <a HREF (а не просто <a id/name) внутри <span class="note">…</span>
    note_segments = re.findall(r'<span class="note">.*?</span>', snip)
    links_in_notes = sum(len(re.findall(r'<a[^>]+href=', s))
                         for s in note_segments)
    if links_in_notes == 0:
        log(item_id, locator, hint, "note-strip", "DONE", "DONE",
            f"в сносках статьи {article_num} ссылок нет")
    else:
        log(item_id, locator, hint, "note-strip", "LINK-REMAINS",
            "NOTE-NEEDS-STRIP",
            f"в сносках ст.{article_num} осталось {links_in_notes} <a>")


# ──────────────────────────────────────────────────────────────────
# TK-секция (Word) — 45 пунктов
# ──────────────────────────────────────────────────────────────────
log("TK-001", "header", "№ Наименование Примечание 1", "header", "N/A", "SKIP",
    "заголовок таблицы")
log("TK-002", "label", "Подпункт 27 п.2 ст.23", "label", "N/A", "SKIP",
    "координаты для TK-003")

check_internal("TK-003", "ст.23 п.2 пп.27", "23",
               "подпунктами 1), 2), 3), 4), 5) и 13) пункта 1 статьи 28", "z28")
check_internal("TK-003b", "ст.23 п.2 пп.27", "23",
               "статьей 99 настоящего Кодекса", "z99")

log("TK-004", "label", "пп.2 п.1 ст.30", "label", "N/A", "SKIP",
    "координаты для TK-005")
check_internal("TK-005", "ст.30 п.1 пп.2", "30",
               "пунктом 2 статьи 51 настоящего Кодекса", "z51")

log("TK-006", "label", "пп.23,24 п.1 ст.52", "label", "N/A", "SKIP",
    "координаты для TK-007/008")
check_external("TK-007", "ст.52 п.1 пп.23", "52",
               'Законом Республики Казахстан "Об акционерных обществах"',
               LAW_DOC["акционерных_обществах"])
check_external("TK-008", "ст.52 п.1 пп.24", "52",
               "Социальным кодексом Республики Казахстан", DOC["socialnyy"])

log("TK-009", "label", "п.1 ст.65", "label", "N/A", "SKIP", "координаты для TK-010")
check_internal("TK-010", "ст.65 п.1", "65",
               "статьи 66 настоящего Кодекса", "z66")

log("TK-011", "label", "п.4 ст.73", "label", "N/A", "SKIP", "координаты для TK-012")
check_internal("TK-012", "ст.73 п.4", "73",
               "статьей 86 настоящего Кодекса", "z86")

log("TK-013", "label", "п.2 ст.103", "label", "N/A", "SKIP", "координаты для TK-014")
check_internal("TK-014", "ст.103 п.2", "103",
               "частью второй пункта 2 статьи 75 настоящего Кодекса", "z75")

log("TK-015", "label", "п.4 ст.127-3", "label", "N/A", "SKIP",
    "координаты для TK-016")
# В тексте уже есть <a> на закон о республ. бюджете (Z2500000239) — проверим:
check_external("TK-016", "ст.127-3 п.4", "127-3",
               "законом о республиканском бюджете", LAW_DOC["респ_бюджете"])

log("TK-017", "label", "п.4-1 ст.133", "label", "N/A", "SKIP",
    "координаты для TK-018")
check_internal("TK-018", "ст.133 п.4-1", "133",
               "пунктом 3 статьи 114 настоящего Кодекса", "z114")

log("TK-019", "label", "п.2 ст.137-1", "label", "N/A", "SKIP",
    "координаты для TK-020")
check_external("TK-020", "ст.137-1 п.2", "137-1",
               'Закона Республики Казахстан "Об обязательном страховании работника от несчастных случаев при исполнении им трудовых (служебных) обязанностей"',
               LAW_DOC["обязательном_страховании"])

log("TK-021", "label", "ст.141", "label", "N/A", "SKIP", "координаты для TK-022")
check_external("TK-022", "ст.141", "141",
               'Законом Республики Казахстан "Об использовании воздушного пространства Республики Казахстан и деятельности авиации"',
               LAW_DOC["воздушного_пространства"])

log("TK-023", "label", "ст.143-1", "label", "N/A", "SKIP",
    "координаты для TK-024")
check_external("TK-024", "ст.143-1", "143-1",
               'Закона Республики Казахстан "О противодействии коррупции"',
               LAW_DOC["противодействии_коррупции"])

log("TK-025", "label", "ст.145-1", "label", "N/A", "SKIP",
    "координаты для TK-026")
check_external("TK-026", "ст.145-1", "145-1",
               'Законом Республики Казахстан "О государственном регулировании, контроле и надзоре финансового рынка и финансовых организаций"',
               LAW_DOC["регулировании_финансового"])

log("TK-027", "label", "п.2 ст.146-1", "label", "N/A", "SKIP",
    "координаты для TK-028")
check_internal("TK-028", "ст.146-1 п.2", "146-1",
               "подпунктом 2) пункта 1 статьи 30 настоящего Кодекса", "z30")

log("TK-029", "label", "п.4-1 ст.159", "label", "N/A", "SKIP",
    "координаты для TK-030..032")
# Все три раза одна ссылка — поэтому after первого DONE второй увидит тот же <a>
check_external("TK-030", "ст.159 п.4-1", "159",
               'Законом Республики Казахстан "О противодействии коррупции"',
               LAW_DOC["противодействии_коррупции"])
check_external("TK-031", "ст.159 п.4-1", "159",
               'Законом Республики Казахстан "О противодействии коррупции"',
               LAW_DOC["противодействии_коррупции"])
check_external("TK-032", "ст.159 п.4-1", "159",
               'Законом Республики Казахстан "О противодействии коррупции"',
               LAW_DOC["противодействии_коррупции"])

log("TK-033", "label", "пп.1) п.1 ст.176", "label", "N/A", "SKIP",
    "координаты для TK-034")
# Две разные ссылки: проверим обе
check_external("TK-034a", "ст.176 п.1 пп.1 / военное полож.", "176",
               '"О военном положении"', LAW_DOC["военном_положении"])
check_external("TK-034b", "ст.176 п.1 пп.1 / чрезвыч. полож.", "176",
               '"О чрезвычайном положении"', LAW_DOC["чрезвычайном_положении"])

log("TK-035", "label", "п.5 ст.191", "label", "N/A", "SKIP",
    "координаты для TK-036")
check_external("TK-036", "ст.191 п.5", "191",
               "Предпринимательским кодексом Республики Казахстан",
               DOC["predprinimatel"])

log("TK-037", "label", "п.1 ст.195", "label", "N/A", "SKIP",
    "координаты для TK-038")
check_external("TK-038", "ст.195 п.1", "195",
               "Предпринимательским кодексом Республики Казахстан",
               DOC["predprinimatel"])

log("TK-039", "label", "п.2 ст.195", "label", "N/A", "SKIP",
    "координаты для TK-040")
check_internal("TK-040", "ст.195 п.2", "195",
               "пункта 3 статьи 198 настоящего Кодекса", "z198")

log("TK-041", "label", "п.3 ст.198", "label", "N/A", "SKIP",
    "координаты для TK-042/043")
check_external("TK-042", "ст.198 п.3", "198",
               'Законом Республики Казахстан "Об исполнительном производстве и статусе судебных исполнителей"',
               LAW_DOC["исполнительном_производстве"])
check_external("TK-043", "ст.198 п.3", "198",
               'Законом Республики Казахстан "Об исполнительном производстве и статусе судебных исполнителей"',
               LAW_DOC["исполнительном_производстве"])

log("TK-044", "label", "ст.200", "label", "N/A", "SKIP", "координаты для TK-045")
check_external("TK-045", "ст.200", "200",
               "Предпринимательским кодексом Республики Казахстан",
               DOC["predprinimatel"])

# ──────────────────────────────────────────────────────────────────
# TKX-секция (Excel) — 37 пунктов
# ──────────────────────────────────────────────────────────────────
verify_note_no_link("TKX-001", "ст.17", "17", "убрать ссылку в сносках")
verify_anchor("TKX-002", "ст.99", "z99")
verify_anchor("TKX-003", "ст.28", "z28")
verify_anchor("TKX-004", "ст.26 п.2", "z26")
verify_anchor("TKX-005", "ст.51 п.2", "z51")
verify_anchor("TKX-006", "ст.58", "z58")
verify_anchor("TKX-007", "ст.58", "z58")
verify_anchor("TKX-008", "ст.58", "z58")
verify_note_no_link("TKX-009", "ст.47", "47", "убрать ссылку в сносках")
verify_note_no_link("TKX-010", "ст.52 п.1-1 пп.2", "52",
                    "убрать ссылку в сносках (КС РК)")
verify_anchor("TKX-011", "ст.52", "z52")
verify_note_no_link("TKX-012", "ст.53", "53", "убрать ссылку в примечании")
verify_anchor("TKX-013", "ст.139", "z139")
verify_anchor("TKX-014", "ст.26", "z26")
verify_anchor("TKX-015", "ст.66", "z66")
verify_anchor("TKX-016", "ст.65", "z65")
verify_anchor("TKX-017", "ст.71", "z71")
verify_anchor("TKX-018", "ст.86", "z86")
verify_anchor("TKX-019", "ст.77", "z77")
verify_anchor("TKX-020", "ст.77", "z77")
verify_anchor("TKX-021", "ст.182", "z182")
verify_anchor("TKX-022", "ст.182-1", "z182-1", article_num="182-1")
verify_note_no_link("TKX-023", "ст.140", "140", "убрать ссылку в сносках")
verify_anchor("TKX-024", "ст.30 п.1 пп.2", "z30")
verify_anchor("TKX-025", "ст.30", "z30")
verify_note_no_link("TKX-026", "ст.160", "160", "убрать ссылку в примечании")
verify_anchor("TKX-027", "ст.176", "z176")
verify_anchor("TKX-028", "ст.176", "z176")
verify_anchor("TKX-029", "ст.164", "z164")
verify_anchor("TKX-030", "ст.171", "z171")
verify_anchor("TKX-031", "ст.198", "z198")
verify_note_no_link("TKX-032", "ст.197", "197", "убрать ссылку в сносках")
verify_note_no_link("TKX-033", "ст.199", "199", "убрать ссылку в сносках")
verify_anchor("TKX-034", "ст.1 п.1", "z1")
verify_anchor("TKX-035", "ст.26", "z26")
verify_anchor("TKX-036", "ст.30", "z30")
verify_anchor("TKX-037", "ст.57", "z57")

# ── Известный under-link: ст.30 должна быть кликабельной ────────────
# Ищем plain-упоминания "статьи 30" / "статьей 30" / "статью 30" вне <a>
ref_patterns = [r'статьи 30 настоящего Кодекса',
                r'статьей 30 настоящего Кодекса',
                r'статью 30 настоящего Кодекса',
                r'пунктом 1 статьи 30',
                r'пункта 1 статьи 30',
                r'подпунктом 2\) пункта 1 статьи 30']
unbound = []
for pat in ref_patterns:
    for m in re.finditer(pat, text):
        if not is_inside_anchor(text, m.start()):
            unbound.append((pat, m.start()))
if unbound:
    log("TK-st30-extra", "поиск под-линка ст.30",
        "статьи 30 / пункта 1 ст.30", "internal",
        f"{len(unbound)} незалинкованных", "NOTED",
        f"первые: {unbound[:3]}")
else:
    log("TK-st30-extra", "поиск под-линка ст.30",
        "статьи 30 / пункта 1 ст.30", "internal",
        "ВСЕ-залинкованы", "DONE", "plain-вхождений нет")

# ──────────────────────────────────────────────────────────────────
# Сохранить файл
# ──────────────────────────────────────────────────────────────────
if text != orig_text:
    HTML.write_text(text, encoding="utf-8")

if missing_anchors:
    MISSING_LOG.write_text(
        json.dumps(missing_anchors, ensure_ascii=False, indent=2),
        encoding="utf-8")

# ── вывод ────────────────────────────────────────────────────────────
print(f"=== ТЗ-Ф2 Трудовой: обработано {len(results)} строк ===")
print(f"новых ссылок добавлено: {new_links_added}")
print(f"пропавших якорей: {len(missing_anchors)}")
print()
print(f"{'ID':14}{'локатор':24}{'STATUS':24}{'тип':14}фраза")
print("-" * 140)
for r in results:
    loc = r["locator"][:22]
    st = f"{r['before']}->{r['after']}"[:22]
    kd = r["type"][:12]
    ref = r["ref"]
    if len(ref) > 70:
        ref = ref[:67] + "..."
    print(f"{r['id']:14}{loc:24}{st:24}{kd:14}{ref}")

done = sum(1 for r in results if r["after"].startswith("DONE"))
fixed = sum(1 for r in results if r["after"] == "FIXED")
ambig = sum(1 for r in results if r["after"] == "AMBIG")
note_strip = sum(1 for r in results if r["after"] == "NOTE-NEEDS-STRIP")
m_anchor = sum(1 for r in results if r["after"] in ("MISSING-anchor",
                                                    "MISSING-anchor-absent"))
not_found = sum(1 for r in results if r["after"] in (
    "NOT-FOUND-IN-ARTICLE", "NO-ARTICLE"))
noted = sum(1 for r in results if r["after"] == "NOTED")
skipped = sum(1 for r in results if r["after"] == "SKIP")

print()
print("=== СВОДКА ===")
print(f"DONE:             {done}")
print(f"MISSING-fixed:    {fixed}")
print(f"AMBIG:            {ambig}")
print(f"NOTE-NEEDS-STRIP: {note_strip}")
print(f"MISSING-anchor:   {m_anchor}")
print(f"NOT-FOUND:        {not_found}")
print(f"NOTED (st30):     {noted}")
print(f"SKIP (labels):    {skipped}")
print(f"новых <a>: {new_links_added}")
