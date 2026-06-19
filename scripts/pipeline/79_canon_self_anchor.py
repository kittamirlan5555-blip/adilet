# -*- coding: utf-8 -*-
"""Свести само-ссылки «статья N» к КАНОНИЧЕСКОМУ якорю article_map (G6 -> 0).
TEXT-INVARIANT.

python scripts/pipeline/79_canon_self_anchor.py <slug ...> [--apply]

Зачем: в части доков `_ready` ссылается «статья N» на ЯКОРЬ-ОМОНИМ (adilet-схема:
у нас `zN` оказался на «Примечании», а заголовок статьи N — на синтетическом
`zNh`, который и лежит в article_map). `_structured` (канон) уже на `zNh`. Это даёт
(а) рассинхрон форм G6 и (б) РЕАЛЬНУЮ мислинку в `_ready` (ст.N ведёт на примечание).
Чиним: для каждой self-ссылки, чей видимый текст = «стать* N», если article_map[N]
существует в документе и отличается от текущего href — переводим на article_map[N].
Только одиночный номер статьи (не диапазон/перечень — там свой стиль). Обе формы;
канон обычно уже верен (no-op), чинится в основном `_ready`.

Гейт: nows(get_text) ДО==ПОСЛЕ; не создаём dangling (target обязан резолвиться).
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import paths  # noqa: E402
from bs4 import BeautifulSoup  # noqa: E402

RE_SELF = re.compile(r"^#(z[\w-]+)$")
# видимый текст ссылки = ровно одна «стать* N» (без второго номера/диапазона)
RE_ART_ONLY = re.compile(r"^\s*стат[ьяиею]\w*\s+(\d+(?:-\d+)?)\s*$", re.I)


def _nows(soup):
    return "".join(soup.get_text().split())


def process(slug, apply_mode):
    amp = paths.MAPS / f"article_map_{slug}.json"
    if not amp.exists():
        print(f"  {slug}: нет article_map"); return 0
    am = json.loads(amp.read_text(encoding="utf-8"))
    total = 0
    for form in ("structured", "ready"):
        p = paths.FINAL / f"{slug}_{form}.html"
        if not p.exists():
            continue
        soup = BeautifulSoup(p.read_text(encoding="utf-8"), "html.parser")
        ids = {t.get("id") for t in soup.find_all(attrs={"id": True})}
        ids |= {t.get("name") for t in soup.find_all("a", attrs={"name": True})}
        before = _nows(soup)
        fixed = 0
        for a in soup.find_all("a", href=True):
            m = RE_SELF.match(a["href"].strip())
            if not m:
                continue
            cur = m.group(1)
            mt = RE_ART_ONLY.match(a.get_text(" ", strip=True))
            if not mt:
                continue
            canon = am.get(mt.group(1))
            if canon and canon != cur and canon in ids:
                a["href"] = f"#{canon}"
                fixed += 1
        if fixed:
            after = _nows(BeautifulSoup(str(soup), "html.parser"))
            if before != after:
                sys.exit(f"STOP: nows-сдвиг в {p.name} — отказ записи")
            print(f"  {slug}_{form}: -> канон article_map: {fixed}")
            if apply_mode:
                p.write_text(str(soup), encoding="utf-8")
            total += fixed
    return total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("slugs", nargs="+")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    g = sum(process(s, a.apply) for s in a.slugs)
    print(f"ИТОГО -> канон: {g}  ({'ПРИМЕНЕНО' if a.apply else 'dry-run'})")


if __name__ == "__main__":
    main()
