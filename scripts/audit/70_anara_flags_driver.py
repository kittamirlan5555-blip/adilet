# -*- coding: utf-8 -*-
"""ДРАЙВЕР ФЛАГОВ АНАРЫ (методика УПК-раунда, §2.1 CLAUDE.md). Параметризованный.

python 70_anara_flags_driver.py --doc upk --flags source/flags_upk.md [--apply]

Повторяет методику закрытия раунда УПК одним заходом:

ЭТАП A. Парсинг флагов из md: "## N. [RED]? контекст" + "- [LINKED|plain] «фрагмент»".
ЭТАП B. Norm-карта документа: текст без тегов со схлопнутыми пробелами + pos_map
        norm->raw. ВСЕ поиски фраз — ТОЛЬКО через norm-карту (теги внутри фраз
        ломают простые regex по raw).
ЭТАП C. Диагностика каждого фрагмента: FULL_SPAN / PARTIAL / PLAIN / ABSENT.
        FULL_SPAN = raw-диапазон фразы целиком внутри ОДНОГО <a> без разрывов.
ЭТАП D. Автофиксы по категориям (строго в этом порядке, после каждого — гейты):
        D1 перечни статей УК; D2 финальная сетка; D3 одиночные внутренние;
        D4 generic-отсылки с битыми якорями (#z0/#z1) -> корень акта.
ЭТАП E. Гейты (FAIL любого = откат правок ЭТАПА; запись файлов только если всё
        зелёное, включая синхронность обеих форм).
ЭТАП F. Пер-флаговый отчёт для Анары -> data/reports/70_anara_flags_{doc}.md

Сноски: фрагменты внутри <span|p class="note"> НЕ линкуются (правило 13.05),
попадают в отчёт со статусом «в сноске — не линкуем».

Без --apply: полный прогон в памяти + отчёт, файлы НЕ перезаписываются.
"""
import re
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import paths

ROOT = paths.ROOT
FINAL = paths.FINAL
MAPS = paths.MAPS
CONFIG = paths.MAPS      # config/ слит в maps/ (Фаза A)
REPORTS = paths.REPORTS

HOST = "https://adilet.zan.kz/rus/docs/"
UK_SLUG = "ugolovniy"

# ---------- ЭТАП A: флаги ----------
RE_FLAG = re.compile(r"^##\s*(\d+)\.\s*(\[RED\]\s*)?(.*)$")
RE_FRAG = re.compile(r"^-\s*\[(LINKED|plain)\]\s*[«\"](.+?)[»\"]\s*$")


def parse_flags(path):
    flags = []
    cur = None
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        m = RE_FLAG.match(line)
        if m:
            cur = {"num": int(m.group(1)), "red": bool(m.group(2)),
                   "context": m.group(3).strip(), "frags": []}
            flags.append(cur)
            continue
        m = RE_FRAG.match(line)
        if m and cur is not None:
            cur["frags"].append((m.group(1), m.group(2)))
    return flags


# ---------- ЭТАП B: norm-карта ----------
class NormDoc:
    """Текст без тегов со схлопнутыми пробелами + pos_map norm->raw."""

    def __init__(self, raw):
        self.raw = raw
        norm = []
        pos = []
        in_tag = False
        last_ws = False
        for i, ch in enumerate(raw):
            if ch == "<":
                in_tag = True
                continue
            if in_tag:
                if ch == ">":
                    in_tag = False
                continue
            if ch.isspace() or ch == " ":
                if norm and not last_ws:
                    norm.append(" ")
                    pos.append(i)
                    last_ws = True
                continue
            norm.append(ch)
            pos.append(i)
            last_ws = False
        self.norm = "".join(norm)
        self.pos = pos

    def to_raw(self, s, e):
        return self.pos[s], self.pos[e - 1] + 1

    def find_phrase(self, phrase):
        """Все вхождения фразы (ws-схлопнуто, при пустоте — без регистра)."""
        needle = re.sub(r"\s+", " ", phrase.replace(" ", " ").strip())
        out = []
        idx = self.norm.find(needle)
        while idx != -1:
            out.append((idx, idx + len(needle)))
            idx = self.norm.find(needle, idx + 1)
        if not out:
            low, nlow = self.norm.lower(), needle.lower()
            idx = low.find(nlow)
            while idx != -1:
                out.append((idx, idx + len(nlow)))
                idx = low.find(nlow, idx + 1)
        return out


