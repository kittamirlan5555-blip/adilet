# -*- coding: utf-8 -*-
"""zhilishniy: репойнт УНАСЛЕДОВАННЫХ-БИТЫХ само-ссылок (как ocorrupt #z59/#z70).

adilet в исходнике ставит ссылки `#zNNN` на якоря, которых НЕТ ни у adilet, ни
у нас (мёртвые само-ссылки). 68 авто-чинит только СИНГУЛЯР «статья N»; остаются
плюраль-головы списков, «голые» номера-продолжения и ссылки «пункт N статьи M».
Каждой определена цель по контексту (article_map / subpoint_map), цели проверены
на существование. Меняем ТОЛЬКО href, get_text не трогаем (гейт). READ→правка
data/final (исходник data/source неприкосновенен).
"""
import re
import hashlib
from pathlib import Path
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
FP = ROOT / "data" / "final" / "zhilishniy_structured.html"

# мёртвый_фрагмент -> (целевой_якорь, пояснение)
REPOINT = {
    "z52":   ("z1951", "статьями 43 -> ст.43"),
    "z53":   ("z1961", "44 -> ст.44"),
    "z72":   ("z1801", "61 -> ст.61"),
    "z100":  ("z1806", "статьях 85 -> ст.85"),
    "z101":  ("z1807", "86 -> ст.86"),
    "z105":  ("z1428", "статей 90 / 90 -> ст.90"),
    "z108":  ("z1813", "93 -> ст.93"),
    "z110":  ("z1430", "95 -> ст.95"),
    "z115":  ("z1431", "статьями 98 -> ст.98"),
    "z118":  ("z1818", "101 -> ст.101"),
    "z738":  ("z2121", "пунктом 4 статьи 101-1 -> п4 ст101-1"),
    "z1581": ("z2121", "пунктом 4 статьи 101-1 -> п4 ст101-1"),
    "z808":  ("z502",  "пунктами 2 статьи 101 -> п2 ст101"),
    "z591":  ("z1469", "пункте 4 статьи 67 -> п4 ст67"),
    "z1589": ("z2125", "5 (пункт) статьи 101-1 -> п5 ст101-1"),
}


def main():
    html = FP.read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "html.parser")
    gt_before = soup.get_text()

    ids = {t.get("id") for t in soup.find_all(attrs={"id": True})}
    ids |= {a.get("name") for a in soup.find_all("a", attrs={"name": True})}
    # все цели должны существовать
    for frag, (tgt, _) in REPOINT.items():
        assert tgt in ids, f"target {tgt} not in ids!"
        assert frag not in ids, f"dead frag {frag} unexpectedly IS an anchor!"

    counts = {f: 0 for f in REPOINT}
    for a in soup.find_all("a", href=True):
        m = re.match(r"^#(z[\w.-]+)$", a["href"].strip())
        if not m:
            continue
        frag = m.group(1)
        if frag in REPOINT:
            a["href"] = "#" + REPOINT[frag][0]
            counts[frag] += 1

    gt_after = soup.get_text()
    assert gt_before == gt_after, "get_text changed!"
    assert hashlib.sha256(gt_before.encode()).hexdigest() == \
           hashlib.sha256(gt_after.encode()).hexdigest()

    FP.write_text(str(soup), encoding="utf-8")

    print("РЕПОЙНТ унаследованных-битых само-ссылок zhilishniy (get_text=OK):")
    total = 0
    for frag, (tgt, note) in REPOINT.items():
        print(f"  #{frag:7} -> #{tgt:7}  x{counts[frag]}   [{note}]")
        total += counts[frag]
    print(f"всего перенаправлено: {total}")

    # пост-контроль: битых само-#z больше нет
    s2 = BeautifulSoup(FP.read_text(encoding="utf-8"), "html.parser")
    ids2 = {t.get("id") for t in s2.find_all(attrs={"id": True})}
    ids2 |= {a.get("name") for a in s2.find_all("a", attrs={"name": True})}
    broken = []
    for a in s2.find_all("a", href=True):
        m = re.match(r"^#(z[\w.-]+)$", a["href"].strip())
        if m and m.group(1) not in ids2:
            broken.append(a["href"])
    print(f"ПОСТ: битых относительных #z = {len(broken)}  {broken[:10]}")


if __name__ == "__main__":
    main()
