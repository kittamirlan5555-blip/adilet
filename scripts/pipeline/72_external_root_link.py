# -*- coding: utf-8 -*-
"""ВНЕШНИЕ АКТЫ -> КОРЕНЬ документа adilet (§4/§8 CLAUDE.md).

Полный спан всей фразы «Законом РК "Название"» -> `…/docs/{НГР}` БЕЗ #z (корень).
Корень не зависит от внутренней нумерации и не ломается — безопасный дефолт.

Источник фраз и кодов: `config/npa_mapping.json` (фраза названия акта -> НГР).
ВНИМАНИЕ §5: маппинг местами протух — ПЕРЕД массовым применением прогони
`74_code_freshness_check.py` и почини протухшие НГР; иначе наплодишь ссылок на
старые редакции. Этот скрипт берёт НГР как есть из mapping.

ЧТО ДЕЛАЕТ (КОНСЕРВАТИВНО, get_text-инвариантно):
  • APPLY: оборачивает в `<a href=root>` фразы акта, которые лежат ПОЛНОСТЬЮ в
    одном плейн-текстовом узле (НЕ внутри уже существующей <a>). Это «полностью
    не залинкованное упоминание акта» — самый частый ручной хвост, чистое
    добавление ссылки (видимый текст не меняется).
  • INVENTORY/REPORT: фразы, которые ПЕРЕСЕКАЮТСЯ с существующей <a>
    (частично залинкованы / ведут на #z / на другой акт) — НЕ трогает, выписывает
    как «ручной разбор» (ретаргет существующих ссылок без валидации опасен).

ГЕЙТЫ (apply): get_text sha ДО==ПОСЛЕ; нет вложенных <a>; все ВНОВЬ добавленные
href — чистые корни вида `…/docs/{НГР}` без #фрагмента; dangling#z не вырос.

РЕЖИМЫ:
  python 72_external_root_link.py <code...> [--apply] [--min-len N]
    без --apply: ФАЗА 1 ИНВЕНТАРИЗАЦИЯ (read-only) -> data/reports/72_external_<code>.txt
    --apply    : оборачивает PLAIN-кейсы; перезапись data/final/<code>_ready.html
    --min-len  : мин. длина фразы для матча (по умолчанию 16; анти-overlink).
"""
import re
import sys
import json
import hashlib
from pathlib import Path
from bs4 import BeautifulSoup, NavigableString, Tag

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import paths

ROOT = paths.ROOT
FINAL = paths.FINAL
CONFIG = paths.MAPS      # config/ слит в maps/ (Фаза A)
REPORTS = paths.GATES    # машинные гейт-отчёты (дерево v2)

HOST = "https://adilet.zan.kz/rus/docs/"
SKIP_PARENTS = {"a", "script", "style", "head", "title"}

# Префикс акта ПЕРЕД кавычкой-именем: «Закон[ом/а/…]/Кодекс[…]/Конституционн[ым] закон[…]»
# опц. «Республики Казахстан|РК», с завершающим пробелом, в КОНЦЕ текст-узла. Явные
# склонения «закон», НЕ «\w*» — иначе поглотит «Законодательством…» (описательный класс §4).
# склонения (ами|ам ДО ам — «законами» не должно резаться до «законам»); мн.ч. ах/ы для
# «согласно законам РК», «в законах РК», «Законы РК "…"».
PREFIX_END = re.compile(
    r"(?:(?<=\s)|^)"
    r"(?:[Зз]акон(?:ами|ам|ах|ов|ом|а|е|у|ы)?|[Кк]одекс(?:ами|ам|ах|ов|ом|а|е|у|ы)?|"
    r"[Кк]онституционны[йм]\s+закон(?:ом|а|е)?|[Кк]онституционного\s+закона)"
    r"(?:\s+Республики\s+Казахстан|\s+РК)?\s+$")
# ЛАТЕНТНАЯ ЛОВУШКА (внешний аудит): «настоящего/настоящим Закон*» = САМ этот закон
# (внутренняя ссылка), НЕ внешний «Законом РК "X"». Не поглощаем такой префикс.
NASTOYASH = re.compile(r"настоящ\w*\s*$", re.I)