# ---------- raw-инфраструктура ----------
RE_A_OPEN = re.compile(r"<a\b[^>]*>", re.I)
RE_A_CLOSE = re.compile(r"</a\s*>", re.I)
RE_NOTE = re.compile(r'<(span|p)\b[^>]*class="note"[^>]*>.*?</\1\s*>', re.I | re.S)
RE_IDS = re.compile(r'(?:id|name)="([^"]+)"')
RE_TAGS = re.compile(r"<[^>]+>")


def link_spans(raw):
    """[(open_start, content_start, content_end, close_end, href)] без вложенности."""
    events = ([(m.start(), "o", m) for m in RE_A_OPEN.finditer(raw)]
              + [(m.start(), "c", m) for m in RE_A_CLOSE.finditer(raw)])
    events.sort(key=lambda x: x[0])
    out = []
    stack = []
    for _, kind, m in events:
        if kind == "o":
            stack.append(m)
        elif stack:
            om = stack.pop()
            hm = re.search(r'href="([^"]*)"', om.group(0))
            out.append((om.start(), om.end(), m.start(), m.end(),
                        hm.group(1) if hm else None))
    return sorted(out)


def note_spans(raw):
    return [(m.start(), m.end()) for m in RE_NOTE.finditer(raw)]


def in_ranges(s, e, ranges):
    return any(a <= s and e <= b for a, b in ranges)


def overlaps_any(s, e, ranges):
    return any(s < b and a < e for a, b in ranges)


def gettext_nows(raw):
    return re.sub(r"\s+", "", RE_TAGS.sub("", raw))


# ---------- ЭТАП C: диагностика ----------
def diagnose(raw, links, rs, re_):
    """FULL_SPAN / PARTIAL / PLAIN для raw-диапазона фразы."""
    contents = [(cs, ce) for _, cs, ce, _, _ in links]
    if any(cs <= rs and re_ <= ce for cs, ce in contents):
        return "FULL_SPAN"
    if any(rs < ce and cs < re_ for cs, ce in contents):
        return "PARTIAL"
    return "PLAIN"


def diagnose_phrase(raw, nd, links, notes, phrase):
    """Статус по ЛУЧШЕМУ вхождению + признак сноски."""
    occ = nd.find_phrase(phrase)
    if not occ:
        return "ABSENT", False
    states = []
    in_note = False
    for s, e in occ:
        rs, re_ = nd.to_raw(s, e)
        states.append(diagnose(raw, links, rs, re_))
        if in_ranges(rs, re_, notes):
            in_note = True
    for st in ("FULL_SPAN", "PARTIAL", "PLAIN"):
        if st in states:
            return st, in_note
    return states[0], in_note


# ---------- объединённая карта УК ----------
RE_H3_ART = re.compile(r'<h3[^>]*id="(z[\w-]+)"[^>]*>\s*Статья\s+(\d+(?:-\d+)?)\.', re.I)


def uk_merged_map():
    """Статья УК -> якорь. Ground-truth из <h3> ugolovniy_ready + rebuilt
    (с проверкой существования якоря). h3 побеждает."""
    p = FINAL / f"{UK_SLUG}_ready.html"
    raw = p.read_text(encoding="utf-8")
    ids = set(RE_IDS.findall(raw))
    merged = {}
    rb = MAPS / f"article_map_{UK_SLUG}_rebuilt.json"
    if rb.exists():
        for art, anc in json.loads(rb.read_text(encoding="utf-8")).items():
            if anc in ids:
                merged[str(art)] = anc
    for anc, art in RE_H3_ART.findall(raw):
        merged[art] = anc
    return merged, ids


