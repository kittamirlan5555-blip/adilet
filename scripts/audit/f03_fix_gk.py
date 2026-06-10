# -*- coding: utf-8 -*-
"""ФИКС-РАУНД БЛОК 3: структурные дыры ГК + карта ГК-осо.

python scripts/audit/f03_fix_gk.py [--apply]
-> data/reports/audit/08_fixround_block3.md

1) grazhdanskiy READY: слитый «<h3 id=z311> Глава 4. Сделки Статья 147…»
   расщепляется на два h3; якорь z147h ПЕРЕНОСИТСЯ с абзаца тела на заголовок
   статьи (все #z147h-ссылки продолжают работать). nows-инвариант обязателен.
2) grazhdanskiy STRUCTURED: главный h3 обрезается до «Глава 4. Сделки» —
   статья 147 уже имеет свой <h3 id=z147h>, дубль видимого текста снимается
   (текст возвращается к source).
3) Обе формы: статьи 148/150/151/155/156 без якорей — инжекция
   <a id="z{N}h" name="z{N}h"></a> в <h3> (прецедент УК). Карта +6 записей.
4) article_map_grazhdanskiy_osob.json строится из заголовков ready (ground
   truth), сверка покрытия и наличия якорей в обеих формах.
5) Отложенный ретаргет Блока 2: ГК-осо «статей 151-152» -> K940001000_#z151h.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import auditlib as al

GK = al.FINAL / "grazhdanskiy_ready.html"
GKS = al.FINAL / "grazhdanskiy_structured.html"
INJECT = ["148", "150", "151", "155", "156"]

MERGED_READY = ('<h3 id="z311"> Глава 4. Сделки Статья 147. Понятие сделки '
                '</h3><p><a id="z147h" name="z147h"></a>')
SPLIT_READY = ('<h3 id="z311"> Глава 4. Сделки</h3>'
               '<h3><a id="z147h" name="z147h"></a> Статья 147. Понятие сделки '
               '</h3><p>')
MERGED_STRUCT = '<h3 id="z311"> Глава 4. Сделки Статья 147. Понятие сделки </h3>'
TRIM_STRUCT = '<h3 id="z311"> Глава 4. Сделки</h3>'


def inject_anchor(raw, num, log):
    """<h3>( )Статья {num}. -> <h3><a id=z{num}h ...></a>\\1Статья {num}."""
    pat = re.compile(rf"<h3>(\s*)(Статья {num}\.)")
    m = pat.search(raw)
    if not m:
        log.append(f"    FAIL: <h3> Статья {num}. не найден")
        return raw, False
    anchor = f'<a id="z{num}h" name="z{num}h"></a>'
    raw = raw[:m.start()] + f"<h3>{anchor}{m.group(1)}{m.group(2)}" + raw[m.end():]
    log.append(f"    инжекция z{num}h в <h3> @{m.start()}")
    return raw, True


def main():
    apply_mode = "--apply" in sys.argv
    L = ["# ФИКС-РАУНД БЛОК 3 — структурные дыры ГК + карта ГК-осо", "",
         f"Режим: {'APPLY' if apply_mode else 'DRY-RUN'}.", ""]
    ok = True

    # ---------- 1+3) ready ----------
    raw0 = GK.read_text(encoding="utf-8")
    raw = raw0
    assert MERGED_READY in raw, "ready: ожидаемый слитый заголовок не найден"
    raw = raw.replace(MERGED_READY, SPLIT_READY, 1)
    L.append("## ready: расщепление слитого заголовка + перенос z147h на <h3>")
    det = []
    for num in INJECT:
        raw, good = inject_anchor(raw, num, det)
        ok &= good
    L += det
    t0, t1 = al.TextMap(raw0), al.TextMap(raw)
    inv = t0.nows == t1.nows
    L.append(f"- nows-инвариант vs снапшот: **{'PASS' if inv else 'FAIL'}**; "
             f"nested={len(al.RE_NESTED_CLOSE.findall(raw))} "
             f"dbl={len(al.RE_DOUBLE_HREF.findall(raw))}")
    ok &= inv
    ready_raw = raw

    # ---------- 2+3) structured ----------
    raw0s = GKS.read_text(encoding="utf-8")
    raws = raw0s
    assert MERGED_STRUCT in raws, "structured: слитый заголовок не найден"
    raws = raws.replace(MERGED_STRUCT, TRIM_STRUCT, 1)
    L.append("\n## structured: обрезка главного h3 (снят дубль «Статья 147…»)")
    det = []
    for num in INJECT:
        raws, good = inject_anchor(raws, num, det)
        ok &= good
    L += det
    # structured МЕНЯЕТ текст (дубль снят) — гейт = сравнение с READY (==source)
    tr = al.TextMap(ready_raw, strip_labels=True)
    ts = al.TextMap(raws, strip_labels=True)
    sync = tr.nows == ts.nows
    L.append(f"- nows structured == ready (после правок): **{'PASS' if sync else 'FAIL'}**; "
             f"nested={len(al.RE_NESTED_CLOSE.findall(raws))} "
             f"dbl={len(al.RE_DOUBLE_HREF.findall(raws))}")
    ok &= sync

    # ---------- карта ГК ----------
    mp = al.MAPS / "article_map_grazhdanskiy.json"
    m = json.loads(mp.read_text(encoding="utf-8"))
    changes = {"147": "z147h"} | {n: f"z{n}h" for n in INJECT}
    L.append("\n## article_map_grazhdanskiy: обновления")
    for k, v in changes.items():
        L.append(f"- {k}: {m.get(k)} -> {v}")
        m[k] = v
    # резолвер-гейт: каждый новый якорь над/на заголовке своей статьи
    for k, v in changes.items():
        for nm, rw in (("ready", ready_raw), ("structured", raws)):
            idp = al.id_positions(rw)
            cl = al.article_clusters(rw)
            import bisect
            pos = idp.get(v)
            if pos is None:
                L.append(f"- **FAIL: {v} нет в {nm}**")
                ok = False
                continue
            i = bisect.bisect_right([c[0] for c in cl], pos) - 1
            got = cl[i][1] if i >= 0 else None
            if got != k:
                L.append(f"- **FAIL: {v} в {nm} резолвится в ст.{got}, не {k}**")
                ok = False
    L.append("- резолвер-гейт новых якорей: " + ("**PASS (12/12)**" if ok else "см. FAIL выше"))

    # ---------- 4) карта ГК-осо ----------
    L.append("\n## article_map_grazhdanskiy_osob: сборка из заголовков (ready)")
    gko_r = (al.FINAL / "grazhdanskiy_osob_ready.html").read_text(encoding="utf-8")
    gko_s = (al.FINAL / "grazhdanskiy_osob_structured.html").read_text(encoding="utf-8")
    cl = al.article_clusters(gko_r)
    ids_s = al.ids_of(gko_s)
    gmap, no_anchor, not_in_str = {}, [], []
    for pos, num, anc, fam in cl:
        if anc is None:
            no_anchor.append(num)
            continue
        gmap.setdefault(num, anc)
        if anc not in ids_s:
            not_in_str.append((num, anc))
    L.append(f"- статей в разметке: {len(cl)}; в карту: **{len(gmap)}**; "
             f"якорей, отсутствующих в structured: {len(not_in_str)} {not_in_str[:5]}")
    L.append(f"- БЕЗ якоря (одиночные <h3> без id, класс ГК-148): {len(no_anchor)} "
             f"{no_anchor} — **строка в отчёт, инжекция НЕ заказана** (вне карты "
             "до решения шефа)")
    ok &= (len(not_in_str) == 0)

    # ---------- 5) отложенный ретаргет ГК-осо 151-152 ----------
    # ready: один спан «статей 151-152» -> z151h (первая статья диапазона);
    # structured: спан разорван на ДВЕ ссылки — «статей 151»(#z320, мислинк) +
    # «152»(#z322, корректна) — чиним только первую.
    L.append("\n## ГК-осо: «статей 151-152» -> K940000_#z151h (по формам)")
    OLD = 'https://adilet.zan.kz/rus/docs/K940001000_#z320'
    NEW = 'https://adilet.zan.kz/rus/docs/K940001000_#z151h'
    TEXTS = {"ready": "статей 151-152", "structured": "статей 151"}
    n_rt = {}
    out_gko = {}
    for nm, rw in (("ready", gko_r), ("structured", gko_s)):
        cnt = 0
        for mt in list(al.RE_A_PAIR.finditer(rw)):
            if mt.group(1) == OLD and al.strip_tags(mt.group(2)) == TEXTS[nm]:
                rw = rw[:mt.start()] + mt.group(0).replace(
                    f'href="{OLD}"', f'href="{NEW}"', 1) + rw[mt.end():]
                cnt += 1
        n_rt[nm] = cnt
        out_gko[nm] = rw
        L.append(f"- {nm}: текст {TEXTS[nm]!r}, заменено {cnt}; nows-инвариант: "
                 f"{'PASS' if al.TextMap(rw).nows == al.TextMap(gko_r if nm=='ready' else gko_s).nows else 'FAIL'}")
    ok &= all(v == 1 for v in n_rt.values())

    L.append(f"\n**ИТОГ: {'ВСЕ ГЕЙТЫ PASS' if ok else 'ЕСТЬ FAIL — НЕ ПРИМЕНЯТЬ'}**")
    if apply_mode and ok:
        GK.write_text(ready_raw, encoding="utf-8")
        GKS.write_text(raws, encoding="utf-8")
        mp.write_text(json.dumps(m, ensure_ascii=False, indent=1), encoding="utf-8")
        (al.MAPS / "article_map_grazhdanskiy_osob.json").write_text(
            json.dumps(gmap, ensure_ascii=False, indent=1), encoding="utf-8")
        (al.FINAL / "grazhdanskiy_osob_ready.html").write_text(
            out_gko["ready"], encoding="utf-8")
        (al.FINAL / "grazhdanskiy_osob_structured.html").write_text(
            out_gko["structured"], encoding="utf-8")
        L.append("ПРИМЕНЕНО: 2 формы ГК, 2 формы ГК-осо, 2 карты.")
    al.AUDIT_OUT.mkdir(parents=True, exist_ok=True)
    (al.AUDIT_OUT / "08_fixround_block3.md").write_text("\n".join(L) + "\n",
                                                        encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
