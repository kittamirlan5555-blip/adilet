# -*- coding: utf-8 -*-
"""Хвост-шаг: разворачивает ВИСЯЧИЕ self-ссылки <a href="#zN"> (цель отсутствует
в документе) в обычный текст. TEXT-INVARIANT (видимый текст байт-в-байт сохранён).

python scripts/pipeline/77_unwrap_dangling.py <slug> [--apply]

Зачем: adilet иногда ссылается на mid-paragraph анкоры, которые 13_cleanup
(расщепление вложенных <a>) удаляет как пустые — ссылка остаётся, цель пропадает.
Чинить 13_cleanup рискованно (регресс 25 готовых док), поэтому битую self-ссылку
разворачиваем здесь: лучше plain-текст, чем ссылка в никуда (CLAUDE.md §6).
Голые href="#" (РУС/ҚАЗ-переключатель adilet) НЕ трогаем — это хром, не право.

Без --apply: только отчёт. Гейт: nows(get_text) ДО==ПОСЛЕ, иначе НЕ пишем.
"""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import paths  # noqa: E402
from bs4 import BeautifulSoup  # noqa: E402

RE_ZTARGET = re.compile(r"^#(z\d+\w*)$")   # #z123 / #z123h / #z12_3 — но не голый "#"


def _ids(soup):
    s = set()
    for t in soup.find_all(attrs={"id": True}):
        s.add(t["id"])
    for t in soup.find_all("a", attrs={"name": True}):
        s.add(t["name"])
    return s


def _nows(soup):
    return "".join(soup.get_text().split())


def unwrap_dangling(html: str):
    soup = BeautifulSoup(html, "html.parser")
    ids = _ids(soup)
    before = _nows(soup)
    victims = []
    for a in soup.find_all("a", href=True):
        m = RE_ZTARGET.match(a["href"].strip())
        if m and m.group(1) not in ids:
            victims.append((a["href"], a.get_text(" ", strip=True)[:40]))
            a.unwrap()                      # снять обёртку, оставить детей/текст
    out = str(soup)
    after = _nows(BeautifulSoup(out, "html.parser"))
    return out, victims, before == after


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("slug")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    total = 0
    for form in ("structured", "ready"):
        p = paths.FINAL / f"{a.slug}_{form}.html"
        if not p.exists():
            continue
        out, victims, inv = unwrap_dangling(p.read_text(encoding="utf-8"))
        total += len(victims)
        tag = "" if inv else "  [!! NOWS-СДВИГ — НЕ ПИШУ]"
        print(f"  {a.slug}_{form}: висячих={len(victims)} invariant={inv}{tag}")
        for href, txt in victims[:20]:
            print(f"      {href}  <- {txt!r}")
        if a.apply and victims:
            if not inv:
                sys.exit(f"STOP: nows-сдвиг в {p.name} — отказ записи")
            p.write_text(out, encoding="utf-8")
    print(f"{a.slug}: всего висячих self-ссылок {'РАЗВЁРНУТО' if a.apply else 'найдено'}: {total}")


if __name__ == "__main__":
    main()
