# -*- coding: utf-8 -*-
"""ПОЛНО-СПАНОВЫЕ ЦЕПОЧКИ подразделов одной статьи (§3/§8 CLAUDE.md).

Дополняет `71_fullspan_wrap.py`. 71 одиночное «пункт N статьи M» сводит в один
<a>, а ЦЕПОЧКИ из НЕСКОЛЬКИХ подразделов одной статьи помечает COMPLEX и НЕ
трогает. Этот скрипт их дозакрывает:

  «<a>пунктами 4</a> и <a>6</a> <a>статьи 167</a>»      -> один <a> «пунктами 4 и 6 статьи 167»
  «<a>частями второй</a> и <a>третьей</a> статьи 32»    -> один <a> «частями второй и третьей статьи 32»

ПРАВИЛО §4: списки РАЗНЫХ СТАТЕЙ (cross-code «статьями 437 и 438») НЕ сливаются —
там REF-подразделов нет, цепочка не стартует, такие места пропускаются.

Цепочка = РОВНО так: REF (CONNECTOR REF)+ [CONNECTOR] СТАТЬЯ, где
  REF       — <a> «пункт/подпункт/часть/абзац … <номер|порядков.>» (≥2 штук);
  CONNECTOR — плейн-текст только из «и|или|,|;» и пробелов;
  СТАТЬЯ    — терминатор: <a> «статьи M» ЛИБО плейн «статьи M» (поглощается до номера,
              «настоящего Кодекса» НЕ захватываем).

Слияние get_text-ИНВАРИАНТНО (только переносим узлы в первый <a>). href: оставляем
самый левый (самый конкретный) REF, остальные дропаем с логом.

РЕЖИМЫ (как у 71):
  python 73_fullspan_chains.py <code...> [--apply]
    без --apply: ФАЗА 1 ИНВЕНТАРИЗАЦИЯ (read-only) -> data/reports/73_chains_<code>.txt
    --apply    : ФАЗА 2 ПРИМЕНИТЬ с гейтами; перезапись data/final/<code>_ready.html
"""
import re
import sys
import hashlib
from pathlib import Path
from bs4 import BeautifulSoup, NavigableString, Tag

ROOT = Path(__file__).resolve().parent.parent
FINAL = ROOT / "data" / "final"
REPORTS = ROOT / "data" / "reports"

ORD = (r"перв|втор|трет|четверт|пят|шест|седьм|восьм|девят|десят|"
       r"одиннадц|двенадц|тринадц|четырнадц|пятнадц")

# REF-АТОМ цепочки = ЧИСТОЕ подразделение БЕЗ собственной «статьи»:
#   «пунктами 4», «подпунктом 2)», «частью второй», «пункта 11».
# Если в атоме уже есть «стать» — это САМОДОСТАТОЧНАЯ ссылка (её закрыл 71) либо
# элемент списка ДРУГОЙ статьи; такой атом цепочку НЕ начинает и РВЁТ её
# (§3/§4: списки разных статей НЕ сливаем — иначе мислинк «...143» -> z132).
RE_SUBDIV = re.compile(r"^\s*(?:(?:под)?пункт\w*|част\w+|абзац\w*)\b.*?"
                       r"(?:\d+(?:-\d+)?\)?|(?:" + ORD + r")\w*)\s*$", re.I | re.S)
# СТЕМ «стат[ье]», НЕ «стать»: род.падеж мн.ч. «статей» не содержит «стать»
# (находка аудит-раунда 2026-06-10; без этого атом «статей N» не рвал цепочку)
RE_HAS_ART = re.compile(r"стат[ье]", re.I)
# «голый» продолжающий номер/порядковое в списке: «6», «6)», «третьей», «4-1)»
RE_BARE = re.compile(r"^\s*(?:\d+(?:-\d+)?\)?|(?:" + ORD + r")\w*)\s*$", re.I)
RE_ART_A = re.compile(r"^\s*стат[ье]\w*\s+\d", re.I)
# плейн-терминатор: начинается со «статьи M»; поглощаем до номера статьи
RE_ART_PLAIN = re.compile(r"^(?P<gap>\s*)(?P<art>стат[ье]\w*\s+\d+(?:-\d+)?)", re.I)
# чистый соединитель между элементами цепочки
RE_CONNECTOR = re.compile(r"^[\s]*(?:и|или|,|;)?[\s]*$", re.I)
RE_DOCID = re.compile(r"/docs/([A-Za-z0-9_]+)")


def code_path(code):
    return FINAL / f"{code}_ready.html"


def gettext_sha(soup):
    return hashlib.sha256(soup.get_text().encode("utf-8")).hexdigest()


