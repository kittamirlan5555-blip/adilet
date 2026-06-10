# -*- coding: utf-8 -*-
"""АУДИТ ФАЗА 3: куда РЕАЛЬНО ведут ссылки. READ-ONLY.

python scripts/audit/a03_links.py [slug ...]
-> data/reports/audit/03_links_{slug}.md + 03_links_{slug}.json + 03_SUMMARY.md

Канонические формы: кодексы = *_ready.html, законы = *_structured.html (§10).

Классификация каждой <a href>:
  INT  внутренняя #zN: якорь существует (иначе BROKEN); резолв = ближайший
       маркер статьи НАД якорем; номер сравнивается с кандидатами из текста
       ссылки и ±контекста (прецеденты мислинков: nalog 351-1, socialnyy 9-4).
       Несовпадение -> WRONG_TARGET (со сниппетами обеих сторон).
  XC   cross-code на НАШ документ ({НГР}#z…): тот же резолв в файле цели.
  EXT  внешние НГР: таблица частот, сверка с npa_mapping, известные протухшие.
  SELF href на собственный НГР (absolute self-reference, ТЗ-01 R01).
Плюс: R15 (вложенные </a></a> СЫРЫМ поиском, двойные href) и выборка 30 ссылок
на спан-дисциплину (R06-R08).
"""
import json
import re
import sys
import bisect
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import auditlib as al

HOST_RE = re.compile(r"^(?:https?:)?//[^/]*adilet[^/]*/(?:rus|kaz)/docs/", re.I)
RE_DOCREF = re.compile(r"/docs/([A-Za-z0-9_]+)(?:\?[^\"#]*)?(?:#([\w-]+))?$")
# СТЕМ: «стат[ье]» а не «стать» — род.падеж мн.ч. «статей» НЕ содержит «стать»
# (статья/статьи/статье/статьей/статьями/статьях/статей). Урок этого аудита.
RE_ART_NUM = re.compile(r"стат[ье]\w*\s+(\d+(?:-\d+)*)", re.I)
RE_BARE = re.compile(r"^\s*(\d+(?:-\d+)*)\s*\)?\s*$")

KNOWN_STALE = {
    "Z950002444_": "О банках 1995 — ЗАМЕНЁН (действ. Z2600000258); решение по ремапу — за шефом",
    "K1700000120": "Налоговый кодекс 2017 — старая редакция (наш nalog=K2500000214)",
    "K080000095_": "Бюджетный кодекс 2008 — старая редакция (наш byudzhet=K2500000171)",
    "K950001000_": "Конституция 1995 (ред.?) — РЕШЕНИЕ ЗА ШЕФОМ, только подсчёт",
    "Z2500000239": "ежегодный закон о республиканском бюджете — обновлять каждый декабрь",
}


def canon_file(slug):
    f = al.doc_files(slug)
    return ("ready", f["ready"]) if "ready" in f else ("structured", f["structured"])


class Doc:
    """Кэшируемое представление документа для резолва целей.

    Резолв якоря в номер статьи:
      1) АВТОРИТЕТНО по article_map/subpoint_map (как делает корпус);
      2) фолбэк — позиционно: статья НАД якорем; если якорь висит в «зазоре»
         прямо перед следующим заголовком (<=400 сырых симв; адилет ставит
         якоря на «Примечание ИЗПИ!» между статьями) — допускаем и следующую.
    Возвращает МНОЖЕСТВО допустимых номеров (обычно 1-2)."""

    def __init__(self, slug):
        self.slug = slug
        self.form, self.path = canon_file(slug)
        self.raw = self.path.read_text(encoding="utf-8")
        self.ids = al.id_positions(self.raw)
        self.clusters = al.article_clusters(self.raw)
        self.cl_pos = [c[0] for c in self.clusters]
        self.rev = {}
        amp = al.MAPS / f"article_map_{slug}.json"
        if amp.exists():
            for art, anc in json.loads(amp.read_text(encoding="utf-8")).items():
                self.rev.setdefault(anc, str(art))
        smp = al.MAPS / f"subpoint_map_{slug}.json"
        if smp.exists():
            for key, anc in json.loads(smp.read_text(encoding="utf-8")).items():
                self.rev.setdefault(anc, str(key).split("_", 1)[0])

    def resolve(self, anchor):
        """Якорь -> (set допустимых номеров статей | None, позиция | None)."""
        p = self.ids.get(anchor)
        if p is None:
            return None, None
        mapped = self.rev.get(anchor)
        if mapped is not None:
            return {mapped}, p
        i = bisect.bisect_right(self.cl_pos, p) - 1
        out = set()
        if i >= 0:
            out.add(self.clusters[i][1])
        if i + 1 < len(self.clusters) and 0 <= self.cl_pos[i + 1] - p <= 400:
            out.add(self.clusters[i + 1][1])
        return (out or None), p


