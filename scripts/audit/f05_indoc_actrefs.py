# -*- coding: utf-8 -*-
"""f05_indoc_actrefs.py — СИСТЕМНЫЙ ФИКС, Партия 1: in-doc резолвимые плейн-акты.

Оборачивает КАЖДОЕ плейн-вхождение фразы-отсылки «Закон/Кодекс РК "Название"»
ПОЛНЫМ СПАНОМ (§3), беря целевой href из УЖЕ-залинкованной ссылки на тот же
акт в ТОМ ЖЕ документе (in-doc резолв). Метод и гейты — по образцу
pipeline/72_external_root_link.py (get_text-инвариантность, нет вложенных <a>,
dangling#z не растёт). Применяется к ОБЕИМ формам (_structured + _ready) с
одинаковым href → синхронность форм по числу.

Источник списка — reports/audit/plain_actrefs.md (строки «в-доке») + 1 mapping
(koap «О разрешениях и уведомлениях» → Z1400000202, подтверждён: 66 ссылок по
корпусу, иных НГР нет).

НЕ ТРОГАЕМ (подтверждено сканом, см. CLAUDE.md §4/§5):
  • nalog «О налогах и других обязательных платежах в бюджет» (самоназвание ст.2
    + датир. на НК-2017 в ст.828/833/848) — резолвится в K2500000214, НЕ в ALLOW;
  • tamozhenniy «О таможенном деле…» — вложено в имя закона-о-введении; doc вне batch.
Фильтр строгий: оборачиваем ТОЛЬКО (doc, НГР) из ALLOW_NGR + один SPECIAL-тайтл.

Запуск:
    python scripts/audit/f05_indoc_actrefs.py            # DRY-RUN (отчёт)
    python scripts/audit/f05_indoc_actrefs.py --apply    # запись обеих форм
"""
import sys
import re
import json
import hashlib
from pathlib import Path
from collections import Counter, defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import paths
from bs4 import BeautifulSoup, NavigableString

HOST = "https://adilet.zan.kz/rus/docs/"
SKIP_PARENTS = {"a", "script", "style", "head", "title"}

KW = (r"(?:Конституционн(?:ый|ым|ого|ому|ом)\s+)?"
      r"(?:[Зз]акон(?:ом|а|е|у|ами|ах)?|[Кк]одекс(?:ом|а|е|у)?)")
DATE = r"(?:\s+от\s+[^\"«»\n]{0,80}?)?"
TITLE = r"(?:«[^»]{3,500}»|\"[^\"]{3,500}\")"
ACTREF = re.compile(KW + r"\s+Республики\s+Казахстан" + DATE + r"\s*(" + TITLE + r")")
QUOTE = re.compile(r"(?:«([^»]{3,500})»|\"([^\"]{3,500})\")")
NGRH = re.compile(r"/docs/([A-Za-z0-9_]+)")

# (doc -> множество разрешённых НГР для in-doc обёртки) + ожидаемое число вхождений
ALLOW_NGR = {
    "vodniy":            {"Z2300000030"},
    "oNedrah":           {"Z100000291_"},
    "zhilishniy":        {"Z070000310_", "Z2300000014"},
    "grazhdanskiy_osob": {"Z990000456_"},
    "koap":              {"K1700000123", "Z030000415_"},
    "ugolovniy":         {"Z1400000213"},
    "nalog":             {"Z070000234_", "Z1500000405"},
    "goszakup":          {"Z2300000030"},
}
# SPECIAL: акт без in-doc ссылки -> корень (§4). Ключ = (doc, norm(title)).
SPECIAL = {("koap", "о разрешениях и уведомлениях"): HOST + "Z1400000202"}
# Ожидаемое число обёрток на ДОКУМЕНТ (на каждую форму).
EXPECT = {"vodniy": 1, "oNedrah": 4, "zhilishniy": 4, "grazhdanskiy_osob": 2,
          "koap": 3, "ugolovniy": 1, "nalog": 2, "goszakup": 2}
FORMS = ("structured", "ready")