def href_multiset(soup):
    out = {}
    for a in soup.find_all("a", href=True):
        out[a["href"]] = out.get(a["href"], 0) + 1
    return out


def text_of(node):
    return node.get_text() if isinstance(node, Tag) else str(node)


def _link_text(node):
    return node.get_text() if (isinstance(node, Tag) and node.name == "a") else None


def is_ref_link(node):
    """ЧИСТЫЙ subdivision-атом (подразделение БЕЗ собственной «статьи»)."""
    t = _link_text(node)
    return bool(t) and bool(RE_SUBDIV.match(t)) and not RE_HAS_ART.search(t)


def is_bare_link(node):
    """Продолжающий «голый» номер/порядковое в списке: «6», «третьей»."""
    t = _link_text(node)
    return bool(t) and bool(RE_BARE.match(t)) and not RE_HAS_ART.search(t)


def is_atom_link(node):
    return is_ref_link(node) or is_bare_link(node)


def is_art_link(node):
    """Терминатор-ссылка «статьи M …» (может тянуть « Закона …» для cross-code)."""
    t = _link_text(node)
    return bool(t) and bool(RE_ART_A.match(t))


def is_connector(node):
    return isinstance(node, NavigableString) and bool(RE_CONNECTOR.match(str(node)))


def href_target(node):
    """Цель ссылки как сравнимый ключ: ('int',) внутр.#z; ('ext',docid) внешняя;
    ('other',href) прочее; None — не ссылка/без href."""
    if not (isinstance(node, Tag) and node.name == "a" and node.get("href")):
        return None
    h = node["href"].strip()
    if h.startswith("#"):
        return ("int",)
    m = RE_DOCID.search(h)
    return ("ext", m.group(1)) if m else ("other", h)


def homogeneous(head, atoms, term):
    """Все атомы (+терминатор-ссылка) ведут в ОДНУ цель-домен, что и head.
    Плейн-терминатор (term=None) допустим только для внутренних (#z) цепочек."""
    base = href_target(head)
    if base is None:
        return False
    for n in atoms:
        if href_target(n) != base:
            return False
    if term is None:
        return base == ("int",)
    return href_target(term) == base


def chain_from(a):
    """Если a — голова цепочки subdivision-атомов ОДНОЙ статьи, собирает её.

    Цепочка = subdiv-АТОМ (CONNECTOR АТОМ)+ [CONNECTOR] СТАТЬЯ, где:
      • каждый АТОМ — чистое подразделение БЕЗ собственной «статьи» (≥2 штук);
      • все атомы и терминатор ведут в ОДНУ цель (все #z ЛИБО один внешний docid);
      • атом с собственной «статьёй» цепочку РВЁТ (разные статьи НЕ сливаем).
    seq — узлы от первого атома до терминатора включительно (в порядке DOM).
    """
    if not is_ref_link(a):
        return None
    # a должна быть ГОЛОВОЙ: предыдущий значимый — не атом и не коннектор-к-атому
    prev = a.previous_sibling
    if is_connector(prev):
        pp = prev.previous_sibling if prev is not None else None
        if is_atom_link(pp):
            return None  # a в середине цепочки — стартуем не отсюда
    if is_atom_link(prev):
        return None

    seq = [a]
    atoms = [a]
    drops = []
    cur = a.next_sibling
    while cur is not None:
        if is_connector(cur):
            seq.append(cur)
            cur = cur.next_sibling
            continue
        if is_atom_link(cur):
            seq.append(cur)
            atoms.append(cur)
            drops.append(cur.get("href"))
            cur = cur.next_sibling
            continue
        if is_art_link(cur):
            if len(atoms) < 2 or not homogeneous(a, atoms[1:], cur):
                return None
            seq.append(cur)
            drops.append(cur.get("href"))
            before = "".join(text_of(n) for n in seq)
            return {"a": a, "seq": seq, "terminal": "link", "drops": drops,
                    "keep": a.get("href"), "before": before, "after": before}
        if isinstance(cur, NavigableString):
            m = RE_ART_PLAIN.match(str(cur))
            if m:
                if len(atoms) < 2 or not homogeneous(a, atoms[1:], None):
                    return None
                seq.append(("plain_art", cur, m.end("art")))
                before = "".join(
                    text_of(n[1])[:n[2]] if isinstance(n, tuple) else text_of(n)
                    for n in seq)
                return {"a": a, "seq": seq, "terminal": "plain", "drops": drops,
                        "keep": a.get("href"), "before": before, "after": before}
            return None  # посторонний текст -> не чистая цепочка
        return None
    return None


def scan(soup):
    cands = []
    for a in soup.find_all("a"):
        if a.find_parent("a") is not None:
            continue
        c = chain_from(a)
        if c:
            cands.append(c)
    return cands


