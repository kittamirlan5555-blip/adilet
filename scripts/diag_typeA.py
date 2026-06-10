"""READ-ONLY диагностика TYPE A (внешние ссылки без <a>) для Земельного.
Считает, сколько раз каждая фраза встречается ВНЕ <a> и ВНУТРИ <a>.
Ничего не меняет."""
import sys
import io
import re
from pathlib import Path
from bs4 import BeautifulSoup

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
OUR = ROOT / "data" / "final" / "zemelnyy_structured.html"
SRC = ROOT / "data" / "source" / "zemelnyy.html"

PHRASES = [
    "Экологическим кодексом",
    "Административным процедурно-процессуальным кодексом",
    "об административных правонарушениях",
    "О недрах и недропользовании",
    "О статусе столицы Республики Казахстан",
    "Предпринимательского кодекса",
]


def analyze(path, label):
    soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
    full_text = soup.get_text(" ")
    print("=" * 80)
    print(f"{label}: {path.name}")
    print("=" * 80)
    for ph in PHRASES:
        total = len(re.findall(re.escape(ph), full_text))
        # сколько раз внутри <a>
        in_a = 0
        for a in soup.find_all("a"):
            in_a += len(re.findall(re.escape(ph), a.get_text(" ")))
        outside = total - in_a
        print(f"  «{ph}»")
        print(f"      всего={total}  внутри <a>={in_a}  ВНЕ <a>={outside}")
    print()


if __name__ == "__main__":
    analyze(OUR, "НАШ HTML (final)")
    if SRC.exists():
        analyze(SRC, "ADILET ОРИГИНАЛ (source)")
    else:
        print("source/zemelnyy.html не найден")
