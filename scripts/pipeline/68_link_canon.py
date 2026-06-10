# -*- coding: utf-8 -*-
"""КАНОН ССЫЛОК (универсальный, как у кодексов): self full-URL -> относительный #z,
   + нормализация внешних кросс-рефов к https://adilet.zan.kz/rus/docs/{NGR}[#z].

КОНСОЛИДАЦИЯ клонов 68_{informatizacii,notariat,obrazovanie}_link_canon.py в ОДИН
скрипт с параметром --doc-id {NGR}. Код-ключ и все пути выводятся из config/codes.json
(обратный поиск doc_id -> key). Включён Step 2b «dropped-z» (#N -> #zN если zN есть),
который раньше был только в копии obrazovanie — для остальных это no-op (нет «голых»
числовых self-фрагментов), поэтому вывод байт-в-байт совпадает со старыми клонами.

Только атрибут href (raw-string/regex по сырому HTML), текст не трогаем —
get_text(before)==get_text(after) байт-в-байт. Бэкап перед записью.

Гейты: get_text идентичен | 0 битых само-якорей | 0 внешних архив/с-датой |
       все внешние в канон-форме adilet.
"""
import re
import sys
import json
import shutil
import argparse
from collections import Counter
from pathlib import Path
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import paths

ROOT = paths.ROOT


def resolve_code(doc_id: str):
    """Обратный поиск doc_id -> ключ кода по maps/codes.json."""
    codes = json.loads(paths.CODES_JSON.read_text(encoding="utf-8"))
    for k, v in codes.items():
        if isinstance(v, dict) and v.get("doc_id") == doc_id:
            return k
    raise SystemExit(f"doc_id {doc_id} не найден в maps/codes.json")


def gettext(html):
    return BeautifulSoup(html, "html.parser").get_text()


