# -*- coding: utf-8 -*-
"""Verify hyperlink fixes requested in the reviewer DOCX.

The script reads the DOCX itself to locate reviewed paragraphs, so the checks
do not depend on Cyrillic string literals in this source file.
"""
from __future__ import annotations

import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from lxml import html


ROOT = Path(__file__).resolve().parent.parent
DOCX_DIR = Path.home() / "Downloads"
HTML_FILES = [
    ROOT / "data" / "final" / "koap_structured.html",
    ROOT / "data" / "final" / "koap_ready.html",
]

KOAP = "https://adilet.zan.kz/rus/docs/K1400000235"

EXPECTED_HREFS = {
    1: [f"{KOAP}#z59h"],
    2: [f"{KOAP}#z242"],
    3: [f"{KOAP}#z242"],
    4: [f"{KOAP}#z242"],
    5: [f"{KOAP}#z242"],
    6: [f"{KOAP}#z242"],
    7: [f"{KOAP}#z242"],
    8: ["https://adilet.zan.kz/rus/docs/K940001000_"],
    9: [
        "https://adilet.zan.kz/rus/docs/K2500000214",
        "https://adilet.zan.kz/rus/docs/K1700000123#z574",
    ],
    10: ["https://adilet.zan.kz/rus/docs/Z1400000176"],
    11: ["https://adilet.zan.kz/rus/docs/Z1400000176"],
    12: ["https://adilet.zan.kz/rus/docs/Z1200000056"],
    13: ["https://adilet.zan.kz/rus/docs/K2500000214"],
    14: ["https://adilet.zan.kz/rus/docs/K2500000214"],
    15: ["https://adilet.zan.kz/rus/docs/K1700000125"],
    16: ["https://adilet.zan.kz/rus/docs/K1700000125"],
    17: ["https://adilet.zan.kz/rus/docs/K1700000125"],
    18: ["https://adilet.zan.kz/rus/docs/Z010000143_"],
    19: ["https://adilet.zan.kz/rus/docs/Z100000257_#z8"],
    20: ["https://adilet.zan.kz/rus/docs/K1700000123"],
    21: ["https://adilet.zan.kz/rus/docs/K2000000350"],
    22: [f"{KOAP}#z1742", f"{KOAP}#z2131", f"{KOAP}#z641h"],
    23: [f"{KOAP}#z3405", f"{KOAP}#z1552"],
    24: [
        "https://adilet.zan.kz/rus/docs/Z040000588_#z1096",
        "https://adilet.zan.kz/rus/docs/Z040000588_#z1136",
        "https://adilet.zan.kz/rus/docs/Z040000588_#z1241",
        "https://adilet.zan.kz/rus/docs/Z040000588_",
        "https://adilet.zan.kz/rus/docs/Z2400000120#z197",
        "https://adilet.zan.kz/rus/docs/Z2400000120#z237",
        "https://adilet.zan.kz/rus/docs/Z2400000120#z342",
        "https://adilet.zan.kz/rus/docs/Z2400000120",
    ],
    26: [f"{KOAP}#z1572", f"{KOAP}#z1580"],
    27: [f"{KOAP}#z1580"],
    28: [f"{KOAP}#z2192"],
    29: [f"{KOAP}#z4814"],
    30: [f"{KOAP}#z4587"],
    31: [f"{KOAP}#z1572"],
    32: [f"{KOAP}#z4536"],
    33: [f"{KOAP}#z242", f"{KOAP}#z80"],
    34: [f"{KOAP}#z242", f"{KOAP}#z80"],
    35: ["https://adilet.zan.kz/rus/docs/Z950002529_"],
    36: ["https://adilet.zan.kz/rus/docs/K950001000_#z278"],
    37: [f"{KOAP}#z8h"],
    38: ["https://adilet.zan.kz/rus/docs/K940001000_"],
    39: [f"{KOAP}#z1501", f"{KOAP}#z1504"],
}


def norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def extract_article(text: str, current_article: str | None) -> str | None:
    prefix = text.split(" - ", 1)[0].split("–", 1)[0]
    if "статья" not in prefix:
        return current_article
    nums = re.findall(r"\d+(?:-\d+)?", prefix)
    return nums[-1] if nums else current_article