_doc_cache = {}


def get_doc(slug):
    if slug not in _doc_cache:
        _doc_cache[slug] = Doc(slug)
    return _doc_cache[slug]


RE_TITLE_CUT = re.compile(r"Статья\s+\d+(?:-\d+)*\.")
RE_SUBDIV_TXT = re.compile(r"^\s*(?:под)?пункт\w*|^\s*част\w*|^\s*абзац\w*", re.I)
RE_STRUCT_TXT = re.compile(r"^\s*(?:раздел|глав|параграф|подраздел)\w*", re.I)
RE_OPENER = re.compile(r"(стат[ье]|пункт|подпункт|част|глав|раздел|параграф)\w*", re.I)
RE_LEAD_NUM = re.compile(r"^\s*(\d+(?:-\d+)*)\s*\)?(?:\s|$)")


def candidates(raw, pos, href_text, match_len):
    """Номера статей-кандидатов по грамматике цитирования. None = НЕ СУДИТЬ.

    - «разделом 7», «главой 11» — структурные единицы: резолв по статье
      неприменим -> None.
    - текст с ВЕДУЩИМ номером («321», «245 Уголовного кодекса…», «2»):
      номер — кандидат, ТОЛЬКО если ближайший опенер перечня слева —
      «стат…» (иначе это номер пункта/подпункта — не судим).
    - текст начинается с пункт/подпункт/часть/абзац: терминатор «статьи N»
      стоит ПОСЛЕ; before-контекст не используем; after обрезаем на
      «настоящ…» («настоящей статьи» = номера нет -> не судим).
    - текст без номера статьи вообще («законом», «Уголовным кодексом») —
      не судим (кроме разорванного спана «…статьей</a> 100»: ведущий номер
      after-контекста).
    Контексты обрезаются по заголовку «Статья N.» с обеих сторон."""
    if RE_STRUCT_TXT.match(href_text):
        return None
    before = al.strip_tags(raw[max(0, pos - 3000):pos])
    after = al.strip_tags(raw[pos + match_len:pos + match_len + 1500])
    tcut = None
    for m in RE_TITLE_CUT.finditer(before):
        tcut = m.end()
    if tcut is not None:
        before = before[tcut:]
    m = RE_TITLE_CUT.search(after)
    if m:
        after = after[:m.start()]
    cands = set(RE_ART_NUM.findall(href_text))

    if not cands:
        lead = RE_LEAD_NUM.match(href_text)
        if lead:
            opener = None
            for om in RE_OPENER.finditer(before[-600:]):
                opener = om.group(1).lower()
            if opener and opener.startswith("стат"):
                cands.add(lead.group(1))
                cands.update(RE_ART_NUM.findall(before[-300:]))
                cands.update(RE_ART_NUM.findall(after[:160]))
                return cands
            return None       # ведущий номер в не-статейном перечне — не судим
        if RE_SUBDIV_TXT.match(href_text):
            mn = re.search(r"настоящ", after)
            scope = after[:mn.start()] if mn else after
            got = RE_ART_NUM.findall(scope[:160])
            return set(got) or None
        if re.search(r"стат[ье]\w*\s*$", href_text, re.I):
            mn = RE_LEAD_NUM.match(after)
            if mn:
                return {mn.group(1)}      # разорванный спан «статьей</a> 100»
        return None           # generic-текст без номера — не судим

    cands.update(RE_ART_NUM.findall(before[-160:]))
    cands.update(RE_ART_NUM.findall(after[:160]))
    return cands


