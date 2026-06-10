# -*- coding: utf-8 -*-
"""R4 БЛОК 1: закрытие mapping-gap кандидатов трёх новых законов.

python scripts/audit/r4_01_newlaws_gaps.py [--apply]
-> reports/r4/newlaws_gaps_report.md

Самоотсылки -> §4 (якорь статьи «Законодательство о X» / профильной статьи);
внешние -> корни по веб-сверенным НГР; падежные ключи -> npa_mapping;
мислинк pravoohranitel (гос. ОХРАНА vs гос. СЛУЖБА) -> ретаргет.
Сноски не линкуем; full span; гейты: invariance, G6, nested.
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import paths

APPLY = "--apply" in sys.argv
A = "https://adilet.zan.kz/rus/docs/"

NEW_KEYS = {
    "законодательством Республики Казахстан о государственном социальном заказе, государственном заказе на реализацию стратегического партнерства, грантах и премиях для неправительственных организаций в Республике Казахстан": "Z050000036_",
    "Закона Республики Казахстан \"О персональных данных и их защите\"": "Z1300000094",
    "законодательством Республики Казахстан о воинской службе": "Z1200000561",
    "законодательством Республики Казахстан о воинской службе и статусе военнослужащих": "Z1200000561",
    "законодательству Республики Казахстан о государственной службе": "Z1500000416",
    "Закон Республики Казахстан \"О государственной службе Республики Казахстан\"": "Z1500000416",
    "Законом Республики Казахстан \"О государственной службе Республики Казахстан\"": "Z1500000416",
    "Законом Республики Казахстан \"О жилищных отношениях\"": "Z970000094_",
    "Трудовой кодекс Республики Казахстан": "K1500000414",
    "Законом Республики Казахстан \"О государственных секретах\"": "Z990000349_",
    "Законом Республики Казахстан \"О связи\"": "Z040000567_",
}

RE_NOTE_BEFORE = 'class="note"'


def text_rx(t):
    return re.compile(r"[\s\xa0]+".join(re.escape(w) for w in t.split()))


def balance(raw):
    ev = []
    for m in re.finditer(r"<a\b[^>]*>|</a\s*>", raw, re.I):
        ev.append((m.start(), 1 if m.group(0)[1] != "/" else -1))
    return ev


def in_link(ev, pos):
    b = 0
    for p, d in ev:
        if p >= pos:
            break
        b += d
    return b > 0


def wrap_all(raw, phrase, href, skip_art=None):
    """Обернуть ВСЕ plain-вхождения phrase -> href. Сноски и уже-ссылки skip.
    skip_art: номер статьи, внутри которой не линкуем (самоотсылка в себя)."""
    n = 0
    while True:
        ev = balance(raw)
        done = False
        for m in text_rx(phrase).finditer(raw):
            if in_link(ev, m.start()) or "<" in m.group(0):
                continue
            if RE_NOTE_BEFORE in raw[max(0, m.start() - 300):m.start()]:
                continue
            if skip_art:
                head = None
                for hm in re.finditer(r'data-number="([\d-]+)" data-type="статья"',
                                      raw[:m.start()]):
                    head = hm.group(1)
                if head is None:
                    for hm in re.finditer(r"Статья\s+([\d-]+)\s*\.",
                                          re.sub(r"<[^>]+>", "", raw[:m.start()])):
                        head = hm.group(1)
                if head == skip_art:
                    continue
            raw = (raw[:m.start()] + f'<a href="{href}">' + m.group(0)
                   + "</a>" + raw[m.end():])
            n += 1
            done = True
            break
        if not done:
            break
    return raw, n


def gates(slug, raws, origs):
    ok = True
    for suf, raw in raws.items():
        if "".join(re.sub(r"<[^>]+>", " ", raw).split()) != origs[suf]:
            ok = False
            print(f"!! INVARIANCE FAIL {slug}_{suf}")
        d = bad = 0
        for t in re.finditer(r"<a\b[^>]*>|</a\s*>", raw, re.I):
            d += 1 if t.group(0)[1] != "/" else -1
            if d > 1 or d < 0:
                bad += 1
        if bad or d != 0:
            ok = False
            print(f"!! NESTED FAIL {slug}_{suf}")
    return ok


def main():
    L = [f"# R4 БЛОК 1 — gap-закрытие трёх новых законов ({'APPLY' if APPLY else 'DRY'})",
         ""]

    # ключи
    mp = json.loads(paths.NPA_MAPPING.read_text(encoding="utf-8"))
    added = sum(1 for k in NEW_KEYS if k not in mp)
    mp.update({k: v for k, v in NEW_KEYS.items() if k not in mp})
    if APPLY:
        paths.NPA_MAPPING.write_text(json.dumps(mp, ensure_ascii=False, indent=1),
                                     encoding="utf-8")
    L.append(f"npa_mapping: +{added} ключей (соцзаказ Z050000036_, госсекреты "
             f"Z990000349_, связь Z040000567_ — веб 2026-06-11; падежные формы "
             f"к ранее сверенным НГР)")
    L.append("")

    PLAN = {
        "gosuslugi": {
            "wrap": [
                ("законодательства Республики Казахстан в сфере оказания государственных и социально ответственных услуг", "#z4", "2"),
                ("законодательства Республики Казахстан в сфере оказания государственных услуг", "#z4", "2"),
                ("законодательством Республики Казахстан о государственном социальном заказе, государственном заказе на реализацию стратегического партнерства, грантах и премиях для неправительственных организаций в Республике Казахстан", A + "Z050000036_", None),
                ('Закона Республики Казахстан "О персональных данных и их защите"', A + "Z1300000094", None),
            ],
            "retarget": [],
        },
        "pravoohranitel": {
            "wrap": [
                ("законодательством Республики Казахстан о воинской службе", A + "Z1200000561", None),
                ("законодательству Республики Казахстан о государственной службе", A + "Z1500000416", None),
                ("законодательства Республики Казахстан о правоохранительной службе", "#z25", "2"),
                ('Закон Республики Казахстан "О государственной службе Республики Казахстан"', A + "Z1500000416", None),
                ('Законом Республики Казахстан "О жилищных отношениях"', A + "Z970000094_", None),
                ("Трудовой кодекс Республики Казахстан", A + "K1500000414", None),
            ],
            "retarget": [
                # МИСЛИНК source: Z950002483_ = «О Службе гос. ОХРАНЫ РК» (созвучный
                # акт), а фраза — закон «О государственной службе РК» -> Z1500000416
                (re.compile(r'(href=")https?://[^"]*/docs/Z950002483_[^"]*(")'),
                 r"\g<1>" + A + r"Z1500000416\g<2>",
                 "Z950002483_ (гос. ОХРАНА, мислинк source) -> Z1500000416"),
            ],
        },
        "persdata": {
            "wrap": [
                ("законодательство Республики Казахстан о персональных данных и их защите", "#z8", "4"),
                ("законодательством Республики Казахстан о воинской службе и статусе военнослужащих", A + "Z1200000561", None),
                ('Законом Республики Казахстан "О государственных секретах"', A + "Z990000349_", None),
                ('Законом Республики Казахстан "О связи"', A + "Z040000567_", None),
            ],
            "retarget": [
                # 17 самоотсылок, свёрнутых 68-м в href="#" -> якорь ст.4 (#z8)
                (re.compile(r'<a href="#">((?:(?!</a)[^<])*законодательств[^<]*?персональных данных[^<]*?)</a\s*>'),
                 r'<a href="#z8">\g<1></a>',
                 "самоотсылки href=# -> #z8 (ст.4 «Законодательство…»)"),
            ],
        },
    }

    for slug, plan in PLAN.items():
        forms = {}
        for suf in ("ready", "structured"):
            p = paths.FINAL / f"{slug}_{suf}.html"
            forms[suf] = [p, p.read_text(encoding="utf-8")]
        origs = {k: "".join(re.sub(r"<[^>]+>", " ", v[1]).split())
                 for k, v in forms.items()}
        L.append(f"## {slug}")
        L.append("")
        for rx, repl, why in plan["retarget"]:
            per = []
            for suf in forms:
                forms[suf][1], n = rx.subn(repl, forms[suf][1])
                per.append(n)
            L.append(f"- RETARGET {why}: {per}")
        for phrase, href, skip in plan["wrap"]:
            per = []
            for suf in forms:
                forms[suf][1], n = wrap_all(forms[suf][1], phrase, href,
                                            skip_art=skip)
                per.append(n)
            L.append(f"- WRAP «{phrase[:60]}» -> {href[len(A):] if href.startswith(A) else href}: {per}")
        ok = gates(slug, {k: v[1] for k, v in forms.items()}, origs)
        L.append(f"- гейты: {'OK' if ok else 'FAIL'}")
        L.append("")
        if APPLY and ok:
            for suf, (p, raw) in forms.items():
                p.write_text(raw, encoding="utf-8")

    L.append("СТОП/вето-строки для SDACHA_R3:")
    L.append("- pravoohranitel: статьи «Законодательство о правоохранительной "
             "службе» в законе НЕТ; самоотсылка переведена на ст.2 «Правовая "
             "основа службы в правоохранительных органах» (#z25) по духу §4 — "
             "ПРАВО ВЕТО Анары/владельца;")
    L.append("- gosuslugi: закон переименован («О государственных и социально "
             "ответственных услугах»), НГР Z1300000088 прежний — корпусные "
             "фразы со старым названием валидны.")
    out = paths.REPORTS / "r4" / "newlaws_gaps_report.md"
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
