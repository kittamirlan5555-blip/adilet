# -*- coding: utf-8 -*-
"""ANARA R2 Фаза 1: диагностика флагов против _structured (READ-ONLY).

python scripts/audit/r2_01_diag.py
-> data/reports/anara_r2/01_diagnosis.md

Вердикты по канону УПК-раунда: FULL_SPAN (false-positive Word) / PARTIAL /
PLAIN / ABSENT. Ядро спана = жёлтое Анары МИНУС хвостовая пунктуация (; . ,)
и непарная ')'; непарная '(' (notariat #2) допаривается до ')' — канон полной
фразы «...(Налоговый кодекс)». Дубли (контекст+фрагмент) — k-е вхождение.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import auditlib as al

R2 = al.REPORTS / "anara_r2"
SLUGS = ["informatizacii", "notariat", "obrazovanie"]
EXPECTED = {"informatizacii": 20, "notariat": 5, "obrazovanie": 9}

RE_FLAG = re.compile(r"^##\s*(\d+)\.\s*(.*)$")
RE_FRAG = re.compile(r"^\s*-\s*\[(LINKED|plain)\s*\]\s*«(.+?)»\s*$")
RE_NOTE = re.compile(r'<(span|p)\b[^>]*class="note"[^>]*>.*?</\1\s*>', re.I | re.S)

# 1:1 нормализация кавычек/тире (длины не меняются — pos_map жив)
QT = str.maketrans({"«": '"', "»": '"', "“": '"', "”": '"', "„": '"',
                    "–": "-", "—": "-", "−": "-"})


def parse_flags(path):
    flags, cur = [], None
    for line in path.read_text(encoding="utf-8").splitlines():
        m = RE_FLAG.match(line)
        if m:
            cur = {"num": int(m.group(1)), "context": m.group(2).strip(),
                   "frags": []}
            flags.append(cur)
            continue
        m = RE_FRAG.match(line)
        if m and cur is not None:
            cur["frags"].append((m.group(1), m.group(2)))
    return flags


def core_span(frag):
    """Жёлтое -> ядро спана. Возвращает (core, notes:list)."""
    core, notes = frag.strip(), []
    while core and core[-1] in " ;.,":
        notes.append(f"снята хвостовая «{core[-1]}»")
        core = core[:-1]
    if core.endswith(")") and core.count(")") > core.count("("):
        core = core[:-1]
        notes.append("снята непарная «)»")
        while core and core[-1] in " ;.,":
            core = core[:-1]
    if core.count("(") > core.count(")"):
        core += ")"
        notes.append("допарена «)» — канон полной фразы")
    return core, notes


def occurrences(hay, needle):
    out, idx = [], hay.find(needle)
    while idx != -1:
        out.append(idx)
        idx = hay.find(needle, idx + 1)
    return out


def diagnose(rs, re_, contents):
    if any(cs <= rs and re_ <= ce for cs, ce in contents):
        return "FULL_SPAN"
    if any(rs < ce and cs < re_ for cs, ce in contents):
        return "PARTIAL"
    return "PLAIN"


def main():
    L = ["# ANARA R2 — Фаза 1: диагностика флагов (read-only)", "",
         "Канон: _structured. Ядро = жёлтое минус хвостовая пунктуация.", ""]
    grand = {"FULL_SPAN": 0, "PARTIAL": 0, "PLAIN": 0, "ABSENT": 0}
    stop = False
    for slug in SLUGS:
        fpath = R2 / f"anara_r2_flags_{slug}.md"
        flags = parse_flags(fpath)
        nfr = sum(len(f["frags"]) for f in flags)
        assert nfr == EXPECTED[slug], f"{slug}: {nfr} != {EXPECTED[slug]}"

        doc = al.FINAL / f"{slug}_structured.html"
        raw = doc.read_text(encoding="utf-8")
        tm = al.TextMap(raw)
        hay = tm.text.translate(QT)
        contents = [(m.start(2), m.end(2))
                    for m in al.RE_A_PAIR.finditer(raw)]
        notes_rng = [(m.start(), m.end()) for m in RE_NOTE.finditer(raw)]

        L += [f"## {slug} — {len(flags)} флагов", "",
              "| № | статья | ядро спана | вх. | взято | вердикт | сноска | прим. |",
              "|---|---|---|---|---|---|---|---|"]
        seen = {}          # (context, core) -> сколько раз уже встречали
        cnt = {"FULL_SPAN": 0, "PARTIAL": 0, "PLAIN": 0, "ABSENT": 0}
        for f in flags:
            art = f["context"].split(" - ")[0].strip()
            for _kind, frag in f["frags"]:
                core, cnotes = core_span(frag)
                needle = re.sub(r"\s+", " ", core).translate(QT)
                occ = occurrences(hay, needle)
                key = (f["context"], core)
                k = seen.get(key, 0)
                seen[key] = k + 1

                # привязка к статье: каскад полный контекст -> 60 -> 40
                # (60 симв. неоднозначен: ст.11 п.2 и ст.61 п.2 informatizacii
                # начинаются одинаково — флаги 5/16 били в одно вхождение)
                ctx = re.sub(r"\s+", " ", f["context"].split(" - ", 1)[-1]
                             ).translate(QT)
                ctx_pos = (occurrences(hay, ctx) or occurrences(hay, ctx[:60])
                           or occurrences(hay, ctx[:40]))
                cand = occ
                if ctx_pos:
                    near = [o for o in occ
                            if any(c - 50 <= o <= c + 2500 for c in ctx_pos)]
                    cand = near or occ
                if not cand:
                    verdict, in_note, pick = "ABSENT", False, "—"
                else:
                    o = cand[min(k, len(cand) - 1)]
                    s, e = o, o + len(needle)
                    rs, re_ = tm.pos[s], tm.pos[e - 1] + 1
                    verdict = diagnose(rs, re_, contents)
                    in_note = any(a <= rs and re_ <= b for a, b in notes_rng)
                    pick = f"{cand.index(o) + 1 if o in cand else '?'}-е из {len(occ)}"
                cnt[verdict] += 1
                grand[verdict] += 1
                if verdict == "ABSENT":
                    stop = True
                disp = core if len(core) <= 70 else core[:67] + "…"
                L.append(f"| {f['num']} | {art} | «{disp}» | {len(occ)} | {pick} "
                         f"| {verdict} | {'ДА' if in_note else '—'} "
                         f"| {'; '.join(cnotes) or '—'} |")
        L += ["", f"**{slug}:** FULL_SPAN={cnt['FULL_SPAN']} "
              f"PARTIAL={cnt['PARTIAL']} PLAIN={cnt['PLAIN']} "
              f"ABSENT={cnt['ABSENT']}", ""]

    L += ["## ИТОГО", "",
          f"FULL_SPAN (false-positive Word) = {grand['FULL_SPAN']}; "
          f"PARTIAL = {grand['PARTIAL']}; PLAIN = {grand['PLAIN']}; "
          f"ABSENT = {grand['ABSENT']}", ""]
    if stop:
        L.append("**ВНИМАНИЕ: есть ABSENT — фраза не найдена, разбор руками.**")
    out = R2 / "01_diagnosis.md"
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))
    print(f"-> {out}")


if __name__ == "__main__":
    main()
