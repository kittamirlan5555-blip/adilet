# -*- coding: utf-8 -*-
"""Ссылки в подзаконных актах: ВНУТРЕННИЕ (на пункты) + на ЗАКОНЫ (маппинг-654).

ВНУТРЕННИЕ — главный риск проекта. Нумерация пунктов рестартует в каждом блоке
(приказ 1..4, затем Правила снова с 1), поэтому «пунктом 5 настоящих Правил» резолвим
СТРОГО в карте блока «Правила», а «пунктом 3 настоящего приказа» — в карте тела акта.
Правила WRONG=0:
  • блок определяется словом-видом после «настоящ*» («…настоящих Правил» -> блок Правил);
  • если такого блока нет / номер в блоке отсутствует / номер помечен AMBIGUOUS
    (нумерация рестартовала внутри блока) — НЕ ЛИНКУЕМ, пишем причину в отчёт;
  • спан полный: гиперссылкой становится вся фраза «пунктом 5 настоящих Правил».

ЗАКОНЫ — существующий маппинг названий (654 ключа), ссылка на КОРЕНЬ акта (§4).
Гейты: текст не меняется (get_text без разделителя), нет вложенных <a>, все #z резолвятся.
"""
import io, sys, re, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from pathlib import Path
from bs4 import BeautifulSoup, NavigableString
from collections import Counter

ROOT = Path(__file__).resolve().parents[1]
HOST = "https://adilet.zan.kz/rus/docs/"
SKIP = {"a", "script", "style", "head", "title"}

# «пунктом 5 настоящих Правил», «пункта 3 настоящего приказа»
# Вид вложенного акта — ИЗ ЗАКРЫТОГО СЛОВАРЯ, иначе «настоящих Правил отказывает»
# затягивает в спан следующее слово и ломает и границу, и определение блока.
# Опциональное прилагательное впереди: «настоящих Санитарных правил».
KIND_NOUN = (r"(?:правил\w*|инструкц\w+|положени\w+|регламент\w*|методик\w+|перечн\w+|"
             r"перечень|норматив\w*|стандарт\w*|порядк\w+|порядок|требовани\w+|форм\w+|"
             r"устав\w*|программ\w+|концепци\w+|план\w*|услови\w+|"
             r"приказ\w*|постановлени\w+|распоряжени\w+|указ\w*|решени\w+)")
RE_INTERNAL = re.compile(
    r"(?P<full>(?P<unit>пункт\w*|подпункт\w*)\s+(?P<num>\d{1,3})\)?\s+"
    r"настоящ\w+\s+(?:[А-ЯЁа-яё]+\s+)?(?P<kind>" + KIND_NOUN + r"))", re.U | re.I)
SUBDIV = re.compile(r"^(Глава|Раздел|Параграф|§)", re.I)
RE_LAW = re.compile(r'Закон\w*\s+Республики\s+Казахстан\s+["«]([^"»]{6,120})["»]')


def stem(w):
    w = (w or "").lower()
    for suf in ("ами", "ах", "ов", "ям", "ями", "ия", "ии", "ие", "ей", "ой", "ый",
                "ам", "а", "ы", "и", "е", "у", "ю", "я", "ь"):
        if len(w) > 5 and w.endswith(suf):
            return w[: -len(suf)]
    return w


ACT_WORDS = {"приказ", "постановлени", "распоряжени", "указ", "решени"}


def find_block(blocks, kindword, here=None):
    """Блок по фразе «настоящ* <вид>».

    Семантика: «настоящих Правил» = ТЕ Правила, которые читаешь. Поэтому сначала
    проверяем БЛОК, В КОТОРОМ стоит сама ссылка (here) — это снимает неоднозначность
    в актах с несколькими блоками «Правила». Только если вид не совпал с текущим
    блоком, ищем единственный подходящий по всему документу.
    """
    st = stem((kindword or "").strip().lower())
    if st in ACT_WORDS or any(st.startswith(a) for a in ACT_WORDS):
        for b in blocks:
            if b["kind"] == "act":
                return b, "act"
        return None, "нет блока тела акта"
    if here is not None and here.get("kindword") and \
       (here["kindword"].startswith(st) or st.startswith(here["kindword"])):
        return here, "self"                            # ссылка внутри своего же блока
    cand = [b for b in blocks if b.get("kindword") and
            (b["kindword"].startswith(st) or st.startswith(b["kindword"]))]
    if len(cand) == 1:
        return cand[0], "nested"
    if not cand:
        return None, f"нет блока вида «{kindword}»"
    return None, f"неоднозначно: {len(cand)} блоков вида «{kindword}»"


def count_dangling(soup):
    """Висячие ТОЛЬКО среди осмысленных #zN; пустые href="#" из выгрузки adilet — не наши."""
    ids = {e.get("id") for e in soup.find_all(attrs={"id": True})}
    return sum(1 for a in soup.find_all("a", href=True)
               if re.match(r"^#z[\w-]+$", a["href"]) and a["href"][1:] not in ids)


def in_skip(node):
    p = node.parent
    while p is not None:
        if getattr(p, "name", None) in SKIP:
            return True
        p = p.parent
    return False


def norm(soup):
    return "".join(soup.get_text().split())