def own_article_map(doc):
    p = MAPS / f"article_map_{doc}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def doc_id_of(doc):
    cj = json.loads((CONFIG / "codes.json").read_text(encoding="utf-8"))
    v = cj.get(doc)
    return v.get("doc_id") if isinstance(v, dict) else None


# ---------- ЭТАП D: автофиксы ----------
ORD_NUM = r"\d{1,3}(?:-\d{1,2})?"
RE_REGION_START = re.compile(r"стать(?:ями|ей|и)\b", re.I)
RE_REGION_END = re.compile(r"Уголовного\s+кодекса", re.I)
RE_STOP = re.compile(r"настоящего Кодекса|настоящим Кодексом|Уголовно-процессуального|"
                     r"Закона Республики|Законом РК|постановлением|дополнена|"
                     r"редакции|Исключен", re.I)
RE_BARE_NUM = re.compile(r"(?<![\d-])(" + ORD_NUM + r")(?![\d)-])")
RE_ENUM_CTX = re.compile(r"(?:стать(?:ями|ей|и)|,|\bи)\s*$", re.I)
RE_DATE_CTX = re.compile(r"(?:\bот|№|\d\.)\s*$", re.I)


def paren_depth_at(norm, region_start, pos):
    seg = norm[region_start:pos]
    return seg.count("(") - seg.count(")")


def uk_href(doc, anchor, uk_doc_id):
    if doc == UK_SLUG:
        return f"#{anchor}"
    return f"{HOST}{uk_doc_id}#{anchor}"


def is_uk_link(href, doc, uk_doc_id):
    if not href:
        return False
    if doc == UK_SLUG:
        return href.startswith("#z")
    return f"/docs/{uk_doc_id}#" in href or href.rstrip("/").endswith(uk_doc_id)


def candidate_ok(nd, s, e, region_start=None):
    """Общие условия голого номера в norm-пространстве."""
    left = nd.norm[max(0, s - 30):s]
    if RE_DATE_CTX.search(left):
        return False
    if region_start is not None and paren_depth_at(nd.norm, region_start, s) > 0:
        return False
    return True


def collect_d1(raw, nd, links, notes, ukmap, doc, uk_doc_id, report):
    """Перечни статей УК: [(rs, re, replacement)]."""
    repl = []
    taken = []
    pos = 0
    while True:
        m = RE_REGION_START.search(nd.norm, pos)
        if not m:
            break
        pos = m.end()
        if any(a <= m.start() < b for a, b in taken):
            continue
        em = RE_REGION_END.search(nd.norm, m.end(), m.end() + 4000)
        if not em:
            continue
        if RE_STOP.search(nd.norm[m.end():em.start()]):
            continue
        taken.append((m.start(), em.end()))
        for nm in RE_BARE_NUM.finditer(nd.norm, m.end(), em.start()):
            s, e = nm.start(), nm.end()
            if not RE_ENUM_CTX.search(nd.norm[max(0, s - 25):s]):
                continue
            if not candidate_ok(nd, s, e, m.start()):
                continue
            rs, re_ = nd.to_raw(s, e)
            if overlaps_any(rs, re_, [(c0, c1) for _, c0, c1, _, _ in links]):
                continue
            if overlaps_any(rs, re_, [(o, c) for o, _, _, c, _ in links]):
                continue
            if in_ranges(rs, re_, notes):
                continue
            num = nm.group(1)
            anc = ukmap.get(num)
            if anc:
                href = uk_href(doc, anc, uk_doc_id)
            else:
                href = HOST + uk_doc_id
                report["no_article"].append(num)
            repl.append((rs, re_, f'<a href="{href}">{raw[rs:re_]}</a>'))
    return repl


