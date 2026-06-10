"""ТЗ-02. Снять <a>…</a> внутри сносок и примечаний (unwrap текст).

Регионы:
  (1) p.note          — <p class="note">…</p>           (целиком).
  (2) span.note-chain — кластер смежных <span class="note">,
                        склеенный включая промежуточные <a> и whitespace
                        (разорванные ссылками сноски типа «… № 62-VII …»).
  (3) <p>Примечание.  — <p>, чей первый видимый текст начинается на
                        «Примечани[ея]» (статутное примечание в теле статьи).
  (4) ИЗПИ/РЦПИ chain — <font color="#FF0000"> с текстом
                        «Примечание {ИЗПИ|РЦПИ}!» и все смежные красные
                        <font color="#FF0000"> через <br/> до разрыва.

Внутри найденных регионов каждый <a> заменяется на свой текст (unwrap).
Снаружи — ничего не меняется.

Запуск:
  python scripts/18_strip_links_in_notes.py            # все коды кроме upk
  python scripts/18_strip_links_in_notes.py trudovoy   # один код
"""
import argparse
import json
import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup, NavigableString, Tag

ROOT = Path(__file__).resolve().parent.parent
FINAL = ROOT / "data" / "final"
CODES = ROOT / "config" / "codes.json"

PRIM_RE = re.compile(r'^\s*Примечани[ея]\b')
IZPI_RE = re.compile(r'Примечани[ея]\s+(ИЗПИ|РЦПИ)\s*!')


def is_ws(node):
    return isinstance(node, NavigableString) and not node.strip()


def is_br(node):
    return isinstance(node, Tag) and node.name == "br"


def is_note_span(node):
    return (isinstance(node, Tag) and node.name == "span"
            and "note" in (node.get("class") or []))


def is_a(node):
    return isinstance(node, Tag) and node.name == "a"


def is_red_font(node):
    if not (isinstance(node, Tag) and node.name == "font"):
        return False
    color = (node.get("color") or "").lstrip("#").upper()
    return color == "FF0000"


def first_visible_text(tag):
    """Первый непустой текст, видимый при чтении <p>. Игнорирует <a id=...>
    без текста и whitespace."""
    for d in tag.descendants:
        if isinstance(d, NavigableString):
            if d.strip():
                return d.strip()
        elif isinstance(d, Tag) and d.name == "br":
            continue
    return ""


def find_note_regions(soup):
    """Возвращает список set'ов тегов, образующих регион. Каждый тег внутри
    региона — кандидат на unwrap <a>."""
    regions = []
    visited = set()

    # (1) p.note  — целиком
    for p in soup.find_all("p"):
        if "note" in (p.get("class") or []):
            if id(p) in visited:
                continue
            regions.append({"type": "p.note", "root": p, "nodes": [p]})
            visited.add(id(p))

    # (2) span.note-chain — склейка смежных span.note + промежуточных <a>/whitespace
    for span in soup.find_all("span"):
        if "note" not in (span.get("class") or []):
            continue
        if id(span) in visited:
            continue
        # начало кластера: вернёмся влево, пока соседи — span.note / <a> / ws
        start = span
        while True:
            prev = start.previous_sibling
            if prev is None:
                break
            if is_ws(prev) or is_a(prev) or is_note_span(prev):
                start = prev
            else:
                break
        # обрежем ведущие ws — старт должен быть тегом
        while is_ws(start):
            start = start.next_sibling
        # пройдём вправо, собирая ноды
        nodes = []
        cur = start
        while cur is not None:
            if is_note_span(cur) or is_a(cur) or is_ws(cur):
                nodes.append(cur)
                cur = cur.next_sibling
                continue
            break
        # отметим все note-span'ы как visited
        for n in nodes:
            if is_note_span(n):
                visited.add(id(n))
        # отбросим хвостовые <a> и ws — регион должен заканчиваться на span.note
        while nodes and (is_a(nodes[-1]) or is_ws(nodes[-1])):
            nodes.pop()
        # отбросим ведущие ws (уже фильтровано) и ведущие <a> (не часть сноски)
        while nodes and (is_a(nodes[0]) or is_ws(nodes[0])):
            nodes.pop(0)
        if not nodes:
            continue
        # должен быть хотя бы один note-span
        if not any(is_note_span(n) for n in nodes):
            continue
        regions.append({"type": "span.note-chain", "root": nodes[0], "nodes": nodes})

    # (3) <p>Примечание. — статутное примечание
    for p in soup.find_all("p"):
        if "note" in (p.get("class") or []):
            continue  # уже учли как p.note
        if id(p) in visited:
            continue
        txt = first_visible_text(p)
        if PRIM_RE.match(txt):
            regions.append({"type": "p.primechanie", "root": p, "nodes": [p]})
            visited.add(id(p))

    # (4) ИЗПИ/РЦПИ chain — красные <font> с «Примечание ИЗПИ/РЦПИ!»,
    #     включая смежные красные <font> через <br/>.
    for font in soup.find_all("font"):
        if not is_red_font(font):
            continue
        if id(font) in visited:
            continue
        if not IZPI_RE.search(font.get_text(" ", strip=True)):
            continue
        # склейка вправо: <br/>, ws, red <font>, …
        nodes = [font]
        visited.add(id(font))
        cur = font.next_sibling
        while cur is not None:
            if is_ws(cur) or is_br(cur):
                nodes.append(cur)
                cur = cur.next_sibling
                continue
            if is_red_font(cur):
                nodes.append(cur)
                visited.add(id(cur))
                cur = cur.next_sibling
                continue
            break
        # хвостовые ws/br убрать
        while nodes and (is_ws(nodes[-1]) or is_br(nodes[-1])):
            nodes.pop()
        regions.append({"type": "izpi-chain", "root": font, "nodes": nodes})

    return regions