def span_flags(text, raw, pos, mlen):
    """Эвристики спан-дисциплины для выборки (R06-R08)."""
    flags = []
    arts = set(RE_ART_NUM.findall(text))
    if len(arts) > 1:
        flags.append("MERGED_ARTICLES(R07)")
    if re.fullmatch(r"(Закон\w*|Кодекс\w*|постановлени\w*)", text.strip()):
        cont = al.strip_tags(raw[pos + mlen:pos + mlen + 60])
        if re.match(r"\s*(Республики Казахстан|РК\b|«|\")", cont):
            flags.append("TORN_SPAN(R06)")
    if re.search(r"\(\s*част", text, re.I):
        flags.append("BRACKET_IN_SPAN(R07)")
    if len(text) > 300:
        flags.append("WHOLE_PARAGRAPH?(R08)")
    return flags


def audit_doc(slug, codes_by_id, mapping_ids):
    doc = get_doc(slug)
    raw = doc.raw
    own_id = None
    for did, s in codes_by_id.items():
        if s == slug:
            own_id = did
    links = al.links_of(raw)
    problems = []
    stats = dict(total=len(links), int_ok=0, int_wrong=0, int_broken=0,
                 int_nocand=0, int_preamble=0, xc_ok=0, xc_wrong=0, xc_broken=0,
                 xc_nocand=0, xc_preamble=0, ext_root=0, ext_anchored=0,
                 self_abs=0, chrome=0, other=0)
    ext_table = {}
    # хром сохранённой страницы adilet: всё ДО первого маркера статьи
    # (шапка: ҚАЗ/ENG/Избранное/«РУС» href="#") — не тело документа
    body_start = doc.cl_pos[0] if doc.cl_pos else 0

    for pos, href, text, m_raw in links:
        h = href.strip()
        if pos < body_start:
            stats["chrome"] += 1
            continue
        if h.startswith("#"):
            anchor = h[1:]
            res, ap = doc.resolve(anchor)
            if ap is None:
                stats["int_broken"] += 1
                problems.append(dict(type="INT_BROKEN", pos=pos, href=h, text=text,
                                     snippet=raw[max(0, pos - 80):pos + 160]))
                continue
            if res is None:
                stats["int_preamble"] += 1
                continue
            cands = candidates(raw, pos, text, len(m_raw))
            if not cands:
                stats["int_nocand"] += 1
                continue
            if res & cands:
                stats["int_ok"] += 1
            else:
                stats["int_wrong"] += 1
                problems.append(dict(
                    type="INT_WRONG_TARGET", pos=pos, href=h, text=text,
                    resolved=sorted(res), candidates=sorted(cands),
                    snippet=raw[max(0, pos - 80):pos + 160],
                    target_snippet=raw[max(0, ap - 80):ap + 160]))
            continue
        dm = RE_DOCREF.search(h.split("#")[0] + ("#" + h.split("#", 1)[1] if "#" in h else ""))
        dm = re.search(r"/docs/([A-Za-z0-9_]+)", h)
        if dm:
            ngr = dm.group(1)
            frag = h.split("#", 1)[1] if "#" in h else None
            if own_id and ngr == own_id:
                stats["self_abs"] += 1
                problems.append(dict(type="SELF_ABSOLUTE", pos=pos, href=h, text=text,
                                     snippet=raw[max(0, pos - 80):pos + 160]))
                continue
            if ngr in codes_by_id and frag:
                tgt = get_doc(codes_by_id[ngr])
                res, ap = tgt.resolve(frag)
                if ap is None:
                    stats["xc_broken"] += 1
                    problems.append(dict(type="XC_BROKEN_ANCHOR", pos=pos, href=h,
                                         text=text, target=codes_by_id[ngr],
                                         snippet=raw[max(0, pos - 80):pos + 160]))
                    continue
                if res is None:
                    stats["xc_preamble"] += 1
                    continue
                cands = candidates(raw, pos, text, len(m_raw))
                if not cands:
                    stats["xc_nocand"] += 1
                    continue
                if res & cands:
                    stats["xc_ok"] += 1
                else:
                    stats["xc_wrong"] += 1
                    problems.append(dict(
                        type="XC_WRONG_TARGET", pos=pos, href=h, text=text,
                        target=codes_by_id[ngr], resolved=sorted(res),
                        candidates=sorted(cands),
                        snippet=raw[max(0, pos - 80):pos + 160],
                        target_snippet=tgt.raw[max(0, ap - 80):ap + 160]))
                continue
            # внешний НГР (или наш без #z = корень на наш документ)
            key = ngr
            ext_table[key] = ext_table.get(key, 0) + 1
            if frag and ngr not in codes_by_id:
                stats["ext_anchored"] += 1
            else:
                stats["ext_root"] += 1
            continue
        stats["other"] += 1

    # R15 сырые гейты
    nested = len(al.RE_NESTED_CLOSE.findall(raw))
    double = len(al.RE_DOUBLE_HREF.findall(raw))

    # выборка спанов
    r = al.rng(slug)
    sample_idx = sorted(r.sample(range(len(links)), min(30, len(links))))
    sample_rows = []
    n_flagged = 0
    for i in sample_idx:
        pos, href, text, m_raw = links[i]
        fl = span_flags(text, raw, pos, len(m_raw))
        n_flagged += bool(fl)
        sample_rows.append((i, text[:70], fl,
                            raw[max(0, pos - 60):pos + len(m_raw) + 60]))

    # ---------- отчёты ----------
    al.AUDIT_OUT.mkdir(parents=True, exist_ok=True)
    j = dict(slug=slug, form=doc.form, stats=stats, nested_close=nested,
             double_href=double,
             ext_table=dict(sorted(ext_table.items(), key=lambda x: -x[1])),
             problems=problems)
    (al.AUDIT_OUT / f"03_links_{slug}.json").write_text(
        json.dumps(j, ensure_ascii=False, indent=1), encoding="utf-8")

    L = [f"# АУДИТ 03 — ссылки: {slug} ({doc.path.name})", "",
         f"Воспроизводимость: `PYTHONIOENCODING=utf-8 python scripts/audit/a03_links.py {slug}`",
         "", "## Счётчики", "",
         f"- всего `<a href>`: **{stats['total']}**",
         f"- внутренние: OK={stats['int_ok']}  WRONG_TARGET=**{stats['int_wrong']}**  "
         f"BROKEN=**{stats['int_broken']}**  без-кандидатов(не статья)={stats['int_nocand']}  "
         f"преамбула={stats['int_preamble']}",
         f"- cross-code (наш корпус): OK={stats['xc_ok']}  WRONG=**{stats['xc_wrong']}**  "
         f"BROKEN=**{stats['xc_broken']}**  без-кандидатов={stats['xc_nocand']}  "
         f"преамбула={stats['xc_preamble']}",
         f"- внешние: корневые={stats['ext_root']}  с якорем (непроверяемо, §4!)="
         f"**{stats['ext_anchored']}**",
         f"- self-reference абсолютным URL (R01, тело документа): **{stats['self_abs']}**",
         f"- хром сохранённой страницы adilet (до 1-й статьи: ҚАЗ/ENG/Избранное и т.п.): "
         f"{stats['chrome']}",
         f"- R15: `</a></a>` сырым поиском = **{nested}**; двойной href = **{double}**",
         ""]

    wrongs = [p for p in problems if p["type"].endswith("WRONG_TARGET")]
    brokens = [p for p in problems if "BROKEN" in p["type"]]
    selfs = [p for p in problems if p["type"] == "SELF_ABSOLUTE"]
    if wrongs:
        L.append("## WRONG_TARGET (ссылка ведёт не на ту статью)\n")
        for p in wrongs[:25]:
            L += [f"### @{p['pos']} `{p['href']}` текст={p['text'][:60]!r} "
                  f"резолв=ст.{p['resolved']} кандидаты={p['candidates']}",
                  "ссылка:", "```", p["snippet"], "```",
                  "цель:", "```", p.get("target_snippet", ""), "```", ""]
    if brokens:
        L.append("## BROKEN (якорь не существует)\n")
        for p in brokens[:15]:
            L += [f"- @{p['pos']} `{p['href']}` {p['text'][:60]!r}", "```",
                  p["snippet"], "```"]
    if selfs:
        L.append(f"\n## SELF_ABSOLUTE ({len(selfs)}) — первые 10\n")
        for p in selfs[:10]:
            L.append(f"- @{p['pos']} `{p['href']}` {p['text'][:60]!r}")

    L.append("\n## Внешние НГР (частоты, сверка с npa_mapping)\n")
    L += ["| НГР | ссылок | в mapping | примечание |", "|---|---|---|---|"]
    for ngr, n in sorted(ext_table.items(), key=lambda x: -x[1]):
        L.append(f"| {ngr} | {n} | {'да' if ngr in mapping_ids else 'НЕТ'} "
                 f"| {KNOWN_STALE.get(ngr, '')} |")

    L.append("\n## Выборка 30 ссылок: спан-дисциплина (R06-R08)\n")
    L.append(f"Помечено эвристиками: **{n_flagged}/30** (каждую смотреть глазами, "
             "эвристика - не вердикт)\n")
    for i, t, fl, sn in sample_rows:
        L.append(f"- №{i} {('⚠ ' + ','.join(fl)) if fl else 'ok'} | {t!r}")
        if fl:
            L += ["```", sn, "```"]
    (al.AUDIT_OUT / f"03_links_{slug}.md").write_text(
        "\n".join(L) + "\n", encoding="utf-8")
    return slug, stats, nested, double, n_flagged, ext_table