def collect_d2(raw, nd, links, notes, ukmap, doc, uk_doc_id, report):
    """Финальная сетка: голый номер между закрытой УК-ссылкой слева (<=95) и
    открытой УК-ссылкой справа (<=160)."""
    repl = []
    uk_links = [(o, cs, ce, cl) for o, cs, ce, cl, h in links
                if is_uk_link(h, doc, uk_doc_id)]
    closes = sorted(cl for _, _, _, cl in uk_links)
    opens = sorted(o for o, _, _, _ in uk_links)
    import bisect
    for nm in RE_BARE_NUM.finditer(nd.norm):
        s, e = nm.start(), nm.end()
        if not candidate_ok(nd, s, e):
            continue
        rs, re_ = nd.to_raw(s, e)
        if overlaps_any(rs, re_, [(o, c) for o, _, _, c, _ in links]):
            continue
        if in_ranges(rs, re_, notes):
            continue
        i = bisect.bisect_right(closes, rs) - 1
        left_ok = i >= 0 and rs - closes[i] <= 95
        j = bisect.bisect_left(opens, re_)
        right_ok = j < len(opens) and opens[j] - re_ <= 160
        if not (left_ok and right_ok):
            continue
        num = nm.group(1)
        anc = ukmap.get(num)
        if anc:
            href = uk_href(doc, anc, uk_doc_id)
        else:
            href = HOST + uk_doc_id
            report["no_article"].append(num)
        repl.append((rs, re_, f'<a href="{href}">{raw[rs:re_]}</a>'))
    return repl


RE_D3 = re.compile(r"стать(?:е|ей|и)\s+(" + ORD_NUM + r")\s+настоящего Кодекса")


def collect_d3(raw, nd, links, notes, amap, file_ids, report):
    """Одиночные внутренние: plain 'статье N настоящего Кодекса' -> #z."""
    repl = []
    for m in RE_D3.finditer(nd.norm):
        s = m.start()
        e_num = m.end(1)
        rs, re_ = nd.to_raw(s, e_num)
        rs_full, re_full = nd.to_raw(s, m.end())
        if overlaps_any(rs_full, re_full, [(o, c) for o, _, _, c, _ in links]):
            continue
        if in_ranges(rs, re_, notes):
            continue
        anc = amap.get(m.group(1))
        if not anc or anc not in file_ids:
            report["no_article_internal"].append(m.group(1))
            continue
        repl.append((rs, re_, f'<a href="#{anc}">{raw[rs:re_]}</a>'))
    return repl


RE_D4 = re.compile(r'(href="[^"]*?/docs/[A-Za-z0-9_]+)#z[01]"')


def apply_d4(raw):
    """Generic-отсылки с битыми якорями #z0/#z1 -> корень акта."""
    return RE_D4.subn(r'\1"', raw)


def apply_replacements(raw, repls):
    out = raw
    for rs, re_, rep in sorted(repls, key=lambda x: -x[0]):
        out = out[:rs] + rep + out[re_:]
    return out


# ---------- ЭТАП E: гейты ----------
RE_NESTED_CLOSE = re.compile(r"</a>\s*</a>")
RE_DOUBLE_HREF = re.compile(r"<a[^>]*href=[^>]*href=")
RE_A_TAG = re.compile(r"<a\b[^>]*>|</a\s*>", re.I)
RE_INTERNAL = re.compile(r'href="#([^"]+)"')
RE_CROSS = re.compile(r'href="[^"]*?/docs/([A-Za-z0-9_]+)#([^"]+)"')


def stage_gates(raw_before, raw_after, uk_ids, uk_doc_id):
    fails = []
    if gettext_nows(raw_before) != gettext_nows(raw_after):
        fails.append("get_text-инвариантность")
    if RE_NESTED_CLOSE.search(raw_after):
        fails.append("</a></a> raw")
    depth = 0
    for m in RE_A_TAG.finditer(raw_after):
        depth += 1 if m.group(0)[1] != "/" else -1
        if depth > 1 or depth < 0:
            fails.append("вложенные/несбалансированные <a>")
            break
    if RE_DOUBLE_HREF.search(raw_after):
        fails.append("двойной href")
    ids = set(RE_IDS.findall(raw_after))
    if any(h not in ids for h in RE_INTERNAL.findall(raw_after)):
        fails.append("битые внутренние #z")
    for docid, anchor in set(RE_CROSS.findall(raw_after)):
        if docid == uk_doc_id and anchor not in uk_ids:
            fails.append(f"cross-якорь {docid}#{anchor} нет в цели")
            break
    return fails


