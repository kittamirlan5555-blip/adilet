"""READ-ONLY диагностика TYPE B (пропавший номер статьи). Ничего не меняет."""
import sys
import io
import re
from pathlib import Path
from bs4 import BeautifulSoup

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
FINAL = ROOT / "data" / "final"

CODES = ["nalog", "trudovoy", "grazhdanskiy", "predprinimatel", "socialnyy",
         "ekologicheskiy", "zemelnyy", "upk", "koap", "appk", "byudzhet", "ugolovniy"]

# Точный регекс шефа: статья-слово + 2+ пробела + и/,/настоящ = ДЫРА (номер пропал)
GAP = re.compile(r"(стать[яиею]|статьями)\s{2,}(и\b|,|или\b|настоящ)", re.I)


def per_p_text(soup):
    """Возвращает список (p_id, text) — текст параграфа с СОХРАНЁННЫМИ пробелами,
    только ведущие/хвостовые срезаны (чтобы форматные \\n не мешали)."""
    out = []
    for p in soup.find_all("p"):
        t = p.get_text()  # без separator — склейка текст-нод как есть
        t = t.strip()
        out.append((p.get("id"), t, p))
    return out


def scan(code, show=False):
    path = FINAL / f"{code}_structured.html"
    soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
    hits = []
    for pid, t, p in per_p_text(soup):
        for m in GAP.finditer(t):
            s = max(0, m.start() - 30)
            e = min(len(t), m.end() + 30)
            ctx = re.sub(r"\n", "\\\\n", t[s:e])
            hits.append((pid, ctx, p))
    if show:
        print(f"\n--- {code}: {len(hits)} matches (показываю до 25) ---")
        for pid, ctx, p in hits[:25]:
            print(f"  p#{pid}: …{ctx}…")
    return hits


if __name__ == "__main__":
    print("=" * 80)
    print("TYPE B SCALE — точный регекс шефа по 12 *_structured.html")
    print(r"regex: (стать[яиею]|статьями)\s{2,}(и\b|,|или\b|настоящ)")
    print("=" * 80)
    print(f"{'код':16} {'дыр':>6}")
    print("-" * 24)
    total = 0
    detail = {}
    for code in CODES:
        h = scan(code)
        detail[code] = h
        total += len(h)
        print(f"{code:16} {len(h):>6}")
    print("-" * 24)
    print(f"{'TOTAL':16} {total:>6}")

    print()
    print("=" * 80)
    print("ZEMELNYY — все совпадения (raw context)")
    print("=" * 80)
    for pid, ctx, p in detail["zemelnyy"]:
        print(f"  p#{pid}: …{ctx}…")