def absorb_prefix(soup):
    """Корпусный стандарт (final/upk_ready.html): «<a>Законом РК "Название"</a>» —
    ПРЕФИКС ВНУТРИ спана. 03 линкует только «"Название"», префикс остаётся плейн-текстом
    снаружи (класс дефекта внешнего аудита). Двигаем ЛЕВУЮ границу <a> влево, поглощая
    префикс из соседнего текст-узла. По DOM: text-invariant, вложенность невозможна
    (переносим sibling-текст ВНУТРЬ), идемпотентно (после — <a> начинается не с кавычки)."""
    moved = 0
    for a in soup.find_all("a", href=True):
        h = a["href"].strip()
        if not (h.startswith(HOST) and "#" not in h):
            continue                                   # только внешний КОРЕНЬ
        txt = a.get_text()
        if not txt or txt[0] not in '"«':              # спан должен начинаться с имени-кавычки
            continue
        prev = a.previous_sibling
        if not isinstance(prev, NavigableString):
            continue
        s = str(prev)
        m = PREFIX_END.search(s)
        if not m:
            continue
        prefix, head = s[m.start():], s[:m.start()]    # «Законом Республики Казахстан », «…с »
        if NASTOYASH.search(head):                     # «настоящего Закона» — само-ссылка, не трогаем
            continue
        first = a.contents[0] if a.contents else None
        if isinstance(first, NavigableString):
            first.replace_with(NavigableString(prefix + str(first)))
        else:
            a.insert(0, NavigableString(prefix))
        prev.replace_with(NavigableString(head))
        moved += 1
    return moved


def code_path(code):
    return FINAL / f"{code}_ready.html"


def root_url(docid):
    return HOST + docid


def gettext_sha(soup):
    return hashlib.sha256(soup.get_text().encode("utf-8")).hexdigest()


def load_phrases(min_len):
    """[(compiled_regex, phrase, docid)] отсортировано по длине фразы убыв."""
    m = json.loads((CONFIG / "npa_mapping.json").read_text(encoding="utf-8"))
    items = []
    for phrase, docid in m.items():
        if len(phrase) < min_len:
            continue
        # ws-гибкий, регистронезависимый паттерн из фразы
        pat = re.escape(phrase)
        pat = re.sub(r"\\\s+", r"\\s+", pat)        # любые пробелы -> \s+
        items.append((re.compile(pat, re.I), phrase, docid))
    items.sort(key=lambda x: -len(x[1]))
    return items


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
              and a["href"].strip()[1:]
              and a["href"].strip()[1:] not in ids)


def nested_count(soup):
    return sum(1 for a in soup.find_all("a") if a.find_parent("a") is not None)


def find_in_text(s, phrases):
    """Непересекающиеся матчи (longest-first) в строке s. -> [(start,end,docid,phrase)]"""
    spans = []
    taken = [False] * len(s)
    for rx, phrase, docid in phrases:
        for m in rx.finditer(s):
            a, b = m.start(), m.end()
            if any(taken[a:b]):
                continue
            spans.append((a, b, docid, phrase))
            for i in range(a, b):
                taken[i] = True
    spans.sort()
    return spans


def block_partials(soup, phrases):
    """Фразы, которые есть в тексте блока, но ПЕРЕСЕКАЮТ существующую <a>.
    READ-ONLY: только для отчёта 'ручной разбор'."""
    out = []
    seen = set()
    for a in soup.find_all("a", href=True):
        block = a.find_parent(["p", "li", "td", "dd", "div"]) or a.parent
        if id(block) in seen:
            continue
        seen.add(id(block))
        full = block.get_text()
        for rx, phrase, docid in phrases:
            for m in rx.finditer(full):
                # есть ли внутри блока <a>, чей текст пересекается с фразой?
                # грубо: если фраза в блоке и в блоке есть <a> с куском фразы
                for aa in block.find_all("a"):
                    at = aa.get_text()
                    if at and at in phrase and at.strip():
                        out.append((docid, phrase, at))
                        break
                break
    # dedup
    uniq = []
    s = set()
    for d, p, at in out:
        k = (d, p, at)
        if k not in s:
            s.add(k)
            uniq.append((d, p, at))
    return uniq


