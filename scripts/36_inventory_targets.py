"""READ-ONLY: инвентаризация ВСЕХ <a href> на #z52 и #z863 в обоих файлах zemelnyy.
Нужно убедиться, что меняем ТОЛЬКО 2 нужные ссылки и не заденем чужие.
"""
import re
import sys
import importlib.util
from pathlib import Path
from bs4 import BeautifulSoup, Tag

ROOT = Path(__file__).resolve().parent.parent
FINAL = ROOT / "data" / "final"
REPORT = ROOT / "data" / "reports" / "36_inventory.txt"

_so = sys.stdout
_spec = importlib.util.spec_from_file_location(
    "audit", ROOT / "scripts" / "audit_links_coverage.py")
A = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(A)
sys.stdout = _so

OUT = []


def emit(s=""):
    OUT.append(s)


def next_text(a, n=40):
    buf = ""
    for sib in a.next_siblings:
        buf += sib.get_text(" ") if isinstance(sib, Tag) else str(sib)
        if len(buf) >= n:
            break
    return re.sub(r"\s+", " ", buf)[:n]


def host(a):
    hd = a.find_parent("div", attrs={"data-type": "статья"})
    return hd.get("data-number") if hd else "(нет div)"


def probe(fname):
    fp = FINAL / fname
    soup = BeautifulSoup(fp.read_text(encoding="utf-8"), "html.parser")
    emit("#" * 92)
    emit(f"### {fname}")
    emit("#" * 92)
    for frag in ("z52", "z863"):
        emit(f"--- href c #{frag} ---")
        cnt = 0
        for a in soup.find_all("a", href=True):
            fm = re.search(r"#(z\d+[\w-]*)$", a["href"])
            if not fm or fm.group(1) != frag:
                continue
            cnt += 1
            emit(f"  [{cnt}] host=ст.{host(a)} | href='{a['href']}' | "
                 f"текст=«{a.get_text(' ', strip=True)[:30]}» | след=«{next_text(a)}»")
        emit(f"  ВСЕГО на #{frag}: {cnt}")


def main():
    probe("zemelnyy_structured.html")
    probe("zemelnyy_ready.html")
    REPORT.write_text("\n".join(OUT) + "\n", encoding="utf-8")
    try:
        sys.stderr.write(f"report -> {REPORT}\n")
    except Exception:
        pass


if __name__ == "__main__":
    main()
