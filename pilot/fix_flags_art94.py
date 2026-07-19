# -*- coding: utf-8 -*-
"""Флаги Анары по «О рынке ценных бумаг» (Z030000461_): «стать* 9-4» — это ссылка
на статью 9-4 ВНЕШНЕГО «О государственном регулировании … финансового рынка»
(Z030000474_), которого статьи 9-4 нет в нашей выгрузке цели → по §4 и указанию
владельца «minimum root link»: полный спан «стать* 9-4 Закона РК "О госрегулировании…"»
→ КОРЕНЬ Z030000474_.

Имя акта уже залинковано на корень Z030000474_; «стать* 9-4 » стоит СЛЕВА вне спана.
Фикс = сдвинуть ЛЕВУЮ границу <a> влево, поглотив «стать* 9-4 » (текст не меняется —
двигаем только границу; идемпотентно: после сдвига «стать* 9-4 » идёт не перед <a>).
"""
import io
import re
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
F = ROOT / "final" / "Z030000461__ready.html"
# «стать*(и|ей) 9-4 » затем открывающий <a …Z030000474_…>
RE = re.compile(r'(стать(?:и|ей|ью|е|я)\s+9-4\s+)(<a\s+href="[^"]*Z030000474_[^"]*">)')


def nows(html):
    s = BeautifulSoup(html, "html.parser")
    for t in s.find_all(["script", "style"]):
        t.decompose()
    return "".join(s.get_text().split())


def main():
    html = F.read_text(encoding="utf-8", errors="replace")
    before_vis = nows(html)
    new, n = RE.subn(r"\2\1", html)
    after_vis = nows(new)
    print(f"перенесено границ <a> (стать* 9-4 -> внутрь Z030000474_-спана): {n}")
    print(f"text-invariance (без пробелов): {'OK' if before_vis == after_vis else 'НАРУШЕНО!'}")
    if before_vis != after_vis:
        sys.exit("СТОП: изменился видимый текст — не пишу")
    if "--apply" in sys.argv and n:
        F.write_text(new, encoding="utf-8")
        print(f"записано -> {F.relative_to(ROOT)}")
    elif not n:
        print("нечего менять (уже применено?)")
    else:
        print("(dry-run; --apply чтобы записать)")


if __name__ == "__main__":
    main()
