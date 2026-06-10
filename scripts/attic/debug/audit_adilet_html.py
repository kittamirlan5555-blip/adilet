import os
import re
import csv
import argparse
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup


# --- regex для "упоминаний" (кандидаты на отсутствующие ссылки) ---
ARTICLE_MENTION_RE = re.compile(r'\b(статья|статьи|статьей)\s+(\d+)\b', re.IGNORECASE)
POINT_ARTICLE_RE = re.compile(r'\b(пункт|пункта)\s+(\d+)\s+(статьи|статья|статьей)\s+(\d+)\b', re.IGNORECASE)
# под "подпункт 46)" в тексте часто так и пишут
SUBPOINT_RE = re.compile(
    r'\b(подпункт|подпункта)\s+(\d+)\)\s+(пункта|пункт)\s+(\d+)\s+(статьи|статья|статьей)\s+(\d+)\b',
    re.IGNORECASE
)

# вытащить ID документа из /rus/docs/<DOCID>
DOC_ID_RE = re.compile(r'/rus/docs/([A-Za-z0-9_]+)', re.IGNORECASE)

# якоря у адилета вида z235 / z1 / z299 ...
ANCHOR_RE = re.compile(r'^z\d+(_\d+)?$', re.IGNORECASE)


def read_html(path: str) -> BeautifulSoup:
    with open(path, "rb") as f:
        data = f.read()
    return BeautifulSoup(data, "html.parser")


def clean_noise(soup: BeautifulSoup) -> None:
    """
    Удаляем шум: расширения, скрипты, стили, шаблоны.
    В твоём примере есть veepn-lock-screen (chrome extension).
    """
    for tag_name in ["script", "style", "template"]:
        for t in soup.find_all(tag_name):
            t.decompose()

    # выкинуть расширение VPN, если есть
    for t in soup.find_all("veepn-lock-screen"):
        t.decompose()


def extract_doc_id(soup: BeautifulSoup) -> str | None:
    # Самый надёжный источник — HTML comment "saved from url=..."
    # Но в твоём фрагменте оно есть как "<!-- saved from url=(...)http://.../rus/docs/K... -->"
    comments = soup.find_all(string=lambda x: isinstance(x, type(soup.comment)))


    # fallback: ищем по href
    for a in soup.find_all("a", href=True):
        m = DOC_ID_RE.search(a["href"])
        if m:
            return m.group(1)
    return None


def collect_anchors(soup: BeautifulSoup) -> tuple[set[str], set[str]]:
    """
    Собираем якоря из:
    - id="z123"
    - <a name="z123">
    Возвращаем: (all_anchors, duplicate_anchors)
    """
    anchors = []

    # id anchors
    for tag in soup.find_all(True):
        if tag.has_attr("id"):
            anchors.append(str(tag["id"]).strip())

    # <a name="z...">
    for a in soup.find_all("a"):
        if a.has_attr("name"):
            anchors.append(str(a["name"]).strip())

    seen = set()
    dups = set()
    for x in anchors:
        if x in seen:
            dups.add(x)
        else:
            seen.add(x)
    return seen, dups


def is_external(href: str) -> bool:
    return href.startswith("http://") or href.startswith("https://")


def check_external_status(url: str, timeout: int = 7) -> tuple[int | None, str | None]:
    try:
        r = requests.head(url, allow_redirects=True, timeout=timeout)
        if r.status_code in (403, 405) or r.status_code >= 500:
            r = requests.get(url, allow_redirects=True, timeout=timeout)
        return r.status_code, None
    except Exception as e:
        return None, str(e)


def iter_text_outside_links(soup: BeautifulSoup):
    """
    Берём текст, который не внутри <a>.
    Также игнорируем слишком короткое.
    """
    for text_node in soup.find_all(string=True):
        parent = text_node.parent
        if not parent:
            continue
        if parent.name == "a":
            continue
        txt = str(text_node).strip()
        if len(txt) < 10:
            continue
        yield txt


def parse_href_for_doc_and_anchor(href: str) -> tuple[str | None, str | None]:
    """
    Возвращает (target_doc_id, anchor) для ссылок вида:
    - /rus/docs/K1500000414#z299
    - http://host/rus/docs/Z2100000061#z5
    - #z235
    """
    href = href.strip()

    if href.startswith("#"):
        return None, href[1:]

    if "/rus/docs/" in href:
        # убираем scheme/host, если есть
        # и вытаскиваем doc_id + anchor
        anchor = None
        base = href
        if "#" in href:
            base, anchor = href.split("#", 1)
        m = DOC_ID_RE.search(base)
        doc_id = m.group(1) if m else None
        return doc_id, anchor

    return None, None