def is_real_link(tag):
    """True если <a> с href — настоящая гиперссылка. Пустые <a id=..>/
    <a name=..> без href — это якоря, их трогать НЕЛЬЗЯ (иначе сломаем
    цели для ТЗ-01)."""
    return isinstance(tag, Tag) and tag.name == "a" and tag.has_attr("href")


def collect_links_in_region(nodes):
    """Множество (по id Python) реальных гиперссылок <a href> в регионе."""
    found = []
    seen_ids = set()
    for n in nodes:
        if not isinstance(n, Tag):
            continue
        if n.name == "a" and is_real_link(n) and id(n) not in seen_ids:
            seen_ids.add(id(n)); found.append(n)
        for a in n.find_all("a"):
            if is_real_link(a) and id(a) not in seen_ids:
                seen_ids.add(id(a)); found.append(a)
    return found


def unwrap_links_in_nodes(nodes):
    """Снять <a href> в регионе. Пустые <a id/name> (якоря) НЕ трогаем."""
    removed = 0
    for a in collect_links_in_region(nodes):
        a.unwrap()
        removed += 1
    return removed


def count_a_total(soup):
    """Считаем только реальные гиперссылки (<a href>), не якоря."""
    return sum(1 for a in soup.find_all("a") if is_real_link(a))


def process_file(path: Path):
    text = path.read_text(encoding="utf-8")
    soup = BeautifulSoup(text, "html.parser")

    total_a_before = count_a_total(soup)
    regions = find_note_regions(soup)

    # before: уникальные <a href> в любых регионах (по id Python)
    in_note_set = {}
    by_type = {}
    for r in regions:
        type_set = set()
        for a in collect_links_in_region(r["nodes"]):
            in_note_set[id(a)] = a
            type_set.add(id(a))
        by_type[r["type"]] = by_type.get(r["type"], 0) + len(type_set)
    in_note_before = len(in_note_set)
    body_before = total_a_before - in_note_before

    # unwrap. Делаем все unwrap скопом по уникальному набору,
    # чтобы не пытаться unwrap'нуть одну и ту же <a> дважды.
    removed = 0
    for a in in_note_set.values():
        if a.parent is not None:   # ещё не отвязана
            a.unwrap()
            removed += 1

    # после — пересоберём регионы и проверим leftover
    regions2 = find_note_regions(soup)
    leftover_set = set()
    for r in regions2:
        for a in collect_links_in_region(r["nodes"]):
            leftover_set.add(id(a))
    leftover = len(leftover_set)
    total_a_after = count_a_total(soup)
    body_after = total_a_after - leftover

    new_text = str(soup)
    if new_text != text:
        path.write_text(new_text, encoding="utf-8")

    return {
        "removed": removed,
        "leftover": leftover,
        "body_before": body_before,
        "body_after": body_after,
        "in_note_before": in_note_before,
        "total_before": total_a_before,
        "total_after": total_a_after,
        "by_type": by_type,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("codes", nargs="*")
    args = ap.parse_args()

    cfg = json.loads(CODES.read_text(encoding="utf-8"))
    all_codes = [k for k in cfg.keys() if not k.startswith("_") and k != "upk"]
    target = args.codes if args.codes else all_codes
    unknown = [c for c in target if c not in all_codes and c != "upk"]
    if unknown:
        print(f"Неизвестные коды: {unknown}", file=sys.stderr)
        sys.exit(2)

    print(f"{'код':18}{'файл':14}{'removed':>9}{'leftover':>10}"
          f"{'body_b':>9}{'body_a':>9}  by_type")
    print("-" * 100)
    grand = {"removed": 0, "leftover": 0, "body_b": 0, "body_a": 0}
    failures = []
    for code in target:
        for suf in ("ready", "structured"):
            p = FINAL / f"{code}_{suf}.html"
            if not p.exists():
                continue
            r = process_file(p)
            bt = ", ".join(f"{k}={v}" for k, v in sorted(r["by_type"].items()))
            print(f"{code:18}{suf:14}{r['removed']:>9}{r['leftover']:>10}"
                  f"{r['body_before']:>9}{r['body_after']:>9}  {bt}")
            grand["removed"] += r["removed"]
            grand["leftover"] += r["leftover"]
            grand["body_b"]   += r["body_before"]
            grand["body_a"]   += r["body_after"]
            if r["leftover"] != 0 or r["body_before"] != r["body_after"]:
                failures.append((code, suf, r))
    print("-" * 100)
    print(f"{'ИТОГО':32}{grand['removed']:>9}{grand['leftover']:>10}"
          f"{grand['body_b']:>9}{grand['body_a']:>9}")
    if failures:
        print("\nFAIL по файлам:")
        for code, suf, r in failures:
            print(f"  {code}_{suf}: leftover={r['leftover']} "
                  f"body_before={r['body_before']} body_after={r['body_after']}")
        sys.exit(1)


if __name__ == "__main__":
    main()
