# -*- coding: utf-8 -*-
"""TYPE A apply (ANARA): обернуть в <a> ГЕНУИННО незалинкованные упоминания
внешних актов ПО ИМЕНИ. После фильтрации ложных срабатываний (виджеты сайта,
омонимы-нарицательные, самоссылки, сноски, Pattern-2) реальных кандидатов 4 —
все КоАП (K1400000235):
  predprinimatel ст.147: «Кодекса Республики Казахстан "Об административных правонарушениях"»
  zemelnyy ст.44-2/99/164-1: «об административных правонарушениях» (после «законодательством Республики Казахстан»)

Детерминированно: добавляем ТОЛЬКО <a>-теги, видимый текст байт-в-байт.
Симметрично в _structured и _ready. Гейты: get_text идентичен; число <a>
выросло ровно на N; ни один старый href не пропал. APPLY только при --apply.
"""
import sys, argparse
from collections import Counter
from pathlib import Path
from bs4 import BeautifulSoup, NavigableString, Tag

ROOT = Path(__file__).resolve().parents[1]
FINAL = ROOT / "data" / "final"
KOAP = "https://adilet.zan.kz/rus/docs/K1400000235"

# code -> list of (node_must_contain, phrase_to_wrap, href)
TARGETS = {
    "predprinimatel": [
        ('Кодекса Республики Казахстан "Об административных правонарушениях"',
         'Кодекса Республики Казахстан "Об административных правонарушениях"', KOAP),
    ],
    "zemelnyy": [
        ('законодательством Республики Казахстан об административных правонарушениях',
         'об административных правонарушениях', KOAP),
    ],
}

def in_link(node):
    p = node.parent
    while p is not None and isinstance(p, Tag):
        if p.name == "a" and p.has_attr("href"):
            return True
        p = p.parent
    return False

def wrap_in_node(soup, ns, phrase, href):
    """Разбить NavigableString ns: [before]<a href>phrase</a>[after]. 1 раз."""
    s = str(ns)
    i = s.find(phrase)
    if i < 0:
        return False
    before, after = s[:i], s[i+len(phrase):]
    a = soup.new_tag("a", href=href)
    a.string = phrase
    new_nodes = []
    if before:
        new_nodes.append(NavigableString(before))
    new_nodes.append(a)
    if after:
        new_nodes.append(NavigableString(after))
    ns.replace_with(*new_nodes)
    return True

def process(code, do_apply):
    L = [f"=== {code} ==="]
    res = {}
    for form in ("structured", "ready"):
        p = FINAL / f"{code}_{form}.html"
        soup = BeautifulSoup(p.read_text(encoding="utf-8"), "html.parser")
        before_text = soup.get_text()
        before_a = len(soup.find_all("a"))
        before_href = Counter(a.get("href") for a in soup.find_all("a", href=True))
        # detect target nodes (bare, not inside <a>)
        plan = []  # (ns, phrase, href)
        for need, phrase, href in TARGETS[code]:
            for ns in list(soup.find_all(string=lambda t: isinstance(t, NavigableString) and need in t)):
                if in_link(ns):
                    continue
                plan.append((ns, phrase, href))
        res[form] = (p, soup, before_text, before_a, before_href, plan)
        L.append(f"  [{form}] кандидатов: {len(plan)}")
        for ns, phrase, href in plan:
            ctx = str(ns)
            j = ctx.find(phrase)
            L.append(f"      «…{ctx[max(0,j-20):j]}[{phrase}]{ctx[j+len(phrase):j+len(phrase)+12]}…» -> {href}")
    ns_n = len(res["structured"][5]); nr_n = len(res["ready"][5])
    L.append(f"  СИММЕТРИЯ structured={ns_n} ready={nr_n}: {ns_n == nr_n}")
    if not do_apply:
        L.append("  DRY-RUN (без записи). Запусти с --apply.")
        return "\n".join(L)
    for form in ("structured", "ready"):
        p, soup, before_text, before_a, before_href, plan = res[form]
        n = 0
        for ns, phrase, href in plan:
            if wrap_in_node(soup, ns, phrase, href):
                n += 1
        after_text = soup.get_text()
        after_a = len(soup.find_all("a"))
        after_href = Counter(a.get("href") for a in soup.find_all("a", href=True))
        assert after_text == before_text, f"[{form}] видимый текст изменился!"
        assert after_a == before_a + n, f"[{form}] <a> {before_a}+{n}!={after_a}"
        # ни один старый href не пропал (только добавился KOAP)
        for h, c in before_href.items():
            assert after_href[h] >= c, f"[{form}] потерян href {h}"
        L.append(f"  [{form}] GATE: текст идентичен OK; <a> {before_a}->{after_a} (+{n}) OK; старые href целы OK")
        p.write_text(str(soup), encoding="utf-8")
        L.append(f"  ЗАПИСАНО: {p.name}")
    return "\n".join(L)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    out = ["TYPE A — оборачивание генуинно незалинкованных имён актов (ANARA)", "=" * 78, ""]
    for c in ("predprinimatel", "zemelnyy"):
        out.append(process(c, a.apply))
        out.append("")
    txt = "\n".join(out) + "\n"
    (ROOT / "data/reports/47_anara_typeA.txt").write_text(txt, encoding="utf-8")
    sys.stdout.write(txt.encode("ascii", "replace").decode("ascii"))

if __name__ == "__main__":
    main()
