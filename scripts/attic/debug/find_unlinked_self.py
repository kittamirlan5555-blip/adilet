"""Сканирует ready-файл на UN-linked самоссылки ('настоящ…')."""
import re
import sys
from bs4 import BeautifulSoup

path = sys.argv[1] if len(sys.argv) > 1 else "data/final/socialnyy_ready.html"
with open(path, encoding="utf-8") as f:
    soup = BeautifulSoup(f.read(), "html.parser")

for tag in soup.find_all(["script", "style"]):
    tag.decompose()


def is_linked(node):
    p = node.parent
    while p:
        if getattr(p, "name", None) == "a":
            return True
        if getattr(p, "name", None) in ("body", "article"):
            break
        p = p.parent
    return False


def is_snoska_or_heading(node):
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


# Ищем "(под)пункт(...) N) [+M)]... + опционально 'части/частью X' + настоящ..."
SELF_REF_RE = re.compile(
    r"(?:подпункт|пункт|стать|глав|част)\w*\s+\d+(?:-\d+)?[)]?"
    r"(?:[^.\n]{0,200}?)?"
    r"настоящ(?:его|ей|им|ему|ем|их)\s+(?:пункта|части|статьи|Кодекса|раздела|главы|параграфа)",
    re.IGNORECASE,
)

count = 0
unique = {}
for tn in soup.find_all(string=True):
    if is_linked(tn) or is_snoska_or_heading(tn):
        continue
    txt = str(tn)
    for m in SELF_REF_RE.finditer(txt):
        match = m.group(0)
        ctx_start = max(0, m.start() - 30)
        ctx_end = min(len(txt), m.end() + 30)
        ctx = txt[ctx_start:ctx_end].replace("\n", " ").strip()
        # Пропускаем если контекст содержит "Сноска"
        if "Сноска" in ctx:
            continue
        unique.setdefault(match[:80], []).append(ctx)
        count += 1

print(f"Найдено {count} unlinked self-ссылок ({len(unique)} уникальных шаблонов)\n")
for match, ctxs in sorted(unique.items(), key=lambda x: -len(x[1]))[:25]:
    print(f"[{len(ctxs)}x] {match!r}")
    print(f"      пример: {ctxs[0][:140]}")
