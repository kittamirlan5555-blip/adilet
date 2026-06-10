# -*- coding: utf-8 -*-
"""R3 БЛОК 1, шаг 1: полный дамп G6-расхождений по 8 документам. READ-ONLY.

python scripts/audit/r3_01_g6_dump.py
-> reports/r3/g6_cases.json + g6_cases.md

Логика G6 (точно как в 71_gates): пара = (canon-href, схлопнутый текст <a>);
расхождение = пара, существующая только в одной форме. Здесь расхождения
СПАРИВАЮТСЯ в кейсы:
  SPAN     — один href, разный текст (обычно расширение спана в одной форме);
  RETARGET — один текст, разный href;
  ONLY     — пара без напарника: ссылка есть в одной форме; в другой тот же
             текст либо плэйн (UNWRAPPED), либо отсутствует (NO_TEXT).
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import paths

HOST = "https://adilet.zan.kz/rus/docs/"
RE_A_PAIR = re.compile(r'<a\b[^>]*href="([^"]*)"[^>]*>(.*?)</a\s*>', re.I | re.S)
RE_TAGS = re.compile(r"<[^>]+>")

DOCS = ["grazhdanskiy_osob", "grazhdanskiy", "socialnyy", "nalog", "appk",
        "predprinimatel", "koap", "byudzhet"]


def own_doc_id(doc):
    cj = json.loads(paths.CODES_JSON.read_text(encoding="utf-8"))
    v = cj.get(doc)
    return v.get("doc_id") if isinstance(v, dict) else None


def canon_pairs(raw, own):
    pairs = Counter()
    for href, inner in RE_A_PAIR.findall(raw):
        h = href.strip()
        if own:
            if h.startswith(HOST + own + "#"):
                h = "#" + h.split("#", 1)[1]
            elif h == HOST + own:
                h = "@SELF_ROOT"
        t = re.sub(r"\s+", " ", RE_TAGS.sub("", inner)).strip()
        pairs[(h, t)] += 1
    return pairs


def plain_text(raw):
    return re.sub(r"\s+", " ", RE_TAGS.sub(" ", raw))


def main():
    out_dir = paths.REPORTS / "r3"
    out_dir.mkdir(parents=True, exist_ok=True)
    all_cases = {}
    md = ["# R3 БЛОК 1: G6-кейсы (read-only дамп)", ""]

    for doc in DOCS:
        own = own_doc_id(doc)
        fs = paths.FINAL / f"{doc}_structured.html"
        fr = paths.FINAL / f"{doc}_ready.html"
        raw_s = fs.read_text(encoding="utf-8")
        raw_r = fr.read_text(encoding="utf-8")
        ps, pr = canon_pairs(raw_s, own), canon_pairs(raw_r, own)
        only_s = {p for p in ps if p not in pr}
        only_r = {p for p in pr if p not in ps}

        cases = []
        used_s, used_r = set(), set()

        # RETARGET: один текст в обеих, href разные
        ts = {}
        for h, t in only_s:
            ts.setdefault(t, []).append(h)
        for h, t in sorted(only_r):
            if t in ts and (h, t) not in used_r:
                for h2 in ts[t]:
                    if (h2, t) in used_s:
                        continue
                    cases.append({"class": "RETARGET", "text": t,
                                  "href_structured": h2, "href_ready": h,
                                  "n_s": ps[(h2, t)], "n_r": pr[(h, t)]})
                    used_s.add((h2, t))
                    used_r.add((h, t))
                    break

        # SPAN: один href в обеих, текст разный (берём пары с вложением текста)
        hs = {}
        for h, t in only_s:
            if (h, t) not in used_s:
                hs.setdefault(h, []).append(t)
        for h, t in sorted(only_r):
            if (h, t) in used_r:
                continue
            for t2 in hs.get(h, []):
                if (h, t2) in used_s:
                    continue
                if t in t2 or t2 in t:
                    cases.append({"class": "SPAN", "href": h,
                                  "text_structured": t2, "text_ready": t,
                                  "n_s": ps[(h, t2)], "n_r": pr[(h, t)]})
                    used_s.add((h, t2))
                    used_r.add((h, t))
                    break

        # ONLY: остаток — без напарника
        pt_s, pt_r = plain_text(raw_s), plain_text(raw_r)
        for src, only, used, other_pt in (("structured", only_s, used_s, pt_r),
                                          ("ready", only_r, used_r, pt_s)):
            for h, t in sorted(only):
                if (h, t) in used:
                    continue
                sub = "UNWRAPPED" if t and t in other_pt else "NO_TEXT"
                cases.append({"class": f"ONLY_{src}", "sub": sub,
                              "href": h, "text": t,
                              "n": (ps if src == "structured" else pr)[(h, t)]})

        all_cases[doc] = cases
        by_class = Counter(c["class"] + ("/" + c["sub"] if "sub" in c else "")
                           for c in cases)
        md.append(f"## {doc} — пар-расхождений {len(only_s) + len(only_r)}, "
                  f"кейсов {len(cases)}: "
                  + ", ".join(f"{k}={v}" for k, v in sorted(by_class.items())))
        md.append("")
        for c in cases:
            if c["class"] == "RETARGET":
                md.append(f"- RETARGET «{c['text'][:80]}»: structured={c['href_structured']} "
                          f"(×{c['n_s']}) vs ready={c['href_ready']} (×{c['n_r']})")
            elif c["class"] == "SPAN":
                md.append(f"- SPAN {c['href']}: structured=«{c['text_structured'][:70]}» "
                          f"(×{c['n_s']}) vs ready=«{c['text_ready'][:70]}» (×{c['n_r']})")
            else:
                md.append(f"- {c['class']}/{c['sub']} {c['href']} «{c['text'][:80]}» ×{c['n']}")
        md.append("")
        print(f"{doc:20} пар={len(only_s)+len(only_r):>4} кейсов={len(cases):>4}  "
              + ", ".join(f"{k}={v}" for k, v in sorted(by_class.items())))

    (out_dir / "g6_cases.json").write_text(
        json.dumps(all_cases, ensure_ascii=False, indent=1), encoding="utf-8")
    (out_dir / "g6_cases.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"\n-> {out_dir / 'g6_cases.json'}\n-> {out_dir / 'g6_cases.md'}")


if __name__ == "__main__":
    main()
