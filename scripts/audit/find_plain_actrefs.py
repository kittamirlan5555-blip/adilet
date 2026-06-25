# -*- coding: utf-8 -*-
"""find_plain_actrefs.py — аудит ПЛЕЙН-ссылок на акты по всему final/*_structured.html.

Анара просит: выявлять должна ПРОГРАММА, не она руками. Скрипт по каждому
документу ищет фразы-отсылки к актам вида

    «Закон[ом/а/е] Республики Казахстан "Название"»
    «Кодекс[ом/а/е] Республики Казахстан [от ДАТА] "Название"»
    «Конституционн(ый/ым) закон[ом] Республики Казахстан "Название"»

и для КАЖДОГО вхождения определяет — обёрнуто ли оно в <a>. Выводятся ТОЛЬКО
ПЛЕЙН вхождения (каждое отдельно, не «есть ли хоть одна ссылка»), таблицей:

    документ | статья | якорь | фраза | резолвимый NGR (уже есть в доке/в маппинге)

Сноски/примечания (<span class="note">, текст «Сноска…») по ТЗ-02 не линкуем —
они помечаются отдельно и выносятся в свою секцию.

Дополнительно (диагностика полного спана §3): «рваные» (torn) ссылки —
когда в <a> попало только ключевое слово («Кодекс»), а «Республики Казахстан
"…"» осталось плейн-хвостом.

ВАЖНО: скрипт НИЧЕГО не правит — только читает и пишет отчёт.

Запуск:
    python scripts/audit/find_plain_actrefs.py            # все файлы, отчёт в reports/audit/
    python scripts/audit/find_plain_actrefs.py vodniy     # один слаг
    python scripts/audit/find_plain_actrefs.py --no-md     # только stdout
"""
import sys
import re
import json
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import paths  # noqa: E402  (побочный эффект: utf-8 stdout)

from bs4 import BeautifulSoup, NavigableString  # noqa: E402

# --- регэксп фразы-отсылки ------------------------------------------------
# Ключевое слово: Закон/Кодекс с падежными окончаниями (+ опц. «Конституционный»).
# \b-границы не дают зацепить «Законодательством», «кодификация» и т.п.
KW = (
    r"(?:Конституционн(?:ый|ым|ого|ому|ом)\s+)?"
    r"(?:[Зз]акон(?:ом|а|е|у|ами|ах)?|[Кк]одекс(?:ом|а|е|у)?)"
)
# Дата между «Республики Казахстан» и названием: «от 30 июня 2010 года»,
# «от 7 июня 1999 г.», «от 25 декабря 2017 года № 120-VI» — всё, что между
# «от» и открывающей кавычкой (без кавычек внутри, до 80 симв.). Опциональна.
DATE = r"(?:\s+от\s+[^\"«»\n]{0,80}?)?"
# Кавычки: парные «…» либо "…" (без вложенных одноимённых).
TITLE = r"(?:«[^»]{3,500}»|\"[^\"]{3,500}\")"

ACTREF = re.compile(
    KW + r"\s+Республики\s+Казахстан" + DATE + r"\s*(" + TITLE + r")"
)
# Заголовок кавычек для извлечения только названия акта.
QUOTE = re.compile(r"(?:«([^»]{3,500})»|\"([^\"]{3,500})\")")
NGR_IN_HREF = re.compile(r"/docs/([A-Za-z0-9_]+)")


