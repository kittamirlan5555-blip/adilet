"""READ-ONLY аудит структуры УК (ugolovniy_structured.html). Ничего не меняет."""
import sys
import io
import re
import json
from pathlib import Path
from bs4 import BeautifulSoup, Tag

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
HTML = ROOT / "data" / "final" / "ugolovniy_structured.html"
CHUNKS = ROOT / "data" / "chunks" / "ugolovniy.jsonl"

soup = BeautifulSoup(HTML.read_text(encoding="utf-8"), "html.parser")


def heading(div):
    """Текст ближайшего заголовка обёртки (h2/h3/h4/span-label)."""
    for ch in div.children:
        if isinstance(ch, Tag) and ch.name in ("h2", "h3", "h4", "span"):
            t = ch.get_text(" ", strip=True)
            if t:
                return t
    return div.get_text(" ", strip=True)[:60]


def direct_articles(div):
    """Статьи (div data-type=статья), чей БЛИЖАЙШИЙ структурный предок = div."""
    out = []
    for art in div.find_all("div", attrs={"data-type": "статья"}):
        # nearest structural ancestor with data-type in part/section/chapter/paragraph
        p = art.parent
        while p is not None:
            if isinstance(p, Tag) and p.get("data-type") in (
                "часть", "раздел", "глава", "параграф", "подраздел"
            ):
                break
            p = p.parent
        if p is div:
            out.append(art)
    return out


def child_divs(div, dtype):
    """Прямые потомки-обёртки заданного типа (на любой глубине, но логически
    ниже текущего уровня; берём те, чей ближайший структурный предок = div)."""
    out = []
    for d in div.find_all("div", attrs={"data-type": dtype}):
        p = d.parent
        while p is not None:
            if isinstance(p, Tag) and p.get("data-type") in (
                "часть", "раздел", "глава", "параграф", "подраздел"
            ):
                break
            p = p.parent
        if p is div:
            out.append(d)
    return out


print("=" * 88)
print("(1) СКЕЛЕТ УК: часть → раздел → глава  (статей напрямую vs в главах)")
print("=" * 88)

doc_root = soup.find("div", class_="document") or soup
parts = [d for d in doc_root.find_all("div", attrs={"data-type": "часть"})]
# top-level only (ближайший структурный предок отсутствует)
top_parts = []
for d in parts:
    p = d.parent
    is_top = True
    while p is not None:
        if isinstance(p, Tag) and p.get("data-type") in ("часть",):
            is_top = False
            break
        p = p.parent
    if is_top:
        top_parts.append(d)

null_chapter_sections = {}  # section label -> count of direct articles


def part_label(div):
    h = heading(div).upper()
    if "ОБЩАЯ" in h:
        return "CH1 Общая часть"
    if "ОСОБЕННАЯ" in h:
        return "CH2 Особенная часть"
    return f"часть {div.get('data-number')}"


def chapter_article_count(ch):
    """Статьи в главе: напрямую + внутри её параграфов."""
    cda = direct_articles(ch)
    pars = child_divs(ch, "параграф")
    par_arts = sum(len(direct_articles(pp)) for pp in pars)
    return len(cda) + par_arts, len(pars)


def print_chapter(ch, indent):
    tot, npars = chapter_article_count(ch)
    extra = f", параграфов={npars}" if npars else ""
    print(f"{indent}G{ch.get('data-number')} «{heading(ch)[:55]}»: статей={tot}{extra}")


for part in top_parts:
    print(f"\n{part_label(part)}")
    sections = child_divs(part, "раздел")
    direct_chapters = child_divs(part, "глава")  # главы прямо под частью (Особенная УК)
    pda = direct_articles(part)
    if pda:
        print(f"  [!] статей НАПРЯМУЮ под частью (вне раздела/главы) = {len(pda)}: "
              f"{[a.get('data-number') for a in pda]}")
    for sec in sections:
        chapters = child_divs(sec, "глава")
        sda = direct_articles(sec)
        h = heading(sec)
        print(f"  R{sec.get('data-number')} «{h[:60]}»: "
              f"статей напрямую={len(sda)}, глав={len(chapters)}")
        if sda:
            null_chapter_sections[f"R{sec.get('data-number')} {h[:40]}"] = \
                [a.get("data-number") for a in sda]
        for ch in chapters:
            print_chapter(ch, "    ")
    if direct_chapters:
        print(f"  (глав напрямую под частью, без раздела = {len(direct_chapters)}; "
              f"section=null для их статей)")
        for ch in direct_chapters:
            print_chapter(ch, "    ")


print()
print("=" * 88)
print("(2) Статьи УК с chapter=null (по чанкам) и их разделы")
print("=" * 88)
rows = [json.loads(l) for l in CHUNKS.open(encoding="utf-8")]
seen_art = {}
for c in rows:
    m = c["meta"]
    art = m["article"]
    if art in seen_art:
        continue
    seen_art[art] = m["hier_path"]

