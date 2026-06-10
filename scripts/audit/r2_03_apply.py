# -*- coding: utf-8 -*-
"""ANARA R2 Фаза 3: применение 34 флагов к 3 законам (_structured — канон).

python scripts/audit/r2_03_apply.py [--apply]
-> data/reports/anara_r2/03_apply_report.md

Спан = ровно жёлтое Анары минус хвостовая пунктуация (канон r2_01.core_span).
Внешние акты -> корень БЕЗ #z. Самоотсылки (решение владельца 2026-06-10):
флаги 14/19 -> #z2h (ст.2 «Законодательство РК об информатизации»); флаг 3 ->
#zgl9 — ИНЖЕКЦИЯ пустого <a id name> в <h3> гл.9 «ЗАЩИТА ОБЪЕКТОВ
ИНФОРМАТИЗАЦИИ» (ст.53–56-1: ОЦИБ/НКЦИБ/единые требования) по прецеденту f03.
Перечень obrazovanie #3 — ТРИ отдельных <a>, запятые/«и»/точка вне спанов.
Гейты: nows-инвариант, nested=0, double=0, </a></a>=0, резолв якорей,
прямое присутствие каждого спана, пост-диагноз FULL_SPAN.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import auditlib as al
import r2_01_diag as d1

R2 = al.REPORTS / "anara_r2"
ROOT_URL = "https://adilet.zan.kz/rus/docs/"

# (slug, № флага) -> ("root", НГР) | ("anchor", "#id") | ("list", [(фраза, НГР)])
T = {}
for n in (1, 5, 16, 17, 18):
    T[("informatizacii", n)] = ("root", "K1500000375")
for n in (7, 8, 9, 10, 11):
    T[("informatizacii", n)] = ("root", "Z990000349_")
T.update({
    ("informatizacii", 2): ("root", "Z030000474_"),
    ("informatizacii", 3): ("anchor", "#zgl9"),
    ("informatizacii", 4): ("root", "Z1400000202"),
    ("informatizacii", 6): ("root", "Z1300000094"),
    ("informatizacii", 12): ("root", "K940001000_"),
    ("informatizacii", 13): ("root", "K940001000_"),
    ("informatizacii", 14): ("anchor", "#z2h"),
    ("informatizacii", 15): ("root", "Z1300000094"),
    ("informatizacii", 19): ("anchor", "#z2h"),
    ("informatizacii", 20): ("root", "K1400000231"),
    ("notariat", 1): ("root", "Z090000191_"),
    ("notariat", 2): ("root", "K2500000214"),
    ("notariat", 3): ("root", "Z980000326_"),
    ("notariat", 4): ("root", "K2500000214"),
    ("notariat", 5): ("root", "Z100000261_"),
    ("obrazovanie", 1): ("root", "Z970000151_"),
    ("obrazovanie", 2): ("root", "Z990000349_"),
    ("obrazovanie", 3): ("list", [
        ('законами Республики Казахстан "О государственном имуществе"',
         "Z1100000413"),
        ('"О некоммерческих организациях"', "Z010000142_"),
        ('"Об акционерных обществах"', "Z030000415_")]),
    ("obrazovanie", 4): ("root", "K2000000360"),
    ("obrazovanie", 5): ("root", "K1500000414"),
    ("obrazovanie", 6): ("root", "K1500000375"),
    ("obrazovanie", 7): ("root", "Z1400000202"),
    ("obrazovanie", 8): ("root", "K1400000235"),
    ("obrazovanie", 9): ("root", "Z1900000293"),
})
EXPECTED_WRAPS = {"informatizacii": 20, "notariat": 5, "obrazovanie": 11}

RE_GL9 = re.compile(
    r'(<div class="chapter" data-number="9" data-type="глава"><h3>)(\s*Глава 9\.)')


def locate(hay, flag, core, seen):
    """Та же дисциплина выбора вхождения, что в r2_01 (k-е возле статьи)."""
    needle = re.sub(r"\s+", " ", core).translate(d1.QT)
    occ = d1.occurrences(hay, needle)
    key = (flag["context"], core)
    k = seen.get(key, 0)
    seen[key] = k + 1
    # каскад полный контекст -> 60 -> 40 (фикс коллизии флагов 5/16)
    ctx = re.sub(r"\s+", " ", flag["context"].split(" - ", 1)[-1]
                 ).translate(d1.QT)
    ctx_pos = (d1.occurrences(hay, ctx) or d1.occurrences(hay, ctx[:60])
               or d1.occurrences(hay, ctx[:40]))
    cand = occ
    if ctx_pos:
        near = [o for o in occ
                if any(c - 50 <= o <= c + 2500 for c in ctx_pos)]
        cand = near or occ
    assert cand, f"ABSENT: {core[:60]}"
    o = cand[min(k, len(cand) - 1)]
    return o, o + len(needle)


def raw_bounds(tm, s, e):
    """Текстовый [s,e) -> сырой [rs,re). Конец entity-aware (&quot; целиком)."""
    rs = tm.pos[s]
    rp = tm.pos[e - 1]
    if tm.raw[rp] == "&":
        semi = tm.raw.find(";", rp, rp + 9)
        if semi != -1 and tm.raw[rp:semi + 1] in al.ENTITIES:
            return rs, semi + 1
    return rs, rp + 1


def heading_gate(raw, anchor_id, must_have, L):
    """Якорь стоит и резолвится в нужный заголовок (ловушка z1=ИЗПИ)."""
    m = re.search(r'(?:id|name)="%s"' % anchor_id, raw)
    assert m, f"якоря {anchor_id} нет"
    around = al.strip_tags(raw[m.start():m.start() + 300])
    ok = must_have in around
    L.append(f"- якорь `#{anchor_id}` -> «{around[:80]}…» — "
             f"{'PASS' if ok else '**FAIL**'}")
    return ok


def main():
    apply_mode = "--apply" in sys.argv
    mapping = json.loads((al.CONFIG / "npa_mapping.json")
                         .read_text(encoding="utf-8"))
    mvals = set(mapping.values())
    for spec in T.values():
        for ngr in ([spec[1]] if spec[0] == "root" else
                    [n for _, n in spec[1]] if spec[0] == "list" else []):
            assert ngr in mvals, f"НГР {ngr} нет в npa_mapping — опечатка?"

    L = ["# ANARA R2 — Фаза 3: применение флагов",
         "", f"Режим: {'APPLY' if apply_mode else 'DRY-RUN'}.", ""]
    ok = True
    grand = 0
    for slug in d1.SLUGS:
        flags = d1.parse_flags(R2 / f"anara_r2_flags_{slug}.md")
        fpath = al.FINAL / f"{slug}_structured.html"
        orig = fpath.read_text(encoding="utf-8")
        raw = orig

        L += [f"## {slug}", ""]
        if slug == "informatizacii":
            assert "zgl9" not in al.ids_of(raw), "zgl9 уже занят"
            raw, n_inj = RE_GL9.subn(
                r'\1<a id="zgl9" name="zgl9"></a>\2', raw, count=1)
            assert n_inj == 1, "заголовок гл.9 не найден"
            L.append("- инжекция `<a id=zgl9>` в `<h3>` гл.9 (пустой якорь, "
                     "текст не меняется) — по прецеденту f03/УК")

        tm = al.TextMap(raw)
        hay = tm.text.translate(d1.QT)
        contents = [(m.start(2), m.end(2)) for m in al.RE_A_PAIR.finditer(raw)]

        # план спанов: (rs, re, href, текст, № флага)
        plan, seen = [], {}
        for f in flags:
            spec = T[(slug, f["num"])]
            for _kind, frag in f["frags"]:
                core, _ = d1.core_span(frag)
                s, e = locate(hay, f, core, seen)
                subs = []
                if spec[0] == "list":
                    for sub, ngr in spec[1]:
                        sn = re.sub(r"\s+", " ", sub).translate(d1.QT)
                        p = hay.find(sn, s, e)
                        assert p != -1, f"подфраза не в спане: {sub[:40]}"
                        subs.append((p, p + len(sn), ROOT_URL + ngr))
                elif spec[0] == "root":
                    subs.append((s, e, ROOT_URL + spec[1]))
                else:
                    subs.append((s, e, spec[1]))
                for ss, se, href in subs:
                    rs, re_ = raw_bounds(tm, ss, se)
                    # ядро вне ссылок (PLAIN из Фазы 1) и без тегов внутри
                    trs, tre = tm.pos[ss], tm.pos[se - 1] + 1
                    assert not any(cs < tre and trs < ce
                                   for cs, ce in contents), \
                        f"пересечение со ссылкой: флаг {f['num']}"
                    seg = raw[rs:re_]
                    assert "<" not in seg, \
                        f"тег внутри спана флага {f['num']}: {seg[:60]}"
                    plan.append((rs, re_, href, seg, f["num"]))

        plan.sort()
        for (a, b, *_), (c, *_2) in zip(plan, plan[1:]):
            assert b <= c, "перекрытие спанов в плане"
        for rs, re_, href, seg, _n in reversed(plan):
            raw = raw[:rs] + f'<a href="{href}">' + seg + "</a>" + raw[re_:]

        # ---- гейты ----
        g = []
        inv = al.TextMap(orig).nows == al.TextMap(raw).nows
        g.append(("nows-инвариант", inv))
        g.append(("</a></a> = 0", not al.RE_NESTED_CLOSE.search(raw)))
        g.append(("двойной href = 0", not al.RE_DOUBLE_HREF.search(raw)))
        g.append(("вложенных <a> = 0",
                  not any("<a" in m.group(2)
                          for m in al.RE_A_PAIR.finditer(raw))))
        # голый href="#" ×2 («РУС»/«Текст») — навигационная обвязка adilet,
        # есть во всех исходниках до правок; не правовая ссылка, не считаем
        ids = al.ids_of(raw)
        bad_anc = [h for _p, h, _t, _r in al.links_of(raw)
                   if h.startswith("#") and len(h) > 1 and h[1:] not in ids]
        g.append((f"внутренние якоря резолвятся (битых {len(bad_anc)}; "
                  "голый «#» ×2 — навигация, вне гейта)", not bad_anc))
        present = all(f'<a href="{h}">{s}</a>' in raw
                      for _a, _b, h, s, _n in plan)
        g.append(("каждый спан присутствует точно", present))
        delta = len(al.links_of(raw)) - len(al.links_of(orig))
        exp = EXPECTED_WRAPS[slug] + (1 if slug == "informatizacii" else 0)
        # +1 у informatizacii — пустой якорь zgl9 не имеет href, в links_of
        # не попадает; ожидание по href-ссылкам = EXPECTED_WRAPS
        g.append((f"добавлено href-ссылок {delta} == {EXPECTED_WRAPS[slug]}",
                  delta == EXPECTED_WRAPS[slug]))

        # пост-диагноз: каждый обёрнутый спан теперь FULL_SPAN
        tm2 = al.TextMap(raw)
        hay2 = tm2.text.translate(d1.QT)
        contents2 = [(m.start(2), m.end(2))
                     for m in al.RE_A_PAIR.finditer(raw)]
        seen2 = {}
        full = True
        for f in flags:
            spec = T[(slug, f["num"])]
            for _kind, frag in f["frags"]:
                core, _ = d1.core_span(frag)
                if spec[0] == "list":
                    s, e = locate(hay2, f, core, seen2)
                    pieces = [(hay2.find(re.sub(r"\s+", " ", sub)
                                         .translate(d1.QT), s, e),
                               len(sub)) for sub, _ in spec[1]]
                    vs = [d1.diagnose(tm2.pos[p], tm2.pos[p + ln - 1] + 1,
                                      contents2) for p, ln in pieces]
                else:
                    s, e = locate(hay2, f, core, seen2)
                    vs = [d1.diagnose(tm2.pos[s], tm2.pos[e - 1] + 1,
                                      contents2)]
                if any(v != "FULL_SPAN" for v in vs):
                    full = False
                    L.append(f"- **флаг {f['num']} пост-диагноз: {vs}**")
        g.append(("пост-диагноз: все спаны FULL_SPAN", full))

        if slug == "informatizacii":
            ok &= heading_gate(raw, "zgl9", "Глава 9", L)
            ok &= heading_gate(raw, "z2h", "Статья 2", L)

        L += ["", "| гейт | статус |", "|---|---|"]
        for name, passed in g:
            L.append(f"| {name} | {'PASS' if passed else '**FAIL**'} |")
            ok &= passed
        L += ["", f"Спанов обёрнуто: {len(plan)}", ""]
        L += ["| флаг | спан (стало) | цель |", "|---|---|---|"]
        for _a, _b, href, seg, n in plan:
            disp = seg if len(seg) <= 65 else seg[:62] + "…"
            L.append(f"| {n} | «{disp}» | `{href}` |")
        L.append("")
        grand += len(plan)

        if apply_mode and ok:
            fpath.write_text(raw, encoding="utf-8")
            L.append(f"[APPLIED] {fpath.name} записан")
        elif apply_mode:
            L.append(f"[ABORT] {slug}: FAIL — файл НЕ записан")
        L.append("")

    L += [f"**ИТОГО спанов: {grand} (20+5+11), гейты: "
          f"{'PASS' if ok else 'FAIL'}**"]
    out = R2 / "03_apply_report.md"
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))
    print(f"-> {out}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