def run(code, apply_mode, min_len):
    path = code_path(code)
    soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
    phrases = load_phrases(min_len)
    sha0 = gettext_sha(soup)
    dangle0 = dangling(soup)

    # ---- найти PLAIN-кандидаты (фраза целиком в одном не-<a> текстовом узле) ----
    text_nodes = [t for t in soup.find_all(string=True)
                  if isinstance(t, NavigableString) and not in_skip(t) and str(t).strip()]
    plain_hits = []           # (node, [(s,e,docid,phrase)])
    for t in text_nodes:
        spans = find_in_text(str(t), phrases)
        if spans:
            plain_hits.append((t, spans))

    partials = block_partials(soup, phrases)

    L = []
    P = L.append
    P("=" * 100)
    P(f"ВНЕШНИЕ АКТЫ -> КОРЕНЬ — {code}_ready.html — "
      f"{'ФАЗА 2 APPLY' if apply_mode else 'ФАЗА 1 ИНВЕНТАРИЗАЦИЯ (read-only)'}")
    P("=" * 100)
    n_plain = sum(len(sp) for _, sp in plain_hits)
    P(f"PLAIN (фраза целиком в плейн-тексте, БУДЕТ обёрнута в корень): {n_plain}")
    P(f"PARTIAL (пересекает существующую <a>, ручной разбор, НЕ трогаем): {len(partials)}")
    P("-" * 100)
    for t, spans in plain_hits:
        for s, e, docid, phrase in spans:
            P(f"[PLAIN] -> {root_url(docid)}   {str(t)[max(0,s-15):s]!r}[{str(t)[s:e]}]")
    P("-" * 100)
    for docid, phrase, at in partials[:200]:
        P(f"[PARTIAL] {root_url(docid)}  фраза={phrase!r}  уже-линк-кусок={at!r}")

    if not apply_mode:
        REPORTS.mkdir(parents=True, exist_ok=True)
        out = REPORTS / f"72_external_{code}.txt"
        out.write_text("\n".join(L) + "\n", encoding="utf-8")
        print("\n".join(L[:60]))
        print(f"\n[inventory] {code}: PLAIN={n_plain} PARTIAL={len(partials)} -> {out}")
        return

    # ---- ФАЗА 2: оборачиваем PLAIN-кейсы ----
    added = 0
    for t, spans in plain_hits:
        s = str(t)
        pieces = []
        last = 0
        for a, b, docid, phrase in spans:
            if a > last:
                pieces.append(NavigableString(s[last:a]))
            link = soup.new_tag("a", href=root_url(docid))
            link.string = s[a:b]
            pieces.append(link)
            added += 1
            last = b
        if last < len(s):
            pieces.append(NavigableString(s[last:]))
        # заменить узел на последовательность
        t.replace_with(*pieces)

    # ---- ПОГЛОЩЕНИЕ ПРЕФИКСА «Законом РК» в уже-залинкованное имя (корп. стандарт) ----
    absorbed = absorb_prefix(soup)

    sha1 = gettext_sha(soup)
    dangle1 = dangling(soup)
    nested1 = nested_count(soup)
    assert sha1 == sha0, f"GET_TEXT CHANGED! {sha0[:12]} -> {sha1[:12]}"
    assert nested1 == 0, f"NESTED <a> = {nested1}"
    assert dangle1 <= dangle0, f"DANGLING #z grew {dangle0} -> {dangle1}"

    P("-" * 100)
    P(f"ДОБАВЛЕНО корневых ссылок: {added}")
    P(f"ПОГЛОЩЕНО префиксов «Закон* РК» в спан: {absorbed}")
    P(f"ГЕЙТЫ: get_text sha ДО==ПОСЛЕ={sha0 == sha1} ({sha0[:12]})  nested<a>={nested1}  "
      f"dangling#z {dangle0}->{dangle1}")

    path.write_text(str(soup), encoding="utf-8")
    REPORTS.mkdir(parents=True, exist_ok=True)
    out = REPORTS / f"72_external_{code}_applied.txt"
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L[:60]))
    print(f"\n[APPLIED] {code}: +{added} root links, +{absorbed} prefix-absorbed  "
          f"sha-invariant={sha0 == sha1}  nested={nested1}  -> wrote {path.name}")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    apply_mode = "--apply" in sys.argv
    min_len = 16
    if "--min-len" in sys.argv:
        min_len = int(sys.argv[sys.argv.index("--min-len") + 1])
    for code in (args or ["grazhdanskiy"]):
        run(code, apply_mode, min_len)


if __name__ == "__main__":
    main()