def process(html, struct, npa_names, stats, samples):
    soup = BeautifulSoup(html, "html.parser")
    blocks = struct["blocks"]
    before = norm(soup)
    dang0 = count_dangling(soup)

    # идём в порядке документа, отслеживая ТЕКУЩИЙ блок теми же правилами, что и
    # структуризатор: h3 «Глава/Раздел» — подраздел, любой другой h3 — новый блок.
    # Сопоставляем по ЯКОРЮ/ЗАГОЛОВКУ блока, а не по порядковому номеру: структуризатор
    # включает в список только блоки, где есть пункты, поэтому позиции не совпадают.
    by_anchor = {b["title_anchor"]: b for b in blocks if b.get("title_anchor")}
    by_title = {b["title"]: b for b in blocks if b.get("title")}
    here = next((b for b in blocks if b["kind"] == "act"), None)
    nodes = []
    for e in soup.find_all(["h3", "p"]):
        if e.name == "h3":
            t = re.sub(r"\s+", " ", e.get_text(" ", strip=True))
            if not SUBDIV.match(t):
                here = by_anchor.get(e.get("id")) or by_title.get(t[:200])
            continue
        for tn in e.find_all(string=True):
            nodes.append((tn, here))

    for tn, here in nodes:
        s = str(tn)
        if len(s.strip()) < 8 or in_skip(tn) or tn.parent is None:
            continue
        pieces, last, changed = [], 0, False
        events = []
        for m in RE_INTERNAL.finditer(s):
            events.append(("int", m))
        for m in RE_LAW.finditer(s):
            events.append(("law", m))
        events.sort(key=lambda x: x[1].start())
        occupied = -1
        for kind, m in events:
            if m.start() < occupied:
                continue
            href = None
            if kind == "int":
                stats["internal_found"] += 1
                blk, why = find_block(blocks, m.group("kind"), here)
                if blk is None:
                    stats["internal_skip_noblock"] += 1
                    stats["reasons"][why] += 1
                else:
                    n = int(m.group("num"))
                    if n in blk.get("ambiguous", []):
                        stats["internal_skip_ambiguous"] += 1
                    elif str(n) in blk["punkt"]:
                        href = "#" + blk["punkt"][str(n)]
                        stats["internal_linked"] += 1
                        if len(samples) < 400:
                            samples.append({"doc": struct["doc_id"], "phrase": m.group("full"),
                                            "block_kind": blk["kind"], "block": blk["title"][:60],
                                            "num": n, "href": href})
                    else:
                        stats["internal_skip_nonum"] += 1
            else:
                nm = m.group(1)
                stats["law_found"] += 1
                if nm in npa_names:
                    href = HOST + npa_names[nm]
                    stats["law_linked"] += 1
                else:
                    stats["law_skip_nomap"] += 1
            if href:
                pieces.append(NavigableString(s[last:m.start()]))
                a = soup.new_tag("a", href=href)
                a.string = m.group(0)
                pieces.append(a)
                last = m.end(); occupied = m.end(); changed = True
        if changed:
            pieces.append(NavigableString(s[last:]))
            tn.replace_with(*pieces)

    after = norm(soup)
    nested = sum(1 for a in soup.find_all("a") if a.find("a"))
    return soup, (before == after), nested, count_dangling(soup) - dang0


def main():
    src, structd, out = (Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))
    out.mkdir(parents=True, exist_ok=True)
    m = json.loads((ROOT / "maps/npa_mapping.json").read_text(encoding="utf-8"))
    npa_names = {}
    for k, v in m.items():
        for nm in re.findall(r'"([^"]+)"', k):
            npa_names.setdefault(nm, v)
    stats = Counter(); stats["reasons"] = Counter()
    samples, bad = [], []
    for f in sorted(src.glob("*.html")):
        sp = structd / f"{f.stem}.json"
        if not sp.exists():
            continue
        struct = json.loads(sp.read_text(encoding="utf-8"))
        soup, inv, nested, dang = process(f.read_text(encoding="utf-8", errors="replace"),
                                          struct, npa_names, stats, samples)
        if not (inv and nested == 0 and dang == 0):
            bad.append((f.stem, inv, nested, dang)); continue
        (out / f.name).write_text(str(soup), encoding="utf-8")
        stats["written"] += 1
    print(f"обработано и записано: {stats['written']}  | гейт-провалов: {len(bad)}")
    for b in bad[:5]:
        print(f"   ПРОВАЛ {b[0]}: textInv={b[1]} nested={b[2]} dangling={b[3]}")
    print(f"\nВНУТРЕННИЕ ссылки:")
    print(f"   найдено фраз          : {stats['internal_found']}")
    print(f"   ЗАЛИНКОВАНО           : {stats['internal_linked']}")
    print(f"   не линкуем (нет блока): {stats['internal_skip_noblock']}")
    print(f"   не линкуем (AMBIGUOUS): {stats['internal_skip_ambiguous']}")
    print(f"   не линкуем (нет номера в блоке): {stats['internal_skip_nonum']}")
    print(f"\nЗАКОНЫ по названию:")
    print(f"   найдено   : {stats['law_found']}")
    print(f"   залинковано: {stats['law_linked']}   без маппинга: {stats['law_skip_nomap']}")
    (Path(sys.argv[4]) if len(sys.argv) > 4 else Path("sub_links_samples.json")).write_text(
        json.dumps({"samples": samples, "reasons": dict(stats["reasons"])},
                   ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
