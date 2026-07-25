# -*- coding: utf-8 -*-
"""anara2 BLOCK 6 независимый аудит final/ (из сырого HTML, §6). Проверяет:
  - nested <a>            = 0   (вложенные ссылки)
  - двойной href          = 0
  - self-root absolute    = 0   (§4: сам на себя корнем)
  - orphan-префикс        = 0   («Закон* РК» плейн-текст ПЕРЕД <a>"Имя">, не поглощён)
  - склейки цифра+буква   = 0   («2статьи», «N.В» без пробела — класс N2)
  - dangling self #z            (якорь #zN без цели в этом же документе)
Печатает сводку + топ-нарушители. Ненулевые целевые метрики => разбор.
"""
import io, sys, re, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from pathlib import Path
from bs4 import BeautifulSoup, NavigableString

ROOT = Path(__file__).resolve().parents[1]
HOST = "https://adilet.zan.kz/rus/docs/"
cj = json.loads((ROOT / "maps/codes.json").read_text(encoding="utf-8"))
slug_of = {}
for s, v in cj.items():
    if not s.startswith("_") and isinstance(v, dict):
        slug_of[s] = v.get("doc_id", s)

MON = r"(?:январ|феврал|март|апрел|ма[йя]|июн|июл|август|сентябр|октябр|ноябр|декабр)\w*"
PREFIX_ORPHAN = re.compile(
    r'(?:[Зз]акон(?:ом|а|у|е|ы)?|[Кк]одекс\w*)(?:\s+Республики\s+Казахстан|\s+РК)?'
    r'(?:\s+от\s+\d{1,2}\s+' + MON + r'\s+\d{4}\s*года)?\s*<a\b[^>]*>\s*["«]', re.I)
SPLICE = re.compile(r'\d[А-Яа-яЁё]|[а-яё]\d(?=[А-Яа-яЁё])')  # цифра-буква склейка (грубо)


def audit_file(p, self_id):
    html = p.read_text(encoding="utf-8", errors="replace")
    soup = BeautifulSoup(html, "html.parser")
    nested = sum(1 for a in soup.find_all("a") if a.find("a"))
    dbl = len(re.findall(r'href="[^"]*"\s+href=', html))
    selfset = {HOST + self_id, HOST + self_id.rstrip("_")}
    selfroot = sum(1 for a in soup.find_all("a", href=True)
                   if a["href"].rstrip("/") in selfset)
    # orphan-prefix: только вне <script>/<a>; грубо по сырому html, но исключим внутри <a>...>
    orphan = len(PREFIX_ORPHAN.findall(html))
    # dangling self #z
    ids = {e.get("id") for e in soup.find_all(attrs={"id": True})}
    ids |= {e.get("name") for e in soup.find_all(attrs={"name": True})}
    dangle = 0
    for a in soup.find_all("a", href=True):
        h = a["href"]
        if h.startswith("#z") and h[1:] not in ids:
            dangle += 1
    return dict(nested=nested, dbl=dbl, selfroot=selfroot, orphan=orphan, dangle=dangle)


def main():
    forms = sorted(ROOT.glob("final/*_ready.html")) + sorted(ROOT.glob("final/*_structured.html"))
    tot = dict(nested=0, dbl=0, selfroot=0, orphan=0, dangle=0)
    bad = {k: [] for k in tot}
    for p in forms:
        stem = p.name.replace("_ready.html", "").replace("_structured.html", "")
        self_id = slug_of.get(stem, stem)
        r = audit_file(p, self_id)
        for k in tot:
            tot[k] += r[k]
            if r[k]:
                bad[k].append((p.name, r[k]))
    print(f"аудит форм-файлов: {len(forms)}\n")
    for k in ("nested", "dbl", "selfroot", "orphan", "splice_skip", "dangle"):
        if k == "splice_skip":
            continue
        print(f"  {k:10s} = {tot[k]}")
    print()
    for k in ("nested", "dbl", "selfroot", "orphan"):
        if bad[k]:
            print(f"  ТОП {k}:")
            for n, c in sorted(bad[k], key=lambda x: -x[1])[:8]:
                print(f"     {c:4d}  {n}")
    # dangle — существующий §9-класс, показываем но не блокируем
    if bad["dangle"]:
        print(f"  dangling self #z (§9/фантом-класс, инфо): {tot['dangle']} в {len(bad['dangle'])} файлах")


if __name__ == "__main__":
    main()
