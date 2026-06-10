# -*- coding: utf-8 -*-
"""TYPE C recon (ANARA): для каждой помеченной статьи predprinimatel показать
её текст с пометкой существующих <a> (⟦text⟧→href), чтобы увидеть, что уже
залинковано и что надо линковать. READ-ONLY.
"""
import sys
from pathlib import Path
from bs4 import BeautifulSoup, NavigableString, Tag

ROOT = Path(__file__).resolve().parents[1]
FINAL = ROOT / "data" / "final"

FLAGS = ["79-3","82","107","120","129","134","144","155","169","192","193",
         "194","196","204","217","218","224","231","232","232-1","324"]

def render(el):
    """текст элемента; ссылки помечаем ⟦txt⟧→href."""
    out = []
    for d in el.descendants:
        if isinstance(d, NavigableString):
            # пропустить, если внутри <a> (обработаем на уровне <a>)
            if d.find_parent("a"):
                continue
            out.append(str(d))
        elif isinstance(d, Tag) and d.name == "a":
            out.append(f"⟦{d.get_text()}⟧→{d.get('href')}")
    return "".join(out)

def find_article(soup, num):
    for div in soup.find_all("div", attrs={"data-type": "статья"}):
        if div.get("data-number") == num:
            return div
    return None

def main():
    soup = BeautifulSoup((FINAL/"predprinimatel_structured.html").read_text(encoding="utf-8"), "html.parser")
    L = ["TYPE C RECON — predprinimatel помеченные статьи (⟦…⟧→href = уже ссылка)",
         "=" * 90]
    for num in FLAGS:
        div = find_article(soup, num)
        L.append("")
        L.append(f"================= ст.{num} =================")
        if div is None:
            L.append("  !! статья не найдена по data-number")
            continue
        txt = render(div)
        # ужать множественные пробелы/переводы
        import re
        txt = re.sub(r"[ \t]*\n[ \t\n]*", "\n", txt)
        txt = re.sub(r"[ \t]{2,}", " ", txt)
        L.append(txt.strip()[:2600])
    out = "\n".join(L) + "\n"
    (ROOT/"data/reports/48_typeC_recon.txt").write_text(out, encoding="utf-8")
    sys.stdout.write(f"written {len(out)} chars\n")

if __name__ == "__main__":
    main()
