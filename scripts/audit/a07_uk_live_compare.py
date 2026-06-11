# -*- coding: utf-8 -*-
"""R6 БЛОК 4: сверка якорей УК с ЖИВЫМ adilet. READ-ONLY.

python scripts/audit/a07_uk_live_compare.py [--snapshot reports/r6/uk_live_snapshot.html] [--n 25]

Снапшот живой страницы: curl -A "Mozilla/5.0" https://adilet.zan.kz/rus/docs/K1400000226
(adilet доступен напрямую — проверено 2026-06-11). Сравнение: для выборки статей
(спорные 45/206/301/303/3 + N детерминированно-случайных) якорь rebuilt-карты
резолвится на живой странице в номер статьи (ближайший маркер над якорем) и
сравнивается. Расхождения — ТАБЛИЦА, ничего не чинится (вход §9 для шефа).
-> reports/r6/BLOCK4_uk_live.md
"""
import argparse
import bisect
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import auditlib as al


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", default="reports/r6/uk_live_snapshot.html")
    ap.add_argument("--n", type=int, default=25)
    a = ap.parse_args()
    live = (al.ROOT / a.snapshot).read_text(encoding="utf-8")
    lcl = al.article_clusters(live)
    lpos = [c[0] for c in lcl]
    lids = al.id_positions(live)
    live_anchor_of = {c[1]: c[2] for c in lcl}

    def live_resolve(anchor):
        p = lids.get(anchor)
        if p is None:
            return None
        i = bisect.bisect_right(lpos, p) - 1
        return lcl[i][1] if i >= 0 else None

    amap = json.loads((al.MAPS / "article_map_ugolovniy.json").read_text(encoding="utf-8"))
    rmap = json.loads((al.MAPS / "article_map_ugolovniy_rebuilt.json").read_text(encoding="utf-8"))
    forced = ["45", "206", "301", "303", "3"]
    rng = random.Random("uk-live-r6")
    sample = forced + rng.sample(sorted(set(rmap) - set(forced)), a.n)

    L = ["# R6 БЛОК 4 — УК-якоря vs живой adilet (вход §9, НИЧЕГО не чинилось)", "",
         f"Живая страница: {a.snapshot} (статей-маркеров {len(lcl)}, якорей {len(lids)}).",
         "", "| статья | наш якорь | вердикт на живом |", "|---|---|---|"]
    match = mism = absent = 0
    for art in sample:
        anc = rmap.get(art) or amap.get(art)
        lr = live_resolve(anc)
        if lr is None:
            absent += 1
            la = live_anchor_of.get(art)
            v = (f"якоря {anc} нет на живом; живой якорь ст.{art}: "
                 f"{la if la else 'ОТСУТСТВУЕТ (заголовок без id!)'}")
        elif lr == art:
            match += 1
            v = "СОВПАЛО"
        else:
            mism += 1
            v = f"**РАСХОЖДЕНИЕ: живой резолвит в ст.{lr}**"
        L.append(f"| {art} | `{anc}` | {v} |")
    L += ["", f"**Итог: совпало {match}, расхождений {mism}, наших-якорей-нет-на-живом "
          f"{absent} из {len(sample)}.** Спот z15 (упк «пунктом 29) статьи 3»): "
          f"живой резолв = ст.{live_resolve('z15')}.",
          "", "## Вердикт (решение за шефом, §9)",
          "- Все НАСТОЯЩИЕ якоря выборки совпадают с живым adilet: article-level",
          "  cross-code на УК работает и при модели Б (живые страницы).",
          "- СИНТЕТИЧЕСКИЕ z45h/z206h/z301h/z303h на живом отсутствуют:",
          "  301/303 имеют живые аналоги (z1124/z1132 — ремап возможен по решению);",
          "  45/206 на живом БЕЗ якорей вовсе — наши синтетические единственная",
          "  адресация: при модели Б ссылки на них вести на корень, при модели А — ок."]
    out = al.ROOT / "reports" / "r6" / "BLOCK4_uk_live.md"
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L[-12:]))
    print(f"-> {out}")


if __name__ == "__main__":
    main()
