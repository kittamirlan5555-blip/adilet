"""READ-ONLY TYPE A — точные фразы шефа + контекст для «об адм. правонарушениях».
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

# Точные фразы Анары (TYPE A)
PHRASES = [
    "Экологическим кодексом",
    "Административным процедурно-процессуальным кодексом",
    "Кодексом Республики Казахстан об административных правонарушениях",
    "об административных правонарушениях",
    "о недрах и недропользовании",
    "О статусе столицы Республики Казахстан",
    "Предпринимательского кодекса",
]


def linked_status(soup, ph):
    full_text = soup.get_text(" ")
    total = len(re.findall(re.escape(ph), full_text))
    in_a = 0
    for a in soup.find_all("a"):
        in_a += len(re.findall(re.escape(ph), a.get_text(" ")))
    return total, in_a, total - in_a


def show_context(soup, ph, n=12):
    """Печатает до n упоминаний фразы с пометкой [LINKED]/[PLAIN]."""
    print(f"  --- контекст «{ph}» ---")
    cnt = 0
    for el in soup.find_all(string=re.compile(re.escape(ph))):
        parent_a = el.find_parent("a")
        tag = "[LINKED]" if parent_a else "[PLAIN] "
        ctx = re.sub(r"\s+", " ", str(el)).strip()
        idx = ctx.find(ph)
        s = max(0, idx - 40)
        e = min(len(ctx), idx + len(ph) + 25)
        print(f"      {tag} …{ctx[s:e]}…")
        cnt += 1
        if cnt >= n:
            break


def analyze(path, label, ctx_phrase=None):
    soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
    print("=" * 84)
    print(f"{label}: {path.name}")
    print("=" * 84)
    for ph in PHRASES:
        total, in_a, outside = linked_status(soup, ph)
        print(f"  «{ph[:55]}»  всего={total} <a>={in_a} ВНЕ={outside}")
    if ctx_phrase:
        print()
        show_context(soup, ctx_phrase)
    print()


if __name__ == "__main__":
    analyze(OUR, "НАШ HTML (final)", ctx_phrase="об административных правонарушениях")
    if SRC.exists():
        analyze(SRC, "ADILET ОРИГИНАЛ (source)")
