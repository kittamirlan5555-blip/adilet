# -*- coding: utf-8 -*-
"""f09_treaty_header.py — возврат Анары: ПЛЕЙН договорная ссылка в ЗАГОЛОВКЕ статьи.

Детектор find_plain_actrefs ловит «Закон/Кодекс РК "Название"», но НЕ договорные
отсылки «статьёй N Договора о Союзе/ЕАЭС» — это отдельный класс. Анара пометила
tamozhenniy ст.211: «статьёй 50 Договора о Союзе» встречается в НАЗВАНИИ статьи
(плейн) и в теле (залинковано → Z1400000240). Линкуем заголовочную.

ЧТО ДЕЛАЕТ:
  • --scan (всегда): корпусный поиск ПЛЕЙН «стать[ёеи]й? N Договора о (Союзе|ЕАЭС)»
    по всем final/*_structured.html — есть ли ещё пропуски детектора.
  • --apply: в tamozhenniy (обе формы) оборачивает «статьел 50» в ЗАГОЛОВКЕ ст.211
    (внутри <b> заголовка) → КОРЕНЬ Z1400000240 (как остальные 9 в теле). Текст не
    меняется, только границы <a>. href = корень (НЕ #z50 — это ст.50 ДОГОВОРА, не
    внутренний якорь).

Гейты: get_text sha ДО==ПОСЛЕ; нет вложенных <a>; dangling#z не вырос; href #z50=0;
ровно 1 обёртка на форму; формы синхронны.

Запуск:
    python scripts/audit/f09_treaty_header.py            # scan + DRY-RUN
    python scripts/audit/f09_treaty_header.py --apply
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import paths
from bs4 import BeautifulSoup, NavigableString
import f06_corpus_actrefs as f06

NGR = "Z1400000240"
HREF = "https://adilet.zan.kz/rus/docs/" + NGR
ART = "211"
ART50 = re.compile(r"стать[ёеи]й?\s+50\b")          # span под обёртку (как в теле)
TREATY = re.compile(r"стать[ёеи]й?\s+\d+(?:\s*[,–-]\s*\d+|\s+и\s+\d+)*"
                    r"\s+Договора\s+о\s+(?:Союзе|Евразийском\s+экономическом\s+союзе|ЕАЭС)")


def scan_corpus():
    """ПЛЕЙН договорные article-refs по корпусу (не в <a>)."""
    out = []
    for p in sorted(paths.FINAL.glob("*_structured.html")):
        soup = BeautifulSoup(p.read_text(encoding="utf-8", errors="replace"), "html.parser")
        for node in soup.find_all(string=True):
            if not isinstance(node, NavigableString) or node.find_parent("a"):
                continue
            s = str(node)
            if "Договора о" not in s:
                continue
            for m in TREATY.finditer(s):
                div = node.find_parent("div", class_="article")
                art = div.get("data-number") if div else "-"
                loc = "ЗАГОЛОВОК" if node.find_parent("b") else "тело"
                out.append((p.stem.replace("_structured", ""), art, loc, m.group(0)))
    return out


def header_hits(soup):
    """Плейн «статьел 50» в <b>-ЗАГОЛОВКЕ ст.211 -> [(node,[(s,e)])].

    Форм-агностично: _structured оборачивает заголовок в <div class=article
    data-number=211>, а _ready — нет (только <p><b><a id=z211>Статья 211…</b></p>).
    Поэтому пиним по самому <b>-заголовку: текст-узел в <b>, содержит «Статья 211»
    и «Договора», вне <a>. Тело (z3386) — в <p id>, не в <b> -> не зацепится."""
    hits = []
    for node in soup.find_all(string=True):
        if not isinstance(node, NavigableString) or node.find_parent("a"):
            continue
        if node.find_parent("b") is None:        # только заголовок (в <b>)
            continue
        s = str(node)
        if "Статья 211" not in s or "Договора" not in s:
            continue
        spans = [(m.start(), m.end()) for m in ART50.finditer(s)]
        if spans:
            hits.append((node, spans))
    return hits


def main():
    apply_mode = "--apply" in sys.argv
    log = []
    P = log.append

    # --- часть 3: корпусный скан ---
    plain = scan_corpus()
    P(f"[ПЕРЕПРОВЕРКА] ПЛЕЙН «стать N Договора о Союзе/ЕАЭС» по корпусу: {len(plain)}")
    for doc, art, loc, ph in plain:
        P(f"    {doc} ст.{art} [{loc}] {ph}")
    P("")

    # --- часть 2: фикс ст.211 заголовок ---
    counts, objs = {}, {}
    for form in f06.FORMS:
        path = paths.FINAL / f"tamozhenniy_{form}.html"
        if not path.exists():
            continue
        soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
        hits = header_hits(soup)
        counts[form] = sum(len(sp) for _, sp in hits)
        objs[form] = (path, soup, hits)
    P(f"[ФИКС] tamozhenniy ст.211 заголовок «статьел 50» -> {NGR} (root): "
      f"{ {f: counts[f] for f in counts} } (ожид 1)")
    for f, n in counts.items():
        assert n == 1, f"tamozhenniy/{f}: найдено {n} != 1"
    if len(counts) == 2:
        assert counts["structured"] == counts["ready"], "формы рассинхрон"

    for form, (path, soup, hits) in objs.items():
        for node, spans in hits:
            for s, e in spans:
                P(f"    [{form}] +<a {NGR}> {str(node)[s:e]}")
        if not apply_mode:
            continue
        sha0 = f06.gettext_sha(soup); d0 = f06.dangling(soup)
        for node, spans in hits:
            s = str(node); pieces = []; last = 0
            for a, b in spans:
                if a > last:
                    pieces.append(NavigableString(s[last:a]))
                link = soup.new_tag("a", href=HREF); link.string = s[a:b]
                pieces.append(link); last = b
            if last < len(s):
                pieces.append(NavigableString(s[last:]))
            node.replace_with(*pieces)
        sha1 = f06.gettext_sha(soup); d1 = f06.dangling(soup); nc = f06.nested_count(soup)
        z50 = str(soup).count('href="#z50"') + len(re.findall(NGR + r"#z50\b", str(soup)))
        assert sha1 == sha0, f"{form}: get_text ИЗМЕНИЛСЯ"
        assert nc == 0, f"{form}: вложенные <a>={nc}"
        assert d1 <= d0, f"{form}: dangling#z вырос {d0}->{d1}"
        assert z50 == 0, f"{form}: появился #z50 (={z50}) — должно быть 0 (root!)"
        path.write_text(str(soup), encoding="utf-8")
        P(f"    [{form}] ЗАПИСАНО +{counts[form]} sha-inv={sha0 == sha1} nested={nc} "
          f"dangling {d0}->{d1} href#z50={z50}")

    report = "\n".join(log)
    print(report)
    out = paths.AUDIT_OUT / "f09_treaty_header_apply.txt"
    out.write_text(report + "\n", encoding="utf-8")
    print(f"\n[лог] {out}")


if __name__ == "__main__":
    main()
