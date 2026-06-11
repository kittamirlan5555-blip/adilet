# -*- coding: utf-8 -*-
"""CROSS-CODE СВЕРКА ЯКОРЕЙ (§4 + §6.3 CLAUDE.md). READ-ONLY.

Для каждой ссылки на КОНКРЕТНУЮ СТАТЬЮ другого кодекса вида
`…/docs/{НГР}#z{X}` проверяет, что якорь `z{X}` в ЦЕЛЕВОМ кодексе реально
указывает на статью с ТЕМ ЖЕ номером, что упомянут в тексте ссылки.

Карта «статья -> якорь» берётся из `data/maps/article_map_{целевой}.json`
(+ subpoint map). Якорь резолвится обратно: `z{X} -> номер статьи`. Если номер
из текста ссылки != номер из карты -> MISMATCH (та самая опасная мислинка из §4:
«206 -> чужая статья»).

⚠️ ВАЖНО (§4/§9): даже статус OK означает лишь, что ссылка согласована с НАШЕЙ
картой. Якоря наших `_ready.html` НЕ совпадают с живым adilet. Article-level
cross-code КОРРЕКТЕН ТОЛЬКО при модели деплоя A (на adilet кладут наши файлы).
Иначе такие ссылки надо переводить на КОРЕНЬ. Скрипт это не решает — помечает.

НИЧЕГО НЕ МЕНЯЕТ.

Запуск:
  python 75_crosscode_verify.py [code ...] [--strict] [--self]
    без аргументов — все data/final/*_ready.html (+ *_structured.html).
    --strict — exit 1, если есть MISMATCH.
    --self   — также проверять само-ссылки в абсолютной форме (doc_id == свой).
"""
import re
import sys
import json
from pathlib import Path
from collections import defaultdict
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import paths

ROOT = paths.ROOT
FINAL = paths.FINAL
MAPS = paths.MAPS
CONFIG = paths.MAPS      # config/ слит в maps/ (Фаза A)
REPORTS = paths.GATES    # машинные гейт-отчёты (дерево v2)

RE_HREF = re.compile(r"/docs/([A-Za-z0-9_]+)#(z[\w-]+)")
# «стат[ье]», не «стать»: иначе «статей N» терял кандидата (аудит 2026-06-10)
RE_ART_IN_TEXT = re.compile(r"стат[ье]\w*\s+(\d+(?:-\d+)?)", re.I)


def docid_to_code():
    cj = json.loads((CONFIG / "codes.json").read_text(encoding="utf-8"))
    return {v["doc_id"]: k for k, v in cj.items()
            if isinstance(v, dict) and "doc_id" in v}


def load_reverse_map(code):
    """anchor -> номер статьи, из article_map (+ subpoint_map, по 1-му сегменту)."""
    rev = {}
    amp = MAPS / f"article_map_{code}.json"
    if amp.exists():
        for art, anc in json.loads(amp.read_text(encoding="utf-8")).items():
            rev.setdefault(anc, art)
    smp = MAPS / f"subpoint_map_{code}.json"
    if smp.exists():
        for key, anc in json.loads(smp.read_text(encoding="utf-8")).items():
            art = str(key).split("_", 1)[0]          # '3_1' -> статья 3
            rev.setdefault(anc, art)
    return rev


def files_for(codes):
    if codes:
        out = []
        for c in codes:
            p = FINAL / f"{c}_ready.html"
            if not p.exists():
                p = FINAL / f"{c}_structured.html"
            if p.exists():
                out.append((c, p))
        return out
    out = []
    for p in sorted(FINAL.glob("*_ready.html")):
        out.append((p.name[:-len("_ready.html")], p))
    # законы — только structured
    have = {c for c, _ in out}
    for p in sorted(FINAL.glob("*_structured.html")):
        c = p.name[:-len("_structured.html")]
        if c not in have:
            out.append((c, p))
    return out


RE_BARE_NUM = re.compile(r"^\(?(\d+(?:-\d+)?)\)?$")


# §9 НЕ РЕШЁН (модель деплоя якорей): известные кейсы, где якорь источника
# совпадает со схемой ЖИВОГО adilet, но не с нашей картой. НЕ чинить до
# решения шефа (правка предрешала бы ответ). Счётчик DEPLOY_PENDING, не гейт.
DEPLOY_PENDING = {
    # appk «статьи 4 Закона РК "О гос. услугах"» -> z4 (на живом adilet это
    # ст.4; по нашей карте gosuslugi z4 = ст.2). Живой пример §9 для шефа.
    ("appk", "gosuslugi", "z4"),
}


def range_first_ok(resolved, cands):
    """Класс RANGE-FIRST (прецеденты «статьями 249-257», ГК «статей 151-152»):
    диапазон статей ведёт на ЗАГОЛОВОК ПЕРВОЙ статьи диапазона — сложившийся
    корректный стиль, не мислинк. Кандидат «A-B» — диапазон, если B > A
    (у суффиксных статей наоборот: «151-1» -> B=1 < A=151). OK, когда якорь
    резолвится ровно в A."""
    for c in cands:
        m = re.match(r"^(\d+)-(\d+)$", str(c))
        if m and int(m.group(2)) > int(m.group(1)) \
                and str(resolved) == m.group(1):
            return True
    return False


