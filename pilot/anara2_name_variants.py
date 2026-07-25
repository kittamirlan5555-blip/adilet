# -*- coding: utf-8 -*-
"""anara2 BLOCK 3: матч имён устойчивый к вариантам
(«...и юридической помощи» vs «...и квалифицированной юридической помощи», опечатки
«в Республик{и/е}», склонения). Только СВЕРЕННЫЕ варианты → маппинг; сомнительные →
unresolved с частотами. WRONG=0: НЕ мапим на repealed, НЕ мапим при смене предмета.

VERIFIED (авто-добавляем ключ `"cited"` → NGR) требует ВСЕХ условий:
  - целевой акт РЕЕСТРА active (repealed=False);
  - difflib ratio(norm) >= 0.90;
  - разница токенов — только «filler» (квалифицированной / опечатка Республик{и/е} /
    склонение), первый содержательный токен-предмет совпадает;
  - однозначный лучший матч (второй кандидат заметно хуже).
Всё прочее (repealed-цель, низкий ratio, частичное имя, неоднозначность) → UNRESOLVED.
Запуск без --apply: только показать. С --apply: записать сверенные в npa_mapping.
"""
import io, sys, json, re, difflib
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from pathlib import Path
from collections import Counter
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
APPLY = "--apply" in sys.argv


def clean(t):
    t = re.sub(r"\s*-\s*ИПС.*$", "", t or "")
    return re.sub(r"\s+", " ", t).strip().strip('«»"""')


def norm(s):
    s = s.lower().replace("ё", "е")
    s = re.sub(r"[«»\"\"'.,]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


FILLER = {"квалифицированной", "республике", "республики", "казахстан", "в", "и"}


def tokens(s):
    return [w for w in norm(s).split() if w]


def only_filler_diff(a, b):
    """Разница множеств токенов — только filler-слова?"""
    sa, sb = set(tokens(a)), set(tokens(b))
    diff = sa.symmetric_difference(sb)
    return all(w in FILLER for w in diff)


def subject_token(s):
    """Первый содержательный токен после «о/об/о» (предмет закона)."""
    ts = [w for w in tokens(s) if w not in ("о", "об", "о")]
    return ts[0] if ts else ""


def main():
    m = json.loads((ROOT / "maps/npa_mapping.json").read_text(encoding="utf-8"))
    reg = json.loads((ROOT / "maps/corpus_registry.json").read_text(encoding="utf-8"))
    # активные акты реестра: имя-> ngr (полный титул)
    active = []
    for r in reg:
        ti = clean(r.get("title", ""))
        if r.get("repealed"):
            continue
        # только «настоящие» законы-названия, не «О внесении изменений...»
        if ti.lower().startswith(("о внесении", "о признании утратив", "о ратификац",
                                  "о присоединении")):
            continue
        if len(ti) < 6:
            continue
        active.append((ti, r["ngr"]))

    key_names = set()
    for k in m:
        for nm in re.findall(r'"([^"]+)"', k):
            key_names.add(nm)

    # цитаты из корпуса
    cite = Counter()
    pat = re.compile(r'(Закон\w*|Кодекс\w*)[^"«]{0,40}[«"]([^»"<]{6,90})[»"]')
    for f in sorted(ROOT.glob("final/*_ready.html")):
        txt = re.sub(r"\s+", " ", BeautifulSoup(
            f.read_text(encoding="utf-8", errors="replace"), "html.parser").get_text(" "))
        for mo in pat.finditer(txt):
            nm = mo.group(2).strip()
            if nm and nm[0].isupper() and "href" not in nm:
                cite[nm] += 1

    unmatched = {nm: c for nm, c in cite.items() if nm not in key_names}

    verified, unresolved = [], []
    for nm, cnt in sorted(unmatched.items(), key=lambda x: -x[1]):
        cands = sorted(((difflib.SequenceMatcher(None, norm(nm), norm(ti)).ratio(), ti, ngr)
                        for ti, ngr in active), reverse=True)
        if not cands:
            unresolved.append((nm, cnt, "нет кандидатов", None, None)); continue
        r1, ti1, ngr1 = cands[0]
        r2 = cands[1][0] if len(cands) > 1 else 0.0
        ok = (r1 >= 0.90 and only_filler_diff(nm, ti1)
              and subject_token(nm) == subject_token(ti1) and (r1 - r2) >= 0.02)
        if ok:
            verified.append((nm, cnt, ti1, ngr1, round(r1, 3)))
        else:
            reason = (f"ratio={r1:.2f}" +
                      ("" if r1 >= 0.90 else " <0.90") +
                      ("" if only_filler_diff(nm, ti1) else " +нефиллер-разница") +
                      ("" if subject_token(nm) == subject_token(ti1) else " предмет≠"))
            unresolved.append((nm, cnt, reason, ti1, ngr1))

    print(f"unmatched цитат: {len(unmatched)}  | VERIFIED вариантов: {len(verified)}  "
          f"| UNRESOLVED: {len(unresolved)}\n")
    print("=== VERIFIED (в маппинг) ===")
    for nm, cnt, ti, ngr, r in verified:
        print(f"  {cnt:3d}× «{nm}»\n        -> {ngr}  «{ti}»  (ratio {r})")
    print("\n=== UNRESOLVED (top 25, с частотами) ===")
    for nm, cnt, reason, ti, ngr in unresolved[:25]:
        best = f" ~ «{ti[:50]}» {ngr}" if ti else ""
        print(f"  {cnt:3d}× «{nm[:60]}»  [{reason}]{best}")

    if APPLY:
        for nm, cnt, ti, ngr, r in verified:
            m[f'"{nm}"'] = ngr
        (ROOT / "maps/npa_mapping.json").write_text(
            json.dumps(m, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"\n[APPLIED] добавлено ключей: {len(verified)} | маппинг теперь {len(m)}")

    (ROOT / "reports/anara2_name_variants.json").write_text(json.dumps(
        {"verified": [dict(cited=nm, cnt=c, target_title=ti, ngr=g, ratio=r)
                      for nm, c, ti, g, r in verified],
         "unresolved": [dict(cited=nm, cnt=c, reason=rs, best_title=ti, best_ngr=g)
                        for nm, c, rs, ti, g in unresolved]},
        ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