def apply_chain(c):
    """Сливает всю цепочку в первый <a>. get_text-инвариантно."""
    a = c["a"]
    for node in c["seq"][1:]:
        if isinstance(node, tuple):                  # плейн-терминатор «статьи M …»
            _, textnode, end = node
            s = str(textnode)
            a.append(NavigableString(s[:end]))
            textnode.replace_with(NavigableString(s[end:]))
        elif isinstance(node, Tag):                  # вложенный <a> (REF или ART)
            for child in list(node.children):
                a.append(child.extract())
            node.decompose()
        else:                                        # NavigableString-коннектор
            a.append(node.extract())


def collect_ids(soup):
    ids = set()
    for t in soup.find_all(attrs={"id": True}):
        ids.add(t["id"])
    for t in soup.find_all(attrs={"name": True}):
        ids.add(t["name"])
    return ids


def dangling(soup):
    ids = collect_ids(soup)
    bad = 0
    for a in soup.find_all("a", href=True):
        h = a["href"].strip()
        if h.startswith("#") and h[1:] and h[1:] not in ids:
            bad += 1
    return bad


def nested_count(soup):
    return sum(1 for a in soup.find_all("a") if a.find_parent("a") is not None)


def run(code, apply_mode):
    path = code_path(code)
    soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
    sha0 = gettext_sha(soup)
    href0 = href_multiset(soup)

    cands = scan(soup)
    L = []
    P = L.append
    P("=" * 100)
    P(f"ПОЛНО-СПАНОВЫЕ ЦЕПОЧКИ — {code}_ready.html — "
      f"{'ФАЗА 2 APPLY' if apply_mode else 'ФАЗА 1 ИНВЕНТАРИЗАЦИЯ (read-only)'}")
    P("=" * 100)
    P(f"цепочек-кандидатов: {len(cands)}")
    P("-" * 100)
    for c in cands:
        P(f"[CHAIN×{len(c['drops'])+1}] {c['before']!r:80}  keep={c['keep']}  "
          f"drop={c['drops']}")

    if not apply_mode:
        REPORTS.mkdir(parents=True, exist_ok=True)
        out = REPORTS / f"73_chains_{code}.txt"
        out.write_text("\n".join(L) + "\n", encoding="utf-8")
        print("\n".join(L[:50]))
        print(f"\n[inventory] {code}: chains={len(cands)} -> {out}")
        return

    # ---- ФАЗА 2: применяем по fixpoint (после каждого слияния пере-скан) ----
    applied = 0
    dropped = []
    rounds = 0
    while True:
        rounds += 1
        cs = scan(soup)
        if not cs:
            break
        c = cs[0]
        dropped.extend(c["drops"])
        apply_chain(c)
        applied += 1
        if rounds > 100000:
            raise RuntimeError("fixpoint runaway")

    sha1 = gettext_sha(soup)
    href1 = href_multiset(soup)
    dangle1 = dangling(soup)
    nested1 = nested_count(soup)

    assert sha1 == sha0, f"GET_TEXT CHANGED! {sha0[:12]} -> {sha1[:12]}"
    assert nested1 == 0, f"NESTED <a> = {nested1}"
    assert dangle1 == 0, f"DANGLING #z = {dangle1}"

    expected = {}
    for d in dropped:
        expected[d] = expected.get(d, 0) + 1
    diffs = []
    for k in set(href0) | set(href1):
        delta = href0.get(k, 0) - href1.get(k, 0)
        if delta != expected.get(k, 0):
            diffs.append((k, href0.get(k, 0), href1.get(k, 0), expected.get(k, 0)))
    assert not diffs, f"HREF multiset unexpected change: {diffs}"

    P("-" * 100)
    P(f"ПРИМЕНЕНО цепочек: {applied} (раундов={rounds})")
    P(f"ГЕЙТЫ: get_text sha ДО==ПОСЛЕ={sha0 == sha1} ({sha0[:12]})  nested<a>={nested1}  "
      f"dangling#z={dangle1}  href-diff-unexpected={len(diffs)}")
    P(f"ПОГЛОЩЁННЫЕ href (менее конкретные): {len(dropped)}")

    path.write_text(str(soup), encoding="utf-8")
    REPORTS.mkdir(parents=True, exist_ok=True)
    out = REPORTS / f"73_chains_{code}_applied.txt"
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L[:50]))
    print(f"\n[APPLIED] {code}: chains={applied}  sha-invariant={sha0 == sha1}  "
          f"nested={nested1}  dangling={dangle1}  -> wrote {path.name}")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    apply_mode = "--apply" in sys.argv
    for code in (args or ["grazhdanskiy"]):
        run(code, apply_mode)


if __name__ == "__main__":
    main()