def norm(s: str) -> str:
    """Нормализация названия акта для сопоставления: lower, схлоп пробелов,
    только буквы/цифры (кавычки/тире/№ выкидываем)."""
    s = s.lower()
    s = re.sub(r"[^0-9a-zа-яё]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def extract_title(phrase: str) -> str:
    m = QUOTE.search(phrase)
    if not m:
        return ""
    return (m.group(1) or m.group(2) or "").strip()


def load_npa_mapping():
    """npa_mapping: имя акта → НГР. Ключи нормализуем. ВНИМАНИЕ: маппинг местами
    протух (CLAUDE.md §5) — пометка 'mapping' = кандидат, сверять вручную."""
    try:
        raw = json.loads(paths.NPA_MAPPING.read_text(encoding="utf-8"))
    except Exception:
        return {}
    out = {}
    for name, ngr in raw.items():
        out.setdefault(norm(name), ngr)
    return out


NPA = load_npa_mapping()


def article_of(node):
    """Номер статьи = data-number ближайшего <div class='article'>."""
    div = node.find_parent("div", class_="article")
    if div is None:
        return "-"
    return div.get("data-number") or "-"


def anchor_of(node):
    """Ближайший предок с id (обычно <p id='zN'>) — точное место."""
    for p in node.parents:
        if getattr(p, "get", None) and p.get("id"):
            return p.get("id")
    return "-"


def is_note(node):
    """Сноска/примечание: предок с class~='note' ИЛИ текст начинается 'Сноска'."""
    for p in node.parents:
        cls = getattr(p, "get", lambda *_: None)("class")
        if cls and any("note" in c for c in cls):
            return True
    txt = str(node).lstrip()
    return txt.startswith("Сноска")


def build_doc_linkmap(soup):
    """title_norm → set(NGR) по ВСЕМ <a> документа (резолвер 'уже есть в доке')."""
    m = {}
    for a in soup.find_all("a", href=True):
        ngr_m = NGR_IN_HREF.search(a.get("href", ""))
        if not ngr_m:
            continue
        ngr = ngr_m.group(1)
        title = extract_title(a.get_text())
        if title:
            m.setdefault(norm(title), set()).add(ngr)
    return m


def resolve_ngr(title, linkmap):
    """Где взять NGR: сначала уже залинкованный тот же акт В ЭТОМ доке, затем маппинг."""
    key = norm(title)
    if key in linkmap:
        ngrs = sorted(linkmap[key])
        return (",".join(ngrs), "в-доке")
    if key in NPA:
        return (NPA[key], "mapping(сверить)")
    return ("", "—")


def scan_file(path: Path):
    html = path.read_text(encoding="utf-8", errors="replace")
    soup = BeautifulSoup(html, "lxml")
    linkmap = build_doc_linkmap(soup)

    plain, notes, torn = [], [], []

    # --- ПЛЕЙН: текстовые узлы ВНЕ <a> ---
    for node in soup.find_all(string=True):
        if not isinstance(node, NavigableString):
            continue
        if node.find_parent("a") is not None:
            continue  # внутри ссылки — значит залинковано
        text = str(node)
        if "Республики Казахстан" not in text:
            continue
        for m in ACTREF.finditer(text):
            phrase = m.group(0).strip()
            title = extract_title(phrase)
            ngr, src = resolve_ngr(title, linkmap)
            rec = {
                "doc": path.stem.replace("_structured", ""),
                "article": article_of(node),
                "anchor": anchor_of(node),
                "phrase": re.sub(r"\s+", " ", phrase),
                "title": title,
                "ngr": ngr,
                "ngr_src": src,
            }
            (notes if is_note(node) else plain).append(rec)

    # --- TORN: в <a> только ключевое слово, хвост «Республики Казахстан "…"» плейн ---
    for a in soup.find_all("a"):
        atext = a.get_text().strip()
        if not re.fullmatch(KW, atext):
            continue
        sib = a.next_sibling
        tail = str(sib) if isinstance(sib, NavigableString) else ""
        head = tail[:600]
        if head.lstrip().startswith("Республики Казахстан") and QUOTE.search(head):
            qm = QUOTE.search(head)
            title = (qm.group(1) or qm.group(2) or "").strip()
            ngr, src = resolve_ngr(title, linkmap)
            tail_phrase = re.sub(r"\s+", " ", head[: qm.end()]).strip()
            torn.append({
                "doc": path.stem.replace("_structured", ""),
                "article": article_of(a),
                "anchor": anchor_of(a),
                "phrase": (atext + " " + tail_phrase).strip(),
                "title": title,
                "ngr": ngr,
                "ngr_src": src,
                "linked_to": NGR_IN_HREF.search(a.get("href", "")).group(1)
                if a.get("href") and NGR_IN_HREF.search(a.get("href", "")) else "",
            })

    return plain, notes, torn


def fmt_table(rows):
    if not rows:
        return "_(пусто)_\n"
    head = "| документ | ст. | якорь | фраза | NGR | источник |\n"
    head += "|---|---|---|---|---|---|\n"
    out = [head]
    for r in rows:
        ph = r["phrase"].replace("|", "\\|")
        if len(ph) > 90:
            ph = ph[:90] + "…"
        out.append(
            f"| {r['doc']} | {r['article']} | {r['anchor']} | {ph} "
            f"| {r['ngr'] or '—'} | {r['ngr_src']} |\n"
        )
    return "".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("slugs", nargs="*", help="слаги (без _structured); пусто = все")
    ap.add_argument("--no-md", action="store_true", help="не писать markdown-отчёт")
    args = ap.parse_args()

    files = sorted(paths.FINAL.glob("*_structured.html"))
    if args.slugs:
        want = set(args.slugs)
        files = [f for f in files if f.stem.replace("_structured", "") in want]

    all_plain, all_notes, all_torn = [], [], []
    for f in files:
        p, n, t = scan_file(f)
        all_plain += p
        all_notes += n
        all_torn += t

    # сортировка для читаемости
    keyf = lambda r: (r["doc"], _num(r["article"]), r["anchor"])
    all_plain.sort(key=keyf)
    all_notes.sort(key=keyf)
    all_torn.sort(key=keyf)

    lines = []
    lines.append("# Плейн-ссылки на акты (find_plain_actrefs)\n")
    lines.append(f"Файлов просканировано: **{len(files)}**\n")
    lines.append(f"\n## A. ПЛЕЙН (не в <a>) — линковать полным спаном: {len(all_plain)}\n\n")
    lines.append(fmt_table(all_plain))
    lines.append(f"\n## B. РВАНЫЕ (torn: в <a> только ключевое слово): {len(all_torn)}\n\n")
    lines.append(fmt_table_torn(all_torn))
    lines.append(f"\n## C. Сноски/примечания (по ТЗ-02 НЕ линкуем, если Анара не подсветила): {len(all_notes)}\n\n")
    lines.append(fmt_table(all_notes))
    report = "".join(lines)

    print(report)

    if not args.no_md:
        out = paths.AUDIT_OUT / "plain_actrefs.md"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(report, encoding="utf-8")
        print(f"\n[отчёт записан] {out}")


def fmt_table_torn(rows):
    if not rows:
        return "_(пусто)_\n"
    out = ["| документ | ст. | якорь | фраза | в <a> ведёт на | NGR(акта) |\n",
           "|---|---|---|---|---|---|\n"]
    for r in rows:
        ph = r["phrase"].replace("|", "\\|")
        out.append(
            f"| {r['doc']} | {r['article']} | {r['anchor']} | {ph} "
            f"| {r.get('linked_to','')} | {r['ngr'] or '—'} |\n"
        )
    return "".join(out)


def _num(a):
    m = re.match(r"(\d+)", str(a))
    return (int(m.group(1)) if m else 10**9, str(a))


if __name__ == "__main__":
    main()