def article_candidates(a):
    """Множество КАНДИДАТ-номеров статьи для ссылки a.

    Полно-спановый <a> может оборачивать как «статьёй 258», так и просто «258»
    (в списке «статьями 437 и 438» каждый номер — отдельный <a>). Поэтому
    собираем ВСЕ правдоподобные номера: голый номер самого <a> + все «статья N»
    из текста <a> + из предыдущего соседа (контекст). MISMATCH срабатывает только
    если якорь резолвится в статью, которой НЕТ среди кандидатов (истинная
    мислинка §4: «206 -> чужая статья», номер которой нигде не упомянут)."""
    cands = set()
    t = a.get_text(" ").strip()
    m = RE_BARE_NUM.match(t)
    if m:
        cands.add(m.group(1))
    cands.update(RE_ART_IN_TEXT.findall(t))
    prev = a.previous_sibling
    ctx = (str(prev)[-80:] if prev else "") + " " + t
    cands.update(RE_ART_IN_TEXT.findall(ctx))
    # ВПЕРЁД-контекст (R6 Блок 3): в «пунктами 5), 6) … статьи 129 ПК» терминатор
    # «статьи N» стоит ПОСЛЕ перечня — без него голые номера пунктов давали
    # ложный MISMATCH при обогащённых subpoint-картах.
    fwd, node, budget = "", a.next_sibling, 200
    while node is not None and budget > 0:
        s = node.get_text(" ") if hasattr(node, "get_text") else str(node)
        fwd += " " + s
        budget -= len(s)
        node = node.next_sibling
    cands.update(RE_ART_IN_TEXT.findall(fwd[:240]))
    return cands


def run(codes, strict, do_self):
    d2c = docid_to_code()
    own_by_file = {}
    cj = json.loads((CONFIG / "codes.json").read_text(encoding="utf-8"))
    code_doc = {k: v["doc_id"] for k, v in cj.items()
                if isinstance(v, dict) and "doc_id" in v}

    rev_cache = {}
    L = []
    P = L.append
    P("=" * 100)
    P("CROSS-CODE СВЕРКА ЯКОРЕЙ (§4/§6.3) — READ-ONLY")
    P("ВНИМАНИЕ: OK = согласовано с НАШЕЙ картой; корректность на adilet зависит")
    P("от модели деплоя (§9). Если деплой != 'наши файлы' — такие ссылки -> КОРЕНЬ.")
    P("=" * 100)

    tot = {"OK": 0, "MISMATCH": 0, "UNRESOLVED": 0, "NO_ART_TEXT": 0, "NO_MAP": 0}
    mismatches = []

    for code, path in files_for(codes):
        self_doc = code_doc.get(code)
        soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
        per = {"OK": 0, "MISMATCH": 0, "UNRESOLVED": 0, "NO_ART_TEXT": 0, "NO_MAP": 0}
        for a in soup.find_all("a", href=True):
            m = RE_HREF.search(a["href"])
            if not m:
                continue
            tgt_doc, anchor = m.group(1), m.group(2)
            is_self = (tgt_doc == self_doc)
            if is_self and not do_self:
                continue
            tgt_code = d2c.get(tgt_doc)
            if tgt_code is None:
                # цель — не наш обрабатываемый кодекс: проверить карту нечем
                continue
            if tgt_code not in rev_cache:
                rev_cache[tgt_code] = load_reverse_map(tgt_code)
            rev = rev_cache[tgt_code]
            if not rev:
                per["NO_MAP"] += 1
                continue
            resolved = rev.get(anchor)
            cands = article_candidates(a)
            if resolved is None:
                per["UNRESOLVED"] += 1
                if per["UNRESOLVED"] <= 5:
                    P(f"  [UNRESOLVED] {code}: {a.get_text()[:40]!r} -> {tgt_code}#{anchor} "
                      f"(якорь не статья/подпункт в карте {tgt_code})")
                continue
            if not cands:
                per["NO_ART_TEXT"] += 1
                continue
            if str(resolved) in {str(x) for x in cands}:
                per["OK"] += 1
            elif range_first_ok(resolved, cands):
                per["OK"] += 1          # RANGE-FIRST: диапазон -> первая статья
            elif (code, tgt_code, anchor) in DEPLOY_PENDING:
                per["DEPLOY_PENDING"] = per.get("DEPLOY_PENDING", 0) + 1
            else:
                per["MISMATCH"] += 1
                mismatches.append((code, tgt_code, anchor, sorted(cands), resolved,
                                   a.get_text()[:50]))
        for k in tot:
            tot[k] += per[k]
        if any(per.values()):
            dp = (f"  DEPLOY_PENDING={per['DEPLOY_PENDING']}"
                  if per.get("DEPLOY_PENDING") else "")
            P(f"\n{code:20} OK={per['OK']}  MISMATCH={per['MISMATCH']}  "
              f"UNRESOLVED={per['UNRESOLVED']}  NO_ART_TEXT={per['NO_ART_TEXT']}  "
              f"NO_MAP={per['NO_MAP']}{dp}")

    P("\n" + "=" * 100)
    P(f"ИТОГО: OK={tot['OK']}  MISMATCH={tot['MISMATCH']}  UNRESOLVED={tot['UNRESOLVED']}  "
      f"NO_ART_TEXT={tot['NO_ART_TEXT']}  NO_MAP={tot['NO_MAP']}")
    if mismatches:
        P("\nMISMATCH (ОПАСНО — ссылка ведёт на ЧУЖУЮ статью по нашей карте):")
        for src, tgt, anc, t_cands, r_art, txt in mismatches:
            P(f"  {src} -> {tgt}#{anc}: текст-кандидаты={t_cands} но якорь = статья {r_art}  "
              f"| {txt!r}")

    REPORTS.mkdir(parents=True, exist_ok=True)
    out = REPORTS / "75_crosscode_verify.txt"
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))
    print(f"\n[crosscode] MISMATCH={tot['MISMATCH']} UNRESOLVED={tot['UNRESOLVED']} -> {out}")

    if strict and tot["MISMATCH"]:
        sys.exit(1)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    strict = "--strict" in sys.argv
    do_self = "--self" in sys.argv
    run(args, strict, do_self)


if __name__ == "__main__":
    main()
