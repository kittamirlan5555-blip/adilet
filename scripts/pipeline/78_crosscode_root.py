# -*- coding: utf-8 -*-
"""CROSS-CODE -> КОРЕНЬ для НЕсогласуемых якорей (§4/§6/§9). TEXT-INVARIANT.

python scripts/pipeline/78_crosscode_root.py [code ...] [--apply]
  без --apply: инвентаризация (read-only).
  --apply: для каждой cross-code ссылки …/docs/{NGR}#zX на ЦЕЛЬ-кодекс корпуса,
    где якорь zX (а) ОТСУТСТВУЕТ в целевом документе  ИЛИ  (б) резолвится в
    статью с ДРУГИМ номером, чем в тексте ссылки (MISMATCH §4) — снимает #zX,
    оставляя КОРЕНЬ …/docs/{NGR}. Видимый текст не меняется.

Зачем: adilet-исходник несёт cross-ref на ЖИВЫЕ якоря adilet; наша выгрузка
нумерует якоря иначе (§9). Пока цель не входила в корпус, сверить было нечем;
как только кодекс добавлен — такие ссылки или висят, или ведут на чужую статью.
Безопасный дефолт по §4 — КОРЕНЬ (не зависит от схемы нумерации).
Якоря-НЕ-статьи (глава/подпункт, резолвятся в элемент) и внешние НЕ-корпус
цели НЕ трогаем. Гейт: nows(get_text) ДО==ПОСЛЕ.
"""
import importlib.util
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import paths  # noqa: E402
from bs4 import BeautifulSoup  # noqa: E402

# переиспользуем резолв-логику аудита 75 (article_candidates / range_first_ok / ...)
_spec = importlib.util.spec_from_file_location(
    "cc75", paths.ROOT / "scripts" / "audit" / "75_crosscode_verify.py")
cc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cc)

FINAL = paths.FINAL


def anchors_of(code, cache):
    if code in cache:
        return cache[code]
    p = FINAL / f"{code}_structured.html"
    if not p.exists():
        p = FINAL / f"{code}_ready.html"
    s = set()
    if p.exists():
        soup = BeautifulSoup(p.read_text(encoding="utf-8"), "html.parser")
        for t in soup.find_all(attrs={"id": True}):
            s.add(t["id"])
        for t in soup.find_all("a", attrs={"name": True}):
            s.add(t["name"])
    cache[code] = s
    return s


def _nows(soup):
    return "".join(soup.get_text().split())


def process(code, own_doc, d2c, anchorset_cache, revcache, apply_mode):
    forms = [f for f in (FINAL / f"{code}_structured.html",
                         FINAL / f"{code}_ready.html") if f.exists()]
    total_missing = total_mismatch = 0
    samples = []
    for p in forms:
        soup = BeautifulSoup(p.read_text(encoding="utf-8"), "html.parser")
        before = _nows(soup)
        n_miss = n_mis = 0
        for a in soup.find_all("a", href=True):
            m = cc.RE_HREF.search(a["href"])
            if not m:
                continue
            tgt_doc, anchor = m.group(1), m.group(2)
            if tgt_doc == own_doc:
                continue                       # само-ссылки — забота 68
            tgt_code = d2c.get(tgt_doc)
            if tgt_code is None:
                continue                       # внешний не-корпус: сверить нечем
            reason = None
            if anchor not in anchors_of(tgt_code, anchorset_cache):
                reason = "MISSING"
            else:
                if tgt_code not in revcache:
                    revcache[tgt_code] = cc.load_reverse_map(tgt_code)
                resolved = revcache[tgt_code].get(anchor)
                cands = cc.article_candidates(a)
                if (resolved is not None and cands
                        and str(resolved) not in {str(x) for x in cands}
                        and not cc.range_first_ok(resolved, cands)
                        and (code, tgt_code, anchor) not in cc.DEPLOY_PENDING):
                    reason = "MISMATCH"
            if reason:
                if len(samples) < 12:
                    samples.append(f"{code}->{tgt_code}#{anchor} [{reason}] "
                                   f"{a.get_text(' ', strip=True)[:30]!r}")
                if reason == "MISSING":
                    n_miss += 1
                else:
                    n_mis += 1
                if apply_mode:
                    a["href"] = a["href"].split("#", 1)[0]   # -> корень
        total_missing += n_miss
        total_mismatch += n_mis
        if apply_mode and (n_miss or n_mis):
            after = _nows(BeautifulSoup(str(soup), "html.parser"))
            if before != after:
                sys.exit(f"STOP: nows-сдвиг в {p.name} — отказ записи")
            p.write_text(str(soup), encoding="utf-8")
    return total_missing, total_mismatch, samples


def main():
    apply_mode = "--apply" in sys.argv
    codes = [a for a in sys.argv[1:] if not a.startswith("--")]
    d2c = cc.docid_to_code()
    code_doc = {c: d for d, c in d2c.items()}
    if not codes:
        codes = sorted(code_doc)
    anchorset_cache, revcache = {}, {}
    gm = gx = 0
    all_samples = []
    for code in codes:
        own = code_doc.get(code)
        if own is None:
            continue
        miss, mis, samples = process(code, own, d2c, anchorset_cache,
                                     revcache, apply_mode)
        if miss or mis:
            print(f"  {code:16} MISSING->root={miss}  MISMATCH->root={mis}")
            all_samples += samples
        gm += miss
        gx += mis
    print(f"\nИТОГО cross-code -> КОРЕНЬ: MISSING={gm}  MISMATCH={gx}  "
          f"({'ПРИМЕНЕНО' if apply_mode else 'инвентаризация'})")
    for s in all_samples[:20]:
        print("   ", s)


if __name__ == "__main__":
    main()
