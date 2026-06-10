# -*- coding: utf-8 -*-
"""АУДИТ ФАЗА 2: структурная валидация под векторную БД. READ-ONLY.

python scripts/audit/a02_structure.py [slug ...]
-> data/reports/audit/02_structure_{slug}.md + 02_SUMMARY.md

Проверки на каждый документ, обе формы:
  2.1 {статьи в разметке} vs {article_map} vs {якоря} (R12)
  2.2 машинная извлекаемость 20 случайных статей + адресуемость подпунктов (R13)
  2.3 последовательность статей vs data/source (R14): пропуски/задвоения/слияния
  2.4 text-invariance structured==ready и final vs source (R11)
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import re
import auditlib as al


def load_map(slug):
    p = al.MAPS / f"article_map_{slug}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def seq_diff(src_seq, fin_seq):
    """Выравнивание последовательностей номеров статей source vs final."""
    import difflib
    sm = difflib.SequenceMatcher(a=src_seq, b=fin_seq, autojunk=False)
    missing, extra = [], []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag in ("delete", "replace"):
            missing += src_seq[i1:i2]
        if tag in ("insert", "replace"):
            extra += fin_seq[j1:j2]
    return missing, extra


def invariance(tm_a, tm_b, scope_b_to_a=False):
    """Сравнение по КАНОНИЧЕСКОМУ инварианту §6.1: текст БЕЗ пробелов вообще
    (''.join(get_text().split())). scope_b_to_a: вырезать из b (source) диапазон,
    соответствующий a (final), по первым/последним 160 символам a."""
    A, B = tm_a.nows, tm_b.nows
    off = 0
    if scope_b_to_a and len(A) >= 320:
        i0 = B.find(A[:160])
        i1 = B.rfind(A[-160:])
        if i0 == -1 or i1 == -1 or i1 + 160 <= i0:
            return ("UNSCOPEABLE", None, None, None)
        off = i0
        B = B[i0:i1 + 160]
    if A == B:
        return ("PASS", None, None, None)
    n = min(len(A), len(B))
    k = next((i for i in range(n) if A[i] != B[i]), n)
    return ("FAIL", k,
            (A[max(0, k - 60):k + 60], tm_a.raw_at_nows(k)),
            (B[max(0, k - 60):k + 60], tm_b.raw_at_nows(k + off)))


def article_diff(fraw, fclusters, sraw):
    """Постатейный дифф final vs source (тексты статей без пробелов, §6.1).
    -> ([(num, k, (текст, raw), (текст, raw))], число общих статей)"""
    scl = al.article_clusters(sraw)

    def segs(raw, cl):
        out = {}
        for i, (pos, num, _anc, _fam) in enumerate(cl):
            end = cl[i + 1][0] if i + 1 < len(cl) else len(raw)
            out.setdefault(num, []).append((pos, end))
        return out

    fs, ss = segs(fraw, fclusters), segs(sraw, scl)
    common = sorted(set(fs) & set(ss),
                    key=lambda x: [int(p) for p in x.split("-")])
    # хвост сегмента обрезаем на заголовке главы/раздела: при расщеплении
    # слитых заголовков (ГК 147) границы сегментов final и source различаются
    # на текст «Глава N. …» — он не часть статьи
    RE_CHAPTER_TAIL = re.compile(r"(?:Глава|Параграф|Раздел|Подраздел)\d+(?:-\d+)*\.")

    def cut_tail(nows):
        m = RE_CHAPTER_TAIL.search(nows)
        return nows[:m.start()] if m else nows

    diffs = []
    for num in common:
        tmF = al.TextMap("".join(fraw[a:b] for a, b in fs[num]), strip_labels=True)
        tmS = al.TextMap("".join(sraw[a:b] for a, b in ss[num]))
        ft, st_ = cut_tail(tmF.nows), cut_tail(tmS.nows)
        if ft == st_:
            continue
        n = min(len(ft), len(st_))
        k = next((i for i in range(n) if ft[i] != st_[i]), n)
        diffs.append((num, k,
                      (ft[max(0, k - 60):k + 60], tmF.raw_at_nows(k)),
                      (st_[max(0, k - 60):k + 60], tmS.raw_at_nows(k))))
    return diffs, len(common)


def audit_doc(slug):
    files = al.doc_files(slug)
    src = al.source_file(slug)
    amap = load_map(slug)
    L = [f"# АУДИТ 02 — структура: {slug}", "",
         "Воспроизводимость: `PYTHONIOENCODING=utf-8 python scripts/audit/a02_structure.py "
         f"{slug}`", ""]
    S = {"slug": slug}
    raws = {f: p.read_text(encoding="utf-8") for f, p in files.items()}
    tms = {f: al.TextMap(r) for f, r in raws.items()}
    clusters = {f: al.article_clusters(r) for f, r in raws.items()}

    # ---------- 2.1 множества ----------
    L.append("## 2.1 Статьи: разметка vs article_map vs якоря (R12)\n")
    for f, cl in clusters.items():
        nums = [c[1] for c in cl]
        uniq = set(nums)
        dup = sorted({n for n in uniq if nums.count(n) > 1},
                     key=lambda x: [int(p) for p in x.split("-")])
        no_anchor = [c for c in cl if c[2] is None]
        fams = {}
        for c in cl:
            for fam in c[3]:
                fams[fam] = fams.get(fam, 0) + 1
        L.append(f"### {slug}_{f}.html")
        L.append(f"- статей в разметке: **{len(cl)}** (уникальных номеров {len(uniq)}); "
                 f"семейства разметки: {fams}")
        L.append(f"- задвоенные номера: {dup if dup else '0'}")
        L.append(f"- статей БЕЗ якоря: **{len(no_anchor)}**"
                 + (f" — {[c[1] for c in no_anchor][:15]}" if no_anchor else ""))
        if amap is not None:
            m = set(amap.keys())
            only_text = sorted(uniq - m, key=lambda x: [int(p) for p in x.split("-")])
            only_map = sorted(m - uniq, key=lambda x: [int(p) for p in x.split("-")])
            L.append(f"- article_map: {len(m)} записей; в разметке но НЕ в карте: "
                     f"**{len(only_text)}** {only_text[:15]}; в карте но НЕ в разметке: "
                     f"**{len(only_map)}** {only_map[:15]}")
            ids = al.ids_of(raws[f])
            bad_anchor = sorted(k for k, v in amap.items() if v not in ids)
            L.append(f"- якорей карты, отсутствующих в файле: **{len(bad_anchor)}** "
                     f"{bad_anchor[:15]}")
            S[f"sets_{f}"] = (len(only_text), len(only_map), len(bad_anchor), len(dup),
                              len(no_anchor))
        else:
            L.append("- article_map: **НЕТ ФАЙЛА** -> R12 FAIL (непроверяемо)")
            S[f"sets_{f}"] = None
        L.append("")

    # ---------- 2.2 извлекаемость ----------
    L.append("## 2.2 Машинная извлекаемость (R13): 20 случайных статей\n")
    f = "ready" if "ready" in raws else "structured"
    raw, cl = raws[f], clusters[f]
    r = al.rng(slug)
    sample = sorted(r.sample(range(len(cl)), min(20, len(cl))))
    ok = fail = 0
    sub_addr = 0
    rows = ["| статья | якорь | симв. | якорей внутри | нумерация пунктов |",
            "|---|---|---|---|---|"]
    examples = []
    for idx in sample:
        pos, num, anc, _ = cl[idx]
        end = cl[idx + 1][0] if idx + 1 < len(cl) else len(raw)
        seg = raw[pos:end]
        txt = al.strip_tags(seg)
        good = txt.startswith(f"Статья {num}") and len(txt) > 40
        ok += good
        fail += not good
        inner_anchors = len(al.RE_IDS.findall(seg)) - (1 if anc else 0)
        has_numbering = bool(re.search(r"(?:\s|^)\d+(?:-\d+)?[.)]\s", txt[:4000]))
        sub_addr += (inner_anchors > 0)
        rows.append(f"| {num} | {anc or '—'} | {len(txt):,} | {inner_anchors} | "
                    f"{'да' if has_numbering else 'нет'} |")
        if len(examples) < 2:
            examples.append(f"**Статья {num}** (якорь `{anc}`, {f}):\n```\n"
                            f"{txt[:300]}…\n```")
    L.append(f"Форма: `{slug}_{f}.html`; алгоритм: от позиции маркера статьи до "
             f"следующего маркера. Извлеклись с верным заголовком: **{ok}/{len(sample)}**; "
             f"статей с якорями внутри (адресуемые пункты): **{sub_addr}/{len(sample)}**.")
    L += rows + [""] + examples + [""]
    S["extract"] = (ok, len(sample), sub_addr)

    # ---------- 2.3 последовательность vs source ----------
    L.append("## 2.3 Последовательность статей vs source (R14)\n")
    if src is None:
        L.append("**FAIL (непроверяемо): source-файла нет.**\n")
        S["seq"] = None
    else:
        sraw = src.read_text(encoding="utf-8")
        scl = al.article_clusters(sraw)
        sseq = [c[1] for c in scl]
        S["src_articles"] = len(scl)
        for f2 in raws:
            fseq = [c[1] for c in clusters[f2]]
            missing, extra = seq_diff(sseq, fseq)
            merged = []
            tmf = tms[f2]
            for num in missing:
                if re.search(rf"Статья {re.escape(num)}[.\s]", tmf.text):
                    merged.append(num)
            L.append(f"### {slug}_{f2}.html: source={len(sseq)} статей, final={len(fseq)}")
            L.append(f"- в source, НЕТ маркера в final: **{len(missing)}** "
                     f"{missing[:15]}{' …' if len(missing) > 15 else ''}")
            if merged:
                L.append(f"  - из них ТЕКСТ есть в final (вероятно слияние/потеря "
                         f"заголовка, прецедент zhilishniy): **{len(merged)}** {merged[:10]}")
            L.append(f"- в final, НЕТ в source: **{len(extra)}** {extra[:15]}")
            S[f"seq_{f2}"] = (len(missing), len(extra), len(merged))
        L.append("")

    # ---------- 2.4 text-invariance ----------
    L.append("## 2.4 text-invariance (R11)\n")
    L.append("Инвариант §6.1: текст без тегов и БЕЗ пробелов; `*-label`-спаны "
             "структуризатора (дубль заголовков глав) исключены из сравнения как "
             "известная декорация.\n")
    tms_n = {f: al.TextMap(r, strip_labels=True) for f, r in raws.items()}
    if "ready" in tms_n and "structured" in tms_n:
        st, k, a, b = invariance(tms_n["ready"], tms_n["structured"])
        S["inv_forms"] = st
        L.append(f"- structured vs ready: **{st}**" + ("" if st == "PASS" else
                 f" (первое расхождение @{k})"))
        if st == "FAIL":
            L += ["", "ready (текст / сырой HTML):", "```", a[0], "```", "```", a[1], "```",
                  "structured (текст / сырой HTML):", "```", b[0], "```", "```", b[1], "```"]
    if src is not None:
        f3 = "structured" if "structured" in raws else "ready"
        diffs, n_common = article_diff(raws[f3], clusters[f3],
                                       src.read_text(encoding="utf-8"))
        S["inv_source"] = ("PASS", 0) if not diffs else ("FAIL", len(diffs))
        L.append(f"- {f3} vs source, ПОСТАТЕЙНОЕ сравнение ({n_common} общих статей): "
                 f"расходятся **{len(diffs)}**"
                 + ("" if not diffs else " — " + ", ".join(d[0] for d in diffs[:15])))
        for num, k, sn_f, sn_s in diffs[:8]:
            L += ["", f"### Статья {num} (final vs source), расхождение @{k}",
                  "final (текст / сырой HTML):", "```", sn_f[0], "```", "```", sn_f[1], "```",
                  "source (текст / сырой HTML):", "```", sn_s[0], "```", "```", sn_s[1], "```"]
    else:
        S["inv_source"] = None
        L.append("- vs source: **FAIL (непроверяемо)** — source отсутствует")

    al.AUDIT_OUT.mkdir(parents=True, exist_ok=True)
    (al.AUDIT_OUT / f"02_structure_{slug}.md").write_text(
        "\n".join(L) + "\n", encoding="utf-8")
    return S


def main():
    slugs = sys.argv[1:] or al.all_slugs()
    rows = []
    for slug in slugs:
        print(f"... {slug}", flush=True)
        rows.append(audit_doc(slug))

    H = ["# АУДИТ 02 — СВОДКА структурной валидации", "",
         "Детали: 02_structure_{slug}.md. Генератор: scripts/audit/a02_structure.py", "",
         "| slug | 2.1 разметка-карта-якоря (тек/карта/якорь/дубль/без-якоря) | "
         "2.2 извлечение | 2.3 vs source (missing/extra/merged) | 2.4 формы | 2.4 source |",
         "|---|---|---|---|---|---|"]
    for S in rows:
        f = "ready" if f"sets_ready" in S and S.get("sets_ready") is not None else "structured"
        sets = S.get(f"sets_{f}")
        sets_s = ("/".join(map(str, sets)) if sets else "**нет карты**")
        seq = S.get(f"seq_{f}") or S.get("seq_structured")
        seq_s = "/".join(map(str, seq)) if seq else "**нет source**"
        ok, tot, sub = S["extract"]
        isrc = S.get("inv_source")
        isrc_s = ("**нет source**" if isrc is None
                  else (f"FAIL: {isrc[1]} статей" if isrc[0] == "FAIL" else "PASS"))
        H.append(f"| {S['slug']} | {sets_s} | {ok}/{tot} (подпункт-якоря {sub}/{tot}) "
                 f"| {seq_s} | {S.get('inv_forms', '—')} | {isrc_s} |")
    (al.AUDIT_OUT / "02_SUMMARY.md").write_text("\n".join(H) + "\n", encoding="utf-8")
    print("\n".join(H))


if __name__ == "__main__":
    main()
