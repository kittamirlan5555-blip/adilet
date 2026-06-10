# -*- coding: utf-8 -*-
"""TYPE B (ANARA): расширить существующую <a> НАЗАД на слово 'статья'.
«стать*<пробел><a href="#z..">N</a>» ⇒ «<a href="#z..">стать* N</a>».

Детерминированно: href НЕ меняется, видимый текст байт-в-байт (символы те же,
сдвигается только граница тега <a>). Применяется к обеим формам (_structured,
_ready). Гейты: get_text идентичен; число <a> и мультимножество href неизменны;
число расширений в обеих формах совпадает. APPLY только при --apply.
"""
import re, sys, argparse
from collections import Counter
from pathlib import Path
from bs4 import BeautifulSoup, NavigableString

ROOT = Path(__file__).resolve().parents[1]
FINAL = ROOT / "data" / "final"
BARENUM = re.compile(r"^\d+(?:-\d+)?$")
STAT_END = re.compile(r"(стат[ьеи][а-яё]{0,6})\s+$")

def detect(soup):
    ops = []
    for a in soup.find_all("a", href=True):
        if not a["href"].startswith("#z"):
            continue
        if not BARENUM.match(a.get_text().strip()):
            continue
        prev = a.previous_sibling
        if not isinstance(prev, NavigableString):
            continue
        m = STAT_END.search(str(prev))
        if not m:
            continue
        ops.append((a, prev, m.start()))
    return ops

def article_of(a):
    """ближайший предок div[data-type=статья] -> номер (для отчёта)."""
    p = a
    while p is not None:
        if getattr(p, "get", None) and p.get("data-type") == "статья":
            return p.get("data-number", "?")
        p = p.parent
    return "?"

def apply_ops(ops):
    for a, prev, start in ops:
        full = str(prev)
        word = full[start:]                 # 'статьёй '
        keep = full[:start]
        a.string = word + a.get_text()      # '<a>статьёй 38</a>'
        prev.replace_with(NavigableString(keep))

def gate(before_soup_text, after_soup, label, n_expected):
    after_text = after_soup.get_text()
    assert after_text == before_soup_text, f"[{label}] видимый текст изменился!"
    return True

def process(code, do_apply):
    L = []
    res = {}
    for form in ("structured", "ready"):
        p = FINAL / f"{code}_{form}.html"
        raw = p.read_text(encoding="utf-8")
        soup = BeautifulSoup(raw, "html.parser")
        before_text = soup.get_text()
        before_a = len(soup.find_all("a"))
        before_href = Counter(a.get("href") for a in soup.find_all("a", href=True))
        ops = detect(soup)
        arts = []
        for a, prev, start in ops:
            arts.append((article_of(a) if form == "structured" else "", a.get_text().strip(),
                         str(prev)[max(0, start-18):]))
        res[form] = (p, soup, before_text, before_a, before_href, ops, arts, raw)
        L.append(f"  [{form}] найдено TYPE B: {len(ops)}")
        if form == "structured":
            for art, num, ctx in arts:
                L.append(f"      ст.{art:<6} «{ctx}<a>{num}</a>»")
    ns = len(res["structured"][5]); nr = len(res["ready"][5])
    L.append(f"  СИММЕТРИЯ structured={ns} ready={nr}: {ns == nr}")
    if not do_apply:
        L.append("  DRY-RUN (без записи). Запусти с --apply.")
        return "\n".join(L), ns, nr
    # APPLY + GATES
    for form in ("structured", "ready"):
        p, soup, before_text, before_a, before_href, ops, arts, raw = res[form]
        apply_ops(ops)
        gate(before_text, soup, form, len(ops))
        after_a = len(soup.find_all("a"))
        after_href = Counter(a.get("href") for a in soup.find_all("a", href=True))
        assert after_a == before_a, f"[{form}] число <a> изменилось {before_a}->{after_a}"
        assert after_href == before_href, f"[{form}] мультимножество href изменилось"
        L.append(f"  [{form}] GATE: get_text идентичен OK; <a> {before_a}=={after_a} OK; "
                 f"href-set неизменно OK")
        p.write_text(str(soup), encoding="utf-8")
        L.append(f"  ЗАПИСАНО: {p.name}")
    return "\n".join(L), ns, nr

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("codes", nargs="*", default=["zemelnyy"])
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    codes = a.codes or ["zemelnyy"]
    out = ["TYPE B — расширение <a> назад на слово 'статья' (ANARA)", "=" * 70]
    for c in codes:
        out.append(f"\n=== {c} ===")
        rep, ns, nr = process(c, a.apply)
        out.append(rep)
    txt = "\n".join(out) + "\n"
    (ROOT / "data/reports/45_anara_typeB.txt").write_text(txt, encoding="utf-8")
    sys.stdout.write(txt.encode("ascii", "replace").decode("ascii"))

if __name__ == "__main__":
    main()
