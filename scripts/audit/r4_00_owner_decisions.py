# -*- coding: utf-8 -*-
"""R4 БЛОК 0: исполнение решений владельца по итогам R3.

python scripts/audit/r4_00_owner_decisions.py [--apply]
-> reports/r4/owner_decisions_report.md

1-1: статейные #z старого банковского Z950002444_ -> корень Z2600000258
     (nalog/upk/zemelnyy, обе формы). Только href.
2:   слипания в nalog — ПРОВЕРЕНО: дефект уже в source (literal
     «изаконамиРеспублики», «взаконах» ×2 + «законом</a>Республики» без
     пробела на границе тега) -> НЕ чиним (текст НПА не меняем), в отчёт.
3-1: 7 ключей в npa_mapping (5 веб-подтверждённых R3 + ГЧП и госслужба,
     досверены вебом 2026-06-11: оба действуют, ред. 2026).
4-1: МФЦА Z1500000438#z1 -> корень акта (фразы «Конституционным законом РК
     "О МФЦА"» — акт целиком, §4).
Гейты: text-invariance, G6 двухформенных, баланс <a>.
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import paths

APPLY = "--apply" in sys.argv

NEW_KEYS = {
    "законодательства Республики Казахстан о противодействии легализации (отмыванию) доходов, полученных преступным путем, финансированию терроризма и финансированию распространения оружия массового уничтожения": "Z090000191_",
    "законодательства Республики Казахстан об обязательном страховании гражданско-правовой ответственности частных нотариусов": "Z030000435_",
    "законодательства Республики Казахстан об информатизации": "Z1500000418",
    "законодательством Республики Казахстан об информатизации": "Z1500000418",
    "законодательством Республики Казахстан о государственной службе": "Z1500000416",
    "законодательства Республики Казахстан о государственной службе": "Z1500000416",
    "законодательством Республики Казахстан в сфере искусственного интеллекта": "Z2500000230",
    "законодательства Республики Казахстан в сфере искусственного интеллекта": "Z2500000230",
    "законодательства Республики Казахстан в области технического регулирования": "Z2000000396",
    "законодательством Республики Казахстан в области технического регулирования": "Z2000000396",
    "законодательством Республики Казахстан в области государственно-частного партнерства": "Z1500000379",
    "законодательства Республики Казахстан в области государственно-частного партнерства": "Z1500000379",
}


def edit_doc(slug, subs):
    """subs: [(regex, repl)] на обе формы; гейты; возвращает (счётчики, ok)."""
    forms = {}
    for suf in ("ready", "structured"):
        p = paths.FINAL / f"{slug}_{suf}.html"
        if p.exists():
            forms[suf] = [p, p.read_text(encoding="utf-8")]
    orig = {k: "".join(re.sub(r"<[^>]+>", " ", v[1]).split())
            for k, v in forms.items()}
    counts = []
    for rx, repl in subs:
        per = []
        for suf in forms:
            forms[suf][1], n = rx.subn(repl, forms[suf][1])
            per.append(n)
        counts.append(per)
    ok = True
    for suf, (p, raw2) in forms.items():
        if "".join(re.sub(r"<[^>]+>", " ", raw2).split()) != orig[suf]:
            ok = False
            print(f"!! INVARIANCE FAIL {p.name}")
        depth = bad = 0
        for t in re.finditer(r"<a\b[^>]*>|</a\s*>", raw2, re.I):
            depth += 1 if t.group(0)[1] != "/" else -1
            if depth > 1 or depth < 0:
                bad += 1
        if bad or depth != 0:
            ok = False
            print(f"!! NESTED FAIL {p.name}")
    if len(forms) == 2:
        def pairs(r):
            return {(m.group(1), re.sub(r"\s+", " ", re.sub(
                r"<[^>]+>", "", m.group(2))).strip())
                for m in re.finditer(r'<a\b[^>]*href="([^"]*)"[^>]*>(.*?)</a\s*>',
                                     r, re.S)}
        if pairs(forms["ready"][1]) != pairs(forms["structured"][1]):
            ok = False
            print(f"!! G6 FAIL {slug}")
    if APPLY and ok:
        for suf, (p, raw2) in forms.items():
            p.write_text(raw2, encoding="utf-8")
    return counts, ok


def main():
    L = [f"# R4 БЛОК 0 — решения владельца ({'APPLY' if APPLY else 'DRY-RUN'})", ""]

    # 1-1: банковские статейные -> корень нового
    L.append("## 1-1: статейные ссылки старого банковского -> корень Z2600000258")
    L.append("")
    rx_bank = re.compile(r'(href="https?://[^"]*/docs/)Z950002444_#z[\w-]+(")')
    for slug in ("nalog", "upk", "zemelnyy"):
        counts, ok = edit_doc(slug, [(rx_bank, r"\g<1>Z2600000258\g<2>")])
        L.append(f"- {slug}: заменено {counts[0]} (формы), гейты "
                 f"{'OK' if ok else 'FAIL'}")
    L.append("")
    L.append("СТРОКА ДЛЯ ОТЧЁТА АНАРЕ: статейные отсылки к закону «О банках и")
    L.append("банковской деятельности в РК» 1995 г. (ст. 5-1, 50, 132) переведены")
    L.append("на корень нового закона Z2600000258 (закон 1995 г. утратил силу")
    L.append("19.03.2026; нумерация статей нового не совпадает — точечный якорь")
    L.append("будет восстановлен после карты соответствия статей).")
    L.append("")

    # 2: слипания — констатация
    L.append("## 2: слипшиеся слова nalog — НЕ чиним (дефект source)")
    L.append("")
    L.append("Проверка source/nalog.html: «изаконамиРеспублики» ×1 и «взаконах…»")
    L.append("×2 — литеральный текст выгрузки; «закономРеспублики» — отсутствие")
    L.append("пробела на границе </a> уже в source. Текст НПА не меняем (§6.1);")
    L.append("дефект исходника adilet — в отчёт Анаре/Ергали.")
    L.append("")

    # 3-1: ключи в маппинг
    L.append("## 3-1: ключи в npa_mapping.json")
    L.append("")
    mp = json.loads(paths.NPA_MAPPING.read_text(encoding="utf-8"))
    added = 0
    for k, v in NEW_KEYS.items():
        if k not in mp:
            mp[k] = v
            added += 1
            L.append(f"- + «{k[:80]}…» -> {v}" if len(k) > 80
                     else f"- + «{k}» -> {v}")
    if APPLY and added:
        paths.NPA_MAPPING.write_text(
            json.dumps(mp, ensure_ascii=False, indent=1), encoding="utf-8")
    L.append(f"добавлено: {added} (ИИ Z2500000230, ПОД/ФТ Z090000191_, техрег "
             f"Z2000000396, ГПО нотариусов Z030000435_, информатизация "
             f"Z1500000418 — веб R3; ГЧП Z1500000379 и госслужба Z1500000416 — "
             f"досверены вебом 2026-06-11, оба действуют)")
    L.append("")

    # 4-1: МФЦА -> корень
    L.append("## 4-1: МФЦА Z1500000438#z1 -> корень")
    L.append("")
    rx_mfca = re.compile(r'(href="https?://[^"]*/docs/)Z1500000438#z1(")')
    for slug in ("appk", "byudzhet", "nalog"):
        counts, ok = edit_doc(slug, [(rx_mfca, r"\g<1>Z1500000438\g<2>")])
        L.append(f"- {slug}: заменено {counts[0]}, гейты {'OK' if ok else 'FAIL'}")
    L.append("(статейные на МФЦА — напр. nalog Z1500000438#z51 «пункта 7 статьи 6» —")
    L.append("НЕ тронуты: там фраза со статьёй, якорь по делу.)")

    out = paths.REPORTS / "r4"
    out.mkdir(parents=True, exist_ok=True)
    (out / "owner_decisions_report.md").write_text("\n".join(L) + "\n",
                                                   encoding="utf-8")
    print("\n".join(L[-12:]))
    print(f"-> {out / 'owner_decisions_report.md'}")


if __name__ == "__main__":
    main()