RE_A_PAIR = re.compile(r'<a\b[^>]*href="([^"]*)"[^>]*>(.*?)</a\s*>', re.I | re.S)


def canon_pairs(raw, own_id):
    pairs = set()
    for href, inner in RE_A_PAIR.findall(raw):
        h = href.strip()
        if own_id:
            if h.startswith(HOST + own_id + "#"):
                h = "#" + h.split("#", 1)[1]
            elif h == HOST + own_id:
                h = "@SELF_ROOT"
        pairs.add((h, re.sub(r"\s+", " ", RE_TAGS.sub("", inner)).strip()))
    return pairs


# ---------- основной прогон ----------
def process_form(raw, doc, ukmap, uk_ids, uk_doc_id, amap, report, log):
    stages = []
    file_ids = set(RE_IDS.findall(raw))

    def stage(name, collector):
        nonlocal raw
        snapshot = raw
        nd = NormDoc(raw)
        links = link_spans(raw)
        notes = note_spans(raw)
        repls = collector(raw, nd, links, notes)
        new_raw = apply_replacements(raw, repls) if repls else raw
        fails = stage_gates(snapshot, new_raw, uk_ids, uk_doc_id)
        if fails:
            log.append(f"    {name}: FAIL {fails} -> ОТКАТ этапа "
                       f"({len(repls)} правок отброшено)")
            stages.append((name, 0, fails))
        else:
            raw = new_raw
            log.append(f"    {name}: +{len(repls)} правок, гейты PASS")
            stages.append((name, len(repls), []))

    stage("D1 перечни УК", lambda r, nd, lk, nt:
          collect_d1(r, nd, lk, nt, ukmap, doc, uk_doc_id, report))
    stage("D2 финальная сетка", lambda r, nd, lk, nt:
          collect_d2(r, nd, lk, nt, ukmap, doc, uk_doc_id, report))
    stage("D3 одиночные внутренние", lambda r, nd, lk, nt:
          collect_d3(r, nd, lk, nt, amap, file_ids, report))

    snapshot = raw
    new_raw, n4 = apply_d4(raw)
    fails = stage_gates(snapshot, new_raw, uk_ids, uk_doc_id)
    if fails:
        log.append(f"    D4 generic#z0/z1: FAIL {fails} -> ОТКАТ")
        stages.append(("D4", 0, fails))
    else:
        raw = new_raw
        log.append(f"    D4 generic#z0/z1->корень: {n4} ретаргетов, гейты PASS")
        stages.append(("D4", n4, []))
    return raw, stages


def flag_status(pre, post, in_note, absent_note="фраза не найдена в документе"):
    if pre == "ABSENT":
        return absent_note
    if in_note and pre != "FULL_SPAN":
        return "в сноске — не линкуем (правило 13.05)"
    if pre == "FULL_SPAN":
        return "false-positive Word (уже была ссылка)"
    if post == "FULL_SPAN":
        return "new link" if pre == "PLAIN" else "span extended"
    return f"НЕ закрыт автофиксами ({pre} -> {post}) — ручной разбор"