def norm(s):
    s = s.lower(); s = re.sub(r"[^0-9a-zа-яё]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def title_of(ph):
    m = QUOTE.search(ph)
    return (m.group(1) or m.group(2)).strip() if m else ""


def gettext_sha(soup):
    return hashlib.sha256(soup.get_text().encode("utf-8")).hexdigest()


def in_skip(node):
    p = node.parent
    while p is not None:
        if getattr(p, "name", None) in SKIP_PARENTS:
            return True
        p = p.parent
    return False


def collect_ids(soup):
    ids = set()
    for t in soup.find_all(attrs={"id": True}):
        ids.add(t["id"])
    for t in soup.find_all(attrs={"name": True}):
        ids.add(t["name"])
    return ids


def dangling(soup):
    ids = collect_ids(soup)
    return sum(1 for a in soup.find_all("a", href=True)
              if a["href"].strip().startswith("#")
              and a["href"].strip()[1:] and a["href"].strip()[1:] not in ids)


def nested_count(soup):
    return sum(1 for a in soup.find_all("a") if a.find_parent("a") is not None)


def canon_hrefs(soup, allow):
    """norm(title) -> канонический href (verbatim из существующей in-doc ссылки),
    только для титулов, чей НГР ∈ allow. Если несколько href — берём самый частый,
    при равенстве предпочитаем КОРЕНЬ (без #)."""
    bytitle = defaultdict(Counter)
    for a in soup.find_all("a", href=True):
        t = title_of(a.get_text())
        if not t:
            continue
        m = NGRH.search(a["href"])
        if m and m.group(1) in allow:
            bytitle[norm(t)][a["href"]] += 1
    out = {}
    for key, c in bytitle.items():
        best = sorted(c.items(), key=lambda kv: (-kv[1], "#" in kv[0]))[0][0]
        out[key] = best
    return out


def find_targets(soup, code, canon):
    """[(node, [(s,e,href)])] — плейн-вхождения, которые НАДО обернуть."""
    hits = []
    for t in soup.find_all(string=True):
        if not isinstance(t, NavigableString) or in_skip(t) or not str(t).strip():
            continue
        s = str(t)
        if "Республики Казахстан" not in s:
            continue
        spans = []
        for m in ACTREF.finditer(s):
            key = norm(title_of(m.group(0)))
            href = None
            if key in canon:                       # in-doc резолв
                href = canon[key]
            elif (code, key) in SPECIAL:           # mapping -> корень
                href = SPECIAL[(code, key)]
            if href:
                spans.append((m.start(), m.end(), href))
        if spans:
            spans.sort()
            hits.append((t, spans))
    return hits


def run(code, apply_mode, log):
    canon = None
    results = {}
    for form in FORMS:
        path = paths.FINAL / f"{code}_{form}.html"
        if not path.exists():
            log.append(f"  [{code}/{form}] нет файла — пропуск")
            continue
        soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
        if canon is None:        # канон href берём из _structured, применяем к обеим
            canon = canon_hrefs(soup, ALLOW_NGR.get(code, set()))
        hits = find_targets(soup, code, canon)
        n = sum(len(sp) for _, sp in hits)
        results[form] = (path, soup, hits, n)

    # сверка ожидаемого числа и синхронности форм
    counts = {f: r[3] for f, r in results.items()}
    exp = EXPECT[code]
    log.append(f"== {code}: ожидаем {exp}/форму; найдено { {f: counts[f] for f in counts} }")
    for f, n in counts.items():
        assert n == exp, f"{code}/{f}: найдено {n} != ожидаемо {exp}"
    if len(counts) == 2:
        assert counts["structured"] == counts["ready"], f"{code}: формы рассинхрон"

    for form, (path, soup, hits, n) in results.items():
        for t, spans in hits:
            for s, e, href in spans:
                ph = str(t)[s:e]
                log.append(f"   [{form}] +<a {href}> {ph[:80]}")
        if not apply_mode:
            continue
        sha0 = gettext_sha(soup); d0 = dangling(soup)
        for t, spans in hits:
            s = str(t); pieces = []; last = 0
            for a, b, href in spans:
                if a > last:
                    pieces.append(NavigableString(s[last:a]))
                link = soup.new_tag("a", href=href)
                link.string = s[a:b]
                pieces.append(link); last = b
            if last < len(s):
                pieces.append(NavigableString(s[last:]))
            t.replace_with(*pieces)
        sha1 = gettext_sha(soup); d1 = dangling(soup); nc = nested_count(soup)
        assert sha1 == sha0, f"{code}/{form}: get_text ИЗМЕНИЛСЯ {sha0[:12]}->{sha1[:12]}"
        assert nc == 0, f"{code}/{form}: вложенные <a> = {nc}"
        assert d1 <= d0, f"{code}/{form}: dangling#z вырос {d0}->{d1}"
        path.write_text(str(soup), encoding="utf-8")
        log.append(f"   [{form}] ЗАПИСАНО +{n}  sha-inv={sha0==sha1} nested={nc} dangling {d0}->{d1}")
    return sum(counts.values())


def main():
    apply_mode = "--apply" in sys.argv
    log = ["DRY-RUN (без записи)" if not apply_mode else "APPLY (запись обеих форм)", ""]
    total = 0
    for code in ALLOW_NGR:
        total += run(code, apply_mode, log)
    log.append("")
    log.append(f"ИТОГО обёрток по всем формам: {total}")
    report = "\n".join(log)
    print(report)
    out = paths.AUDIT_OUT / "f05_indoc_actrefs_apply.txt"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(report + "\n", encoding="utf-8")
    print(f"\n[лог] {out}")


if __name__ == "__main__":
    main()