null_chap = [(a, hp) for a, hp in seen_art.items() if hp.get("chapter") is None]
print(f"всего статей УК (уникальных) = {len(seen_art)}")
print(f"статей с chapter=null = {len(null_chap)}")
from collections import Counter
by_sec = Counter()
for a, hp in null_chap:
    by_sec[(hp.get("code_part"), hp.get("section"))] += 1
for (cp, sec), n in sorted(by_sec.items(), key=lambda x: (str(x[0][0]), str(x[0][1]))):
    print(f"  code_part={cp} section={sec}: {n} статей")
print("  список (первые 60):", [a for a, _ in null_chap][:60])


print()
print("=" * 88)
print("(3) Вердикт: есть ли разделы где «Глава N» ВИДНА в тексте, но обёртки нет?")
print("=" * 88)
GLAVA_RE = re.compile(r"\bГЛАВА\s+(\d+)", re.IGNORECASE)
problem_found = False
for part in top_parts:
    for sec in child_divs(part, "раздел"):
        chapters = child_divs(sec, "глава")
        if chapters:
            continue  # есть обёртки — норм
        # нет обёрток-глав. Ищем в СЫРОМ html этого раздела упоминания "Глава N"
        # вне вложенных глав (их и так нет). Берём h2/h3/h4/p внутри раздела.
        raw_hits = []
        for el in sec.find_all(["h2", "h3", "h4", "p", "b", "strong", "span"]):
            # пропустим тексты внутри статей (тело статьи может цитировать "главы")
            anc = el
            in_article = False
            while anc is not None:
                if isinstance(anc, Tag) and anc.get("data-type") == "статья":
                    in_article = True
                    break
                anc = anc.parent
            if in_article:
                continue
            t = el.get_text(" ", strip=True)
            m = GLAVA_RE.search(t)
            if m and len(t) < 120:
                raw_hits.append(t[:100])
        if raw_hits:
            problem_found = True
            print(f"  [BUG?] R{sec.get('data-number')} «{heading(sec)[:50]}» "
                  f"без <div глава>, но в тексте есть:")
            for h in raw_hits[:5]:
                print(f"         {h!r}")
if not problem_found:
    print("  Чисто: во ВСЕХ разделах без обёрток-глав НЕТ заголовков «Глава N» "
          "вне тела статей.")

# Глобальный кросс-чек: все ли «ГЛАВА N» / «РАЗДЕЛ N» заголовки стали обёртками?
HEAD_RE = re.compile(r"^\s*(ГЛАВА|РАЗДЕЛ|ПАРАГРАФ)\s+([IVXLCDM]+|\d+[\w-]*)\b", re.I)
n_chap_wrap = len(soup.find_all("div", attrs={"data-type": "глава"}))
n_sec_wrap = len(soup.find_all("div", attrs={"data-type": "раздел"}))
unwrapped = []
for el in soup.find_all(["h2", "h3", "h4", "b", "strong"]):
    t = el.get_text(" ", strip=True)
    if not HEAD_RE.match(t) or len(t) > 120:
        continue
    anc = el
    in_article = is_wrapper_head = False
    while anc is not None:
        if isinstance(anc, Tag):
            if anc.get("data-type") == "статья":
                in_article = True
                break
            # заголовок-обёртки сидит как ПРЯМОЙ ребёнок div data-type=глава/раздел/параграф
            if anc.get("data-type") in ("глава", "раздел", "параграф") and el.parent is anc:
                is_wrapper_head = True
                break
        anc = anc.parent
    if not in_article and not is_wrapper_head:
        unwrapped.append(t[:80])
print(f"  глобально: обёрток-глав={n_chap_wrap}, обёрток-разделов={n_sec_wrap}, "
      f"НЕобёрнутых заголовков (глава/раздел/§) вне статей={len(unwrapped)}")
for u in unwrapped[:10]:
    print(f"      [unwrapped] {u!r}")
if not problem_found and not unwrapped:
    print("  → ВЕРДИКТ: chapter=null отражает РЕАЛЬНУЮ структуру источника "
          "(в разделах 1–7 Общей части глав нет), а НЕ баг структуризатора.")


print()
print("=" * 88)
print("(4) hier_id непустой у ВСЕХ чанков ugolovniy.jsonl?")
print("=" * 88)
empty = [c["id"] for c in rows if not c["meta"].get("hier_id")]
print(f"всего чанков = {len(rows)}")
print(f"с пустым/отсутствующим hier_id = {len(empty)}")
print(f"ВЕРДИКТ: {'ВСЕ непустые ✓' if not empty else ('ПУСТЫЕ: ' + str(empty[:20]))}")
