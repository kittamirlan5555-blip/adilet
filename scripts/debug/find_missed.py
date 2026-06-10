"""Сканирует ready-файл и ищет фразы, которые ОЖИДАЕМО должны быть ссылкой,
но не обёрнуты в <a>."""

import re
import sys
from bs4 import BeautifulSoup

if len(sys.argv) < 2:
    print("Usage: find_missed.py data/final/X_ready.html")
    sys.exit(1)

path = sys.argv[1]
with open(path, encoding="utf-8") as f:
    soup = BeautifulSoup(f.read(), "html.parser")

# Удаляем сноски и заголовки
for tag in soup.find_all(["script", "style", "template"]):
    tag.decompose()

PATTERNS = [
    ("article ref", re.compile(r"\bстать[ьеяию][яиеёюийми]*\s+\d+(?:-\d+)?\b", re.IGNORECASE)),
    ("punkt ref", re.compile(r"\bпункт(?:ом|а|е|у|ами|ах|ы|ов)?\s+\d+(?:-\d+)?\b(?!\))", re.IGNORECASE)),
    ("subpoint ref", re.compile(r"\bподпункт(?:ом|а|е|у|ами|ах|ы|ов)?\s+\d+(?:-\d+)?\)", re.IGNORECASE)),
    ("glava ref", re.compile(r"\bглав(?:ой|е|ы|у|а|ами|ах)\s+\d+\b", re.IGNORECASE)),
    ("cross-code (kodex)", re.compile(r"\bстать[\w]+\s+\d+(?:-\d+)?\s+(?:Налогов|Гражданск|Уголовн|Трудов|Эколог|Земельн|Бюджетн|Предприним|Социальн|Лесн|Водн|Семейн)", re.IGNORECASE)),
    ("law form", re.compile(r'Закон[\w]*\s+Республики\s+Казахстан\s+["«][^"»]+["»]', re.IGNORECASE)),
]

# Игнорируем сноски и заголовки статей
def is_skipped(node):
    p = node.parent
    while p:
        if getattr(p, "name", None) == "span" and "note" in (p.get("class") or []):
            return True
        if getattr(p, "name", None) == "font":
            color = (p.get("color") or "").upper().lstrip("#")
            if color == "FF0000":
                return True
        if getattr(p, "name", None) in ("h1", "h2", "h3", "h4"):
            return True
        if getattr(p, "name", None) == "b":
            if hasattr(p, "find") and p.find("a", attrs={"name": True}):
                return True
        if getattr(p, "name", None) in ("body", "article"):
            break
        p = p.parent
    return False


def is_linked(node):
    p = node.parent
    while p:
        if getattr(p, "name", None) == "a":
            return True
        if getattr(p, "name", None) in ("body", "article"):
            break
        p = p.parent
    return False


found = {k: [] for k, _ in PATTERNS}
for tn in soup.find_all(string=True):
    if is_linked(tn) or is_skipped(tn):
        continue
    txt = str(tn)
    if len(txt.strip()) < 5:
        continue
    for name, pat in PATTERNS:
        for m in pat.finditer(txt):
            ctx = txt[max(0, m.start()-25):m.end()+25].replace("\n", " ").strip()
            found[name].append((m.group(0), ctx))

print(f"=== Скан {path} ===\n")
for name, hits in found.items():
    print(f"{name}: {len(hits)}")
    # Уникальные фрагменты
    uniq = {}
    for match, ctx in hits:
        uniq.setdefault(match, []).append(ctx)
    for match, ctxs in list(uniq.items())[:10]:
        print(f"  '{match}' ({len(ctxs)}× ): {ctxs[0][:100]}...")
    print()