def main():
    ap = argparse.ArgumentParser(description="Канон ссылок: self full-URL -> #z")
    ap.add_argument("--doc-id", required=True, help="NGR кода (как в config/codes.json)")
    args = ap.parse_args()

    SELF = args.doc_id
    code = resolve_code(SELF)
    FP = paths.FINAL / f"{code}_structured.html"
    BK = paths.BACKUPS / f"final_backup_{code}"
    REPORT = paths.REPORTS / f"68_{code}_link_canon.txt"

    # self full-URL (любой base: 85.202… ИЛИ adilet) c фрагментом -> #zX
    RE_SELF_FRAG = re.compile(
        r'href="(?:https?://[^"]*?)/rus/docs/' + re.escape(SELF) + r'(#z[\w-]+)"')
    # self full-URL без фрагмента -> # (док-рут самого себя; редкий случай)
    RE_SELF_NOFRAG = re.compile(
        r'href="(?:https?://[^"]*?)/rus/docs/' + re.escape(SELF) + r'"')
    # внешний /docs/{NGR}[#frag] — захват для канонизации
    RE_EXT = re.compile(r'href="([^"]*?/docs/([A-Z]\d{6,}_?)([^"]*))"')
    CANON_EXT = re.compile(
        r'^https://adilet\.zan\.kz/rus/docs/[A-Z]\d{6,}_?(?:#z[\w-]+)?$')
    # признаки «архив/с датой/мусор Ctrl+S»
    RE_ANOMALY = re.compile(
        r'(web\.archive\.org|/history|\?|&|docs_date|/info\b|\.html$|file:|#!|%)')

    BK.mkdir(exist_ok=True)
    before = FP.read_text(encoding="utf-8")
    # бэкап среза ДО канона — только если ещё нет (идемпотентно, не затираем)
    pre = BK / f"{code}_structured.pre_canon.html"
    if not pre.exists():
        shutil.copy2(FP, pre)

    L = []
    P = L.append
    P("=" * 96)
    P(f"КАНОН ССЫЛОК {code}: self full-URL -> #z + нормализация внешних")
    P("=" * 96)

    html = before

    # ── Шаг 2: self full-URL -> #z ──────────────────────────────────────
    n_self_frag = len(RE_SELF_FRAG.findall(html))
    html = RE_SELF_FRAG.sub(r'href="\1"', html)
    # Шаг 2b: self full-URL с «голым» числовым фрагментом (напр. #1647).
    # adilet иногда роняет префикс 'z' в href, тогда как настоящий якорь — z{N}
    # (наблюдалось: текст «ст. 68» -> #1647, а в документе есть только id="z1647").
    # Нормализуем #{N} -> #z{N}, если z{N} существует (иначе #{N}, если есть; иначе
    # не трогаем -> попадёт в остаток-гейт).
    idset = {t.get("id") for t in BeautifulSoup(before, "html.parser")
             .find_all(attrs={"id": True}) if t.get("id")}
    RE_SELF_BARE = re.compile(
        r'href="(?:https?://[^"]*?)/rus/docs/' + re.escape(SELF) + r'#(\d[\w-]*)"')

    def _bare_self(m):
        n = m.group(1)
        if ("z" + n) in idset:
            return f'href="#z{n}"'
        if n in idset:
            return f'href="#{n}"'
        return m.group(0)
    n_self_bare = len(RE_SELF_BARE.findall(html))
    html = RE_SELF_BARE.sub(_bare_self, html)
    n_self_nofrag = len(RE_SELF_NOFRAG.findall(html))
    html = RE_SELF_NOFRAG.sub(r'href="#"', html)
    P(f"\n[self-URL -> #z]")
    P(f"  с фрагментом сокращено : {n_self_frag}")
    P(f"  «голый» #N -> #z{{N}}     : {n_self_bare}")
    P(f"  без фрагмента -> #      : {n_self_nofrag}")
    # остаточные self full-URL (whole-file, информационно: включает chrome-тулбар)
    rest_self_all = len(re.findall(r'/rus/docs/' + re.escape(SELF), html))
    P(f"  остаточных self full-URL (вся стр., вкл. chrome): {rest_self_all}")

    # ── Шаг 3: внешние — нормализация + детект аномалий ─────────────────
    anomalies = []
    normalized = []

    def norm_ext(m):
        full, ngr, tail = m.group(1), m.group(2), m.group(3)
        if ngr == SELF:
            return m.group(0)  # self уже обработан выше
        # фрагмент (если есть)
        fm = re.search(r'(#z[\w-]+)', tail)
        frag = fm.group(1) if fm else ""
        canon = f"https://adilet.zan.kz/rus/docs/{ngr}{frag}"
        if RE_ANOMALY.search(full):
            anomalies.append(full[:120])
        if full != canon:
            normalized.append((full[:80], canon[:80]))
            return f'href="{canon}"'
        return m.group(0)

    html = RE_EXT.sub(norm_ext, html)
    P(f"\n[внешние кросс-рефы]")
    P(f"  нормализовано к канону : {len(normalized)}")
    for a, b in normalized[:15]:
        P(f"     {a}  ->  {b}")
    P(f"  аномалий (архив/дата/?): {len(anomalies)}")
    for a in anomalies[:15]:
        P(f"     {a}")

    # ── Шаг 3.5: дедуп повторяющихся id ─────────────────────────────────
    # Источник adilet содержит коллизии native-якорей. Они НЕ адресуются нашими
    # ссылками, но ломают гейт dupID=0. Переименовываем все вхождения, кроме
    # первого: id="zX" -> id="zX__d2". Только для id, на которые НЕТ ссылок (#id) —
    # адресуемые дубли не трогаем (требуют ручного разбора). Текст не меняется.
    sp = BeautifulSoup(html, "html.parser")
    idc = Counter(t.get("id") for t in sp.find_all(attrs={"id": True}) if t.get("id"))
    href_ids = {a["href"][1:] for a in sp.find_all("a", href=True)
                if a["href"].startswith("#")}
    dups = sorted(i for i, c in idc.items() if c > 1)
    deduped, skipped = [], []
    for dup in dups:
        if dup in href_ids:
            skipped.append(dup)
            continue
        cnt = {"n": 0}

        def _ren(mm, _dup=dup, _cnt=cnt):
            _cnt["n"] += 1
            return mm.group(0) if _cnt["n"] == 1 else f'id="{_dup}__d{_cnt["n"]}"'
        html = re.sub(r'id="' + re.escape(dup) + r'"', _ren, html)
        deduped.append((dup, idc[dup]))
    P(f"\n[дедуп id] групп дублей: {len(dups)} | переименовано: {len(deduped)} "
      f"{deduped} | пропущено (адресуемые): {skipped}")

    # ── Шаг 3.6: норм. self-якоря одиночной «статья N» к канону карты ────
    # adilet иногда предлинковывает тело-ссылку «статьёй N» на NATIVE-якорь
    # начала секции (закладка «Примечание ИЗПИ» ПЕРЕД статьёй), тогда как канон.
    # якорь ЗАГОЛОВКА статьи — z{N}h (инжектирован шагом 07). Перенацеливаем
    # такие тело-ссылки на z{N}h: обе проверки (аудит и 67) резолвят их
    # единообразно. Только одиночные «статья N», только href.
    amap = json.loads((paths.MAPS /
                       f"article_map_{code}.json").read_text(encoding="utf-8"))
    ARTREF = re.compile(r'^(?:Стать[яиеью]+|статьей|статьи)\s+(\d+(?:-\d+)?)$', re.I)
    sp2 = BeautifulSoup(html, "html.parser")
    repoint = []
    for a in sp2.find_all("a", href=True):
        if not a.find_parent("div", attrs={"data-type": True}):
            continue
        if not a["href"].startswith("#"):
            continue
        rm = ARTREF.match(a.get_text(" ", strip=True))
        if not rm:
            continue
        N, cur, canon = rm.group(1), a["href"][1:], amap.get(rm.group(1))
        if canon and cur != canon:
            inner = a.decode_contents()
            old, new = f'<a href="#{cur}">{inner}</a>', f'<a href="#{canon}">{inner}</a>'
            if old in html:
                html = html.replace(old, new, 1)
                repoint.append((a.get_text(" ", strip=True), cur, canon))
    P(f"\n[норм self-якоря] тело-ссылок «статья N» -> z(N)h: {len(repoint)} {repoint}")

    # ── ГЕЙТ get_text ───────────────────────────────────────────────────
    gt_ok = gettext(before) == gettext(html)
    P(f"\n[ГЕЙТ] get_text(before)==get_text(after): {'OK' if gt_ok else 'FAIL!!!'}")
    assert gt_ok, "get_text изменился — STOP, не записываем"

    # запись
    FP.write_text(html, encoding="utf-8")
    P(f"  записан: {FP.name}")

    # ── ПОСТ-ПРОВЕРКИ ───────────────────────────────────────────────────
    s = BeautifulSoup(html, "html.parser")
    ids = {t.get("id") for t in s.find_all(attrs={"id": True})}
    ids |= {a.get("name") for a in s.find_all("a", attrs={"name": True})}
    rel = [a["href"] for a in s.find_all("a", href=True)
           if a["href"].startswith("#z")]
    broken = [h for h in rel if h[1:] not in ids]
    P(f"\n[ПОСТ] относительных #z: {len(rel)}  | битых: {len(broken)}")
    if broken:
        P(f"   битые: {broken[:10]}")

    # внешние — все канонические?
    ext = [a["href"] for a in s.find_all("a", href=True)
           if a.find_parent("div", attrs={"data-type": True})
           and re.search(r"/docs/[A-Z]\d{6,}_?", a["href"])
           and not re.search(r"/docs/" + re.escape(SELF), a["href"])]
    noncanon = [h for h in ext if not CANON_EXT.match(h)]
    P(f"[ПОСТ] внешних: {len(ext)}  | не-канон: {len(noncanon)}  | архив/дата: "
      f"{sum(1 for h in ext if RE_ANOMALY.search(h))}")
    for h in noncanon[:15]:
        P(f"   не-канон: {h[:110]}")

    # остаточные self full-URL ВНУТРИ КОНТЕНТА (div[data-type]) — это и есть гейт.
    # chrome-ссылки тулбара adilet живут ВНЕ div[data-type] и не трогаются.
    self_content = [a["href"] for a in s.find_all("a", href=True)
                    if a.find_parent("div", attrs={"data-type": True})
                    and re.search(r"/rus/docs/" + re.escape(SELF), a["href"])]
    rest_self = len(self_content)
    chrome = rest_self_all - rest_self
    P(f"[ПОСТ] self full-URL в контенте (div[data-type]): {rest_self}  (гейт=0)"
      f"  | вне контента (chrome-тулбар, не трогаем): {chrome}")
    for h in self_content[:10]:
        P(f"   self-в-контенте: {h[:110]}")

    P("\n" + "=" * 96)
    ok = gt_ok and not broken and not noncanon and rest_self == 0
    P(f"ИТОГ: get_text=OK | self-битых={len(broken)} | внеш-не-канон={len(noncanon)}"
      f" | self-остаток={rest_self}  =>  {'ВСЕ ГЕЙТЫ ОК' if ok else 'ЕСТЬ ПРОБЛЕМЫ'}")
    P("=" * 96)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"written: {REPORT}  ok={ok}  self_shortened={n_self_frag+n_self_nofrag}"
          f"  ext_norm={len(normalized)}  anomalies={len(anomalies)}")


if __name__ == "__main__":
    main()