def main():
    argv = sys.argv[1:]
    def opt(name, default=None):
        return argv[argv.index(name) + 1] if name in argv else default
    doc = opt("--doc")
    flags_path = opt("--flags")
    apply_mode = "--apply" in argv
    if not doc or not flags_path:
        print("usage: python 70_anara_flags_driver.py --doc {slug} "
              "--flags {file.md} [--apply]")
        sys.exit(2)

    forms = [p for p in (FINAL / f"{doc}_structured.html",
                         FINAL / f"{doc}_ready.html") if p.exists()]
    if not forms:
        print(f"FATAL: нет файлов {doc} в data/final")
        sys.exit(2)

    flags = parse_flags(flags_path)
    ukmap, uk_ids = uk_merged_map()
    uk_doc_id = doc_id_of(UK_SLUG)
    own_id = doc_id_of(doc)
    amap = own_article_map(doc)
    report = {"no_article": [], "no_article_internal": []}
    log = []

    # ---- диагностика ДО (по канонической форме) ----
    prim = forms[-1]   # _ready предпочтительно (последняя в списке)
    raw0 = prim.read_text(encoding="utf-8")
    nd0, links0, notes0 = NormDoc(raw0), link_spans(raw0), note_spans(raw0)
    pre = {}
    for f in flags:
        for kind, frag in f["frags"]:
            pre[(f["num"], frag)] = diagnose_phrase(raw0, nd0, links0, notes0, frag)

    # ---- автофиксы на обеих формах ----
    out_raws = {}
    all_stages = {}
    for p in forms:
        log.append(f"  {p.name}:")
        raw = p.read_text(encoding="utf-8")
        new_raw, stages = process_form(raw, doc, ukmap, uk_ids, uk_doc_id,
                                       amap, report, log)
        out_raws[p] = new_raw
        all_stages[p.name] = stages

    # ---- финальная сверка форм ----
    sync_ok = True
    if len(forms) == 2:
        a = canon_pairs(out_raws[forms[0]], own_id)
        b = canon_pairs(out_raws[forms[1]], own_id)
        diverge = (a - b) | (b - a)
        sync_ok = not diverge
        log.append(f"  СИНХРОННОСТЬ ФОРМ: расхождений={len(diverge)}"
                   + ("" if sync_ok else f" напр. {sorted(diverge)[:4]}"))

    # ---- диагностика ПОСЛЕ ----
    raw1 = out_raws[prim]
    nd1, links1, notes1 = NormDoc(raw1), link_spans(raw1), note_spans(raw1)
    rows = []
    for f in flags:
        for kind, frag in f["frags"]:
            p_st, p_note = pre[(f["num"], frag)]
            a_st, _ = diagnose_phrase(raw1, nd1, links1, notes1, frag)
            rows.append((f["num"], kind, frag, flag_status(p_st, a_st, p_note)))

    # ---- ЭТАП F: отчёт ----
    REPORTS.mkdir(parents=True, exist_ok=True)
    L = [f"# Отчёт по флагам — {doc}", "",
         f"Флагов: {len(flags)}; фрагментов: {len(rows)}; "
         f"режим: {'APPLY' if apply_mode else 'DRY-RUN (файлы не тронуты)'}", "",
         "## Прогон", ""]
    L += log
    L += ["", "## Пер-флаговая таблица (для Анары)", "",
          "| № | тип | фрагмент | статус |", "|---|---|---|---|"]
    for num, kind, frag, status in rows:
        frag_short = frag if len(frag) <= 80 else frag[:77] + "…"
        L.append(f"| {num} | {kind} | «{frag_short}» | {status} |")
    if report["no_article"]:
        L += ["", "## Статьи БЕЗ якоря в выгрузке УК (залинкованы на корень):",
              "  " + ", ".join(sorted(set(report["no_article"])))]
    if report["no_article_internal"]:
        L += ["", "## Внутренние статьи без якоря (НЕ линкованы):",
              "  " + ", ".join(sorted(set(report["no_article_internal"])))]
    out = REPORTS / f"70_anara_flags_{doc}.md"
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))

    # ---- запись ----
    if apply_mode:
        if not sync_ok:
            print("\n!!! СИНХРОННОСТЬ ФОРМ FAIL — файлы НЕ записаны")
            sys.exit(1)
        for p in forms:
            p.write_text(out_raws[p], encoding="utf-8")
        print(f"\n[APPLIED] записаны: {[p.name for p in forms]}")
    else:
        print("\n[DRY-RUN] файлы не тронуты; для записи добавь --apply")
    print(f"-> {out}")


if __name__ == "__main__":
    main()