def reviewer_items() -> list[tuple[int, str | None, str]]:
    docx_files = [p for p in DOCX_DIR.glob("*.docx") if "(6)" in p.name]
    if not docx_files:
        raise FileNotFoundError("Reviewer DOCX with '(6)' in the name was not found")
    path = docx_files[0]

    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    w = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    with zipfile.ZipFile(path) as zf:
        root = ET.fromstring(zf.read("word/document.xml"))

    items: list[tuple[int, str | None, str]] = []
    current_article: str | None = None
    for p in root.iter(w + "p"):
        chunks: list[str] = []
        has_red = False
        has_yellow = False
        for r in p.findall(".//w:r", ns):
            txt = "".join(t.text or "" for t in r.findall(".//w:t", ns))
            if not txt:
                continue
            chunks.append(txt)
            rpr = r.find("w:rPr", ns)
            if rpr is None:
                continue
            color = rpr.find("w:color", ns)
            if color is not None and (color.get(w + "val") or "").lower() in {
                "ff0000",
                "red",
                "c00000",
                "e60000",
            }:
                has_red = True
            highlight = rpr.find("w:highlight", ns)
            if highlight is not None and (highlight.get(w + "val") or "").lower() == "yellow":
                has_yellow = True
        text = norm("".join(chunks))
        if text and (has_red or has_yellow):
            current_article = extract_article(text, current_article)
            items.append((len(items) + 1, current_article, text))
    return items


def probe_text(item_text: str) -> str:
    if " - " in item_text:
        item_text = item_text.split(" - ", 1)[1]
    if "–" in item_text and item_text.strip().endswith("–"):
        return ""
    return norm(item_text)[:90]


def article_paragraphs(doc: html.HtmlElement, article: str | None) -> list[html.HtmlElement]:
    all_paragraphs = doc.xpath("//p")
    if not article:
        return all_paragraphs

    structured = doc.xpath(f'//div[@class="article" and @data-number="{article}"]//p')
    if structured:
        return structured

    heading_index: int | None = None
    heading_prefix = f"Статья {article}."
    for idx, p in enumerate(all_paragraphs):
        if norm(p.text_content()).startswith(heading_prefix):
            heading_index = idx
            break
    if heading_index is None:
        return all_paragraphs

    scoped: list[html.HtmlElement] = []
    for p in all_paragraphs[heading_index + 1 :]:
        if re.match(r"Статья \d+(?:-\d+)?\.", norm(p.text_content())):
            break
        scoped.append(p)
    return scoped or all_paragraphs


def locate_paragraph(
    doc: html.HtmlElement,
    article: str | None,
    probe: str,
    expected_hrefs: list[str],
) -> html.HtmlElement | None:
    if not probe:
        return None
    matches = []
    for p in article_paragraphs(doc, article):
        if probe in norm(p.text_content()):
            matches.append(p)
    if not matches and article:
        for p in article_paragraphs(doc, None):
            if probe in norm(p.text_content()):
                matches.append(p)
    if not matches:
        return None
    for p in matches:
        hrefs = hrefs_in_paragraph(p)
        if all(expected in hrefs for expected in expected_hrefs):
            return p
    for p in matches:
        if hrefs_in_paragraph(p):
            return p
    return matches[0]


def hrefs_in_paragraph(p: html.HtmlElement) -> list[str]:
    return [a.get("href", "") for a in p.xpath(".//a")]


def verify_file(path: Path, items: list[tuple[int, str | None, str]]) -> list[str]:
    doc = html.fromstring(path.read_text(encoding="utf-8"))
    failures: list[str] = []
    for item_no, article, item_text in items:
        if item_no not in EXPECTED_HREFS:
            continue
        p = locate_paragraph(doc, article, probe_text(item_text), EXPECTED_HREFS[item_no])
        if p is None:
            failures.append(f"item {item_no}: paragraph not found")
            continue
        hrefs = hrefs_in_paragraph(p)
        for expected in EXPECTED_HREFS[item_no]:
            if expected not in hrefs:
                failures.append(f"item {item_no}: missing {expected}")
    return failures


def main() -> None:
    items = reviewer_items()
    print(f"reviewer_items={len(items)} expected_checks={len(EXPECTED_HREFS)}")
    all_failures: list[str] = []
    for path in HTML_FILES:
        failures = verify_file(path, items)
        if failures:
            print(f"{path.relative_to(ROOT)}: FAIL")
            for failure in failures:
                print(f"  {failure}")
            all_failures.extend(f"{path.name}: {f}" for f in failures)
        else:
            print(f"{path.relative_to(ROOT)}: OK")
    if all_failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