def audit_file(path: str, check_http: bool) -> dict:
    soup = read_html(path)
    clean_noise(soup)

    doc_id = extract_doc_id(soup)
    anchors, dup_anchors = collect_anchors(soup)

    link_rows = []
    missing_anchor_rows = []
    external_rows = []
    mentions_rows = []

    # --- Links ---
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        text = a.get_text(" ", strip=True)

        # External
        if is_external(href):
            status = None
            err = None
            if check_http:
                status, err = check_external_status(href)
            external_rows.append((path, doc_id, text, href, status, err))
            continue

        # internal /rus/docs or #anchor
        target_doc, anchor = parse_href_for_doc_and_anchor(href)

        if href.startswith("#"):
            # anchor в рамках этого же документа
            ok = (anchor in anchors) if anchor else True
            link_rows.append((path, doc_id, text, href, "same_doc_anchor", ok))
            if anchor and not ok:
                missing_anchor_rows.append((path, doc_id, text, href, anchor))
            continue

        if "/rus/docs/" in href:
            if anchor:
                # если ссылка на этот же doc_id — проверяем якорь
                if doc_id and target_doc and target_doc == doc_id:
                    ok = anchor in anchors
                    link_rows.append((path, doc_id, text, href, "self_doc_anchor", ok))
                    if not ok:
                        missing_anchor_rows.append((path, doc_id, text, href, anchor))
                else:
                    # другой документ: якорь не проверяем (нужен второй HTML или доступ к API для того doc)
                    link_rows.append((path, doc_id, text, href, "other_doc_anchor", True))
            else:
                link_rows.append((path, doc_id, text, href, "doc_link", True))
            continue

        # прочие (например относительные k150414.htm)
        link_rows.append((path, doc_id, text, href, "other", True))

    # --- Mentions (candidates) ---
    for txt in iter_text_outside_links(soup):
        for m in SUBPOINT_RE.finditer(txt):
            mentions_rows.append((path, doc_id, "subpoint_point_article", m.group(0)))
        for m in POINT_ARTICLE_RE.finditer(txt):
            mentions_rows.append((path, doc_id, "point_article", m.group(0)))
        for m in ARTICLE_MENTION_RE.finditer(txt):
            mentions_rows.append((path, doc_id, "article", m.group(0)))

    # --- Anchors summary ---
    anchor_stats = {
        "anchors_total": len(anchors),
        "duplicate_anchors_count": len(dup_anchors),
    }

    return {
        "doc_id": doc_id,
        "anchors_total": anchor_stats["anchors_total"],
        "dup_anchors": sorted(list(dup_anchors)),
        "links": link_rows,
        "missing_anchors": missing_anchor_rows,
        "externals": external_rows,
        "mentions": mentions_rows,
    }


def write_csv(path_out: str, header: list[str], rows: list[tuple]):
    os.makedirs(os.path.dirname(path_out), exist_ok=True)
    with open(path_out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="Папка с .html/.htm или один файл")
    ap.add_argument("--out", default="out_audit", help="Папка для отчётов")
    ap.add_argument("--check-http", action="store_true", help="Проверять HTTP статус внешних ссылок")
    args = ap.parse_args()

    paths = []
    if os.path.isdir(args.input):
        for root, _, files in os.walk(args.input):
            for fn in files:
                if fn.lower().endswith((".html", ".htm")):
                    paths.append(os.path.join(root, fn))
    else:
        paths = [args.input]

    all_links, all_missing, all_externals, all_mentions, dup_report = [], [], [], [], []

    for p in sorted(paths):
        res = audit_file(p, check_http=args.check_http)
        dup_report.append((p, res["doc_id"], ";".join(res["dup_anchors"]), res["anchors_total"]))

        all_links.extend(res["links"])
        all_missing.extend(res["missing_anchors"])
        all_externals.extend(res["externals"])
        all_mentions.extend(res["mentions"])

    write_csv(os.path.join(args.out, "01_links.csv"),
              ["file", "doc_id", "a_text", "href", "type", "ok"],
              all_links)

    write_csv(os.path.join(args.out, "02_missing_anchors.csv"),
              ["file", "doc_id", "a_text", "href", "missing_anchor"],
              all_missing)

    write_csv(os.path.join(args.out, "03_external_links.csv"),
              ["file", "doc_id", "a_text", "href", "http_status", "error"],
              all_externals)

    write_csv(os.path.join(args.out, "04_mentions_candidates.csv"),
              ["file", "doc_id", "pattern", "match_text"],
              all_mentions)

    write_csv(os.path.join(args.out, "05_duplicate_anchors.csv"),
              ["file", "doc_id", "duplicate_anchors", "anchors_total"],
              dup_report)

    print(f"Done. Reports in: {args.out}")


if __name__ == "__main__":
    main()