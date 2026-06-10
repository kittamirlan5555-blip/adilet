"""READ-ONLY: сырые фрагменты ст.38 и ст.100 Земельного — наш HTML vs adilet оригинал.
Печатает RAW innerHTML релевантных <p>. Ничего не меняет."""
import sys
import io
import re
from pathlib import Path
from bs4 import BeautifulSoup

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
OUR = ROOT / "data" / "final" / "zemelnyy_structured.html"
SRC = ROOT / "data" / "source" / "zemelnyy.html"


def dump_our(art_num, needles):
    soup = BeautifulSoup(OUR.read_text(encoding="utf-8"), "html.parser")
    div = soup.find("div", attrs={"data-type": "статья", "data-number": art_num})
    print("=" * 84)
    print(f"НАШ HTML — статья {art_num}  (div id={div.get('id') if div else '??'})")
    print("=" * 84)
    if not div:
        print("  статья не найдена"); return
    for p in div.find_all("p"):
        raw = re.sub(r"\s+", " ", p.decode_contents()).strip()
        if any(n in raw for n in needles):
            print(f"  p#{p.get('id')}:")
            print(f"    {raw}")
    print()


def dump_src(needles, win=260):
    txt = SRC.read_text(encoding="utf-8")
    soup = BeautifulSoup(txt, "html.parser")
    print("=" * 84)
    print("ADILET ОРИГИНАЛ — поиск тех же фрагментов (raw <p>)")
    print("=" * 84)
    for p in soup.find_all("p"):
        raw = re.sub(r"\s+", " ", p.decode_contents()).strip()
        if any(n in raw for n in needles):
            print(f"    {raw[:600]}")
            print()


if __name__ == "__main__":
    print("\n########## ст.38 (Анара: п.4/5) ##########")
    dump_our("38", ["настоящего Кодекса", "статьей", "статьи "])
    dump_src(["64", "65"], )

    print("\n########## ст.100 (Анара: п.2/4/6) ##########")
    dump_our("100", ["настоящего Кодекса", "статьями", "статье ", "статьей"])
    dump_src(["92, 93 и 95"])