def main():
    cj = json.loads((al.CONFIG / "codes.json").read_text(encoding="utf-8"))
    codes_by_id = {v["doc_id"]: k for k, v in cj.items()
                   if isinstance(v, dict) and "doc_id" in v}
    mapping_ids = set(json.loads(
        (al.CONFIG / "npa_mapping.json").read_text(encoding="utf-8")).values())

    slugs = sys.argv[1:] or al.all_slugs()
    rows = []
    glob_ext = {}
    for slug in slugs:
        print(f"... {slug}", flush=True)
        rows.append(audit_doc(slug, codes_by_id, mapping_ids))
        for k, v in rows[-1][5].items():
            glob_ext[k] = glob_ext.get(k, 0) + v

    H = ["# АУДИТ 03 — СВОДКА валидации ссылок", "",
         "| slug | всего | INT ok/wrong/broken | XC ok/wrong/broken | EXT root/#z | "
         "SELF | хром | R15 nested/dbl | спан ⚠/30 |", "|---|---|---|---|---|---|---|---|---|"]
    for slug, s, nested, double, nfl, _ in rows:
        H.append(f"| {slug} | {s['total']} | {s['int_ok']}/{s['int_wrong']}/"
                 f"{s['int_broken']} | {s['xc_ok']}/{s['xc_wrong']}/{s['xc_broken']} "
                 f"| {s['ext_root']}/{s['ext_anchored']} | {s['self_abs']} | {s['chrome']} "
                 f"| {nested}/{double} | {nfl} |")
    H += ["", "## Известные протухшие/особые НГР по корпусу (итог)", ""]
    for ngr, note in KNOWN_STALE.items():
        H.append(f"- {ngr}: **{glob_ext.get(ngr, 0)} ссылок** — {note}")
    (al.AUDIT_OUT / "03_SUMMARY.md").write_text("\n".join(H) + "\n", encoding="utf-8")
    print("\n".join(H))


if __name__ == "__main__":
    main()
