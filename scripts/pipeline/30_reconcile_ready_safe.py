"""SAFE reconcile: подтянуть link-канон из _structured в _ready (текстовое
выравнивание + гард на каждую правку).

ПОЧЕМУ не difflib-по-href (как в 29 --reconcile): href — это ровно то, что между
ready/structured меняется (его и диффим), поэтому позиционный дифф ПО href
МИСАЛАЙНИТ и плодит фантомные only_ready/only_struct. Пример: upk #z192 'статьи 32'
остаётся ССЫЛКОЙ в ОБОИХ файлах, но href-дифф показывает его как only_ready.

ПОДХОД: выравниваем последовательности ссылок по НОРМАЛИЗОВАННОМУ ВИДИМОМУ ТЕКСТУ
(он стабилен при структуризации). В text-equal блоках, если href различается ->
ретаргетим _ready на канон (ГАРД: внутренний #zK применяется только если zK реально
есть в DOM _ready). text-delete блок (ссылка есть в ready, и пары (sig,text) НЕТ
нигде в structured) -> разворачиваем ссылку в _ready в текст (напр. trudovoy #z23
'статьей 23-1' — линк, вручную снятый в structured). text-insert / text-replace
(структуризатор расширил текст ссылки или это контентные добавки) -> ТОЛЬКО ЛОГ,
без авто-правки (нельзя безопасно обернуть произвольный текст; чанки всё равно
строятся из _structured).

  python scripts/30_reconcile_ready_safe.py            # dry-run (отчёт)
  python scripts/30_reconcile_ready_safe.py --apply    # писать _ready
  python scripts/30_reconcile_ready_safe.py --code upk # только один код
"""
import re
import sys
import shutil
import difflib
import importlib.util
from pathlib import Path
from collections import Counter
from bs4 import BeautifulSoup, NavigableString

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import paths

ROOT = paths.ROOT
FINAL = paths.FINAL
APPLY = "--apply" in sys.argv
BACKUP = paths.BACKUPS / "final_backup_RECONCILE"

# переиспользуем norm_href/link_sigs/SELF_DOC/CODES из скрипта 29
_spec = importlib.util.spec_from_file_location(
    "diff29", ROOT / "scripts" / "pipeline" / "29_diff_ready_structured.py")
D = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(D)
SELF_DOC = D.SELF_DOC
CODES = D.CODES
norm_href = D.norm_href
link_sigs = D.link_sigs

# одиночный код через --code X
ONLY = None
if "--code" in sys.argv:
    ONLY = sys.argv[sys.argv.index("--code") + 1]

DOC_RE = re.compile(r"/docs/[A-Z]\d{6,}_?(#z[\w-]+)?")
DOCID_RE = re.compile(r"/docs/([A-Z]\d{6,}_?)")
NUM_RE = re.compile(r"(\d+(?:-\d+)?)")
DOC2CODE = {v: k for k, v in SELF_DOC.items()}   # doc_id -> код (для внешних таргетов)

# артикул-номера целевого кодекса (для гарда «статья существует?»)
_artnums = {}


def artnums_for_code(code):
    if code in _artnums:
        return _artnums[code]
    sp = FINAL / f"{code}_structured.html"
    nums = set()
    if sp.exists():
        s = BeautifulSoup(sp.read_text(encoding="utf-8"), "html.parser")
        for d in s.find_all("div", attrs={"data-type": "статья"}):
            dn = d.get("data-number")
            if dn:
                nums.add(dn)
    _artnums[code] = nums
    return nums


def target_code(sig, cur_code):
    """Куда ведёт ссылка: внутр.#z -> текущий код; внешн./docs/DOC -> код по doc_id."""
    if sig.startswith("#"):
        return cur_code
    m = DOCID_RE.search(sig)
    if m:
        return DOC2CODE.get(m.group(1))   # None если внешний акт вне наших кодексов
    return None


def claimed_article(text):
    m = NUM_RE.search(text or "")
    return m.group(1) if m else None


def target_article_exists(sig, text, cur_code):
    """ВАЖНО: ссылку НЕ снимаем, если заявленная статья реально существует в цели —
    тогда это валидная отсылка, которую _structured потерял, а не мусор."""
    tcode = target_code(sig, cur_code)
    if tcode is None:                    # внешний акт вне наших файлов — не можем
        return True                      # доказать «мусор» -> консервативно НЕ снимаем
    claim = claimed_article(text)
    if not claim:
        return True                      # номер не извлекли -> консервативно НЕ снимаем
    return claim in artnums_for_code(tcode)


def rewrite_href(old, sig):
    """Перенести канон-сигнатуру в реальный href, сохраняя стиль ссылки ready."""
    if sig.startswith("#"):
        return sig                      # внутренняя относительная
    if "/docs/" in old:
        return DOC_RE.sub(sig, old, count=1)   # внешняя: подменить /docs/DOC#frag
    return sig


def ready_anchor_ids(soup):
    ids = set()
    for t in soup.find_all(id=True):
        ids.add(t.get("id"))
    for t in soup.find_all(attrs={"name": True}):
        ids.add(t.get("name"))
    return ids


def reconcile(code):
    rp = FINAL / f"{code}_ready.html"
    sp = FINAL / f"{code}_structured.html"
    if not rp.exists() or not sp.exists():
        return None
    self_doc = SELF_DOC.get(code, "")
    soup_r = BeautifulSoup(rp.read_text(encoding="utf-8"), "html.parser")
    soup_s = BeautifulSoup(sp.read_text(encoding="utf-8"), "html.parser")
    R = link_sigs(soup_r, self_doc)
    S = link_sigs(soup_s, self_doc)
    rids = ready_anchor_ids(soup_r)
    S_pairs = set((s, t) for s, t, _ in S)     # гард: пара (sig,text) есть в каноне
    S_sigs = set(s for s, t, _ in S)           # гард: сам href-таргет есть в каноне

    textR = [t for _, t, _ in R]
    textS = [t for _, t, _ in S]
    sm = difflib.SequenceMatcher(a=textR, b=textS, autojunk=False)

    retarget, unwrap, skip, struct, kept = [], [], [], [], []
    changed = 0
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                rs, rt, ra = R[i1 + k]
                ss, st, _ = S[j1 + k]
                if rs == ss:
                    continue
                # ретаргет-кандидат (текст совпал, href отличается)
                if ss.startswith("#z"):
                    if ss[1:] in rids:
                        retarget.append((rs, ss, rt))
                        if APPLY:
                            ra["href"] = rewrite_href(ra["href"], ss)
                            changed += 1
                    else:
                        skip.append((rs, ss, rt, f"якорь {ss} отсутствует в _ready"))
                else:
                    retarget.append((rs, ss, rt))
                    if APPLY:
                        ra["href"] = rewrite_href(ra["href"], ss)
                        changed += 1
        elif tag == "delete":
            for k in range(i1, i2):
                rs, rt, ra = R[k]
                if (rs, rt) in S_pairs:            # такой же линк есть в каноне
                    skip.append((rs, "-", rt, "delete-артефакт (пара есть в structured)"))
                elif rs in S_sigs:                 # таргет жив, отличается только спан текста
                    skip.append((rs, "-", rt, "span/text-diff (sig есть в structured)"))
                elif target_article_exists(rs, rt, code):
                    # ВАЛИДНАЯ отсылка: статья-цель существует, _structured её потерял.
                    # НЕ снимаем — это не мусор (линк нужно вернуть и в _structured).
                    kept.append((rs, rt, claimed_article(rt), target_code(rs, code)))
                else:                              # цель не существует -> подлинно мусор -> снять
                    unwrap.append((rs, rt))
                    if APPLY:
                        ra.replace_with(NavigableString(ra.get_text()))
                        changed += 1
        elif tag == "insert":
            for k in range(j1, j2):
                ss, st, _ = S[k]
                struct.append(("only_struct", ss, st))
        elif tag == "replace":
            for k in range(max(i2 - i1, j2 - j1)):
                rv = R[i1 + k][:2] if i1 + k < i2 else None
                sv = S[j1 + k][:2] if j1 + k < j2 else None
                struct.append(("text-replace", rv, sv))

    if APPLY and changed:
        bk = BACKUP / f"{code}_ready.html"
        if not bk.exists():
            BACKUP.mkdir(parents=True, exist_ok=True)
            shutil.copy2(rp, bk)
        rp.write_text(str(soup_r), encoding="utf-8")
    return retarget, unwrap, skip, struct, kept, changed


def main():
    mode = "APPLY (пишем _ready)" if APPLY else "DRY-RUN (read-only)"
    print("=" * 100)
    print(f"SAFE RECONCILE _ready <= _structured (text-aligned) — режим: {mode}")
    print("=" * 100)
    codes = [ONLY] if ONLY else CODES
    grand = Counter()
    for code in codes:
        res = reconcile(code)
        if res is None:
            print(f"  {code:16} — нет файлов, пропуск")
            continue
        retarget, unwrap, skip, struct, kept, changed = res
        grand["retarget"] += len(retarget)
        grand["unwrap"] += len(unwrap)
        grand["skip"] += len(skip)
        grand["struct"] += len(struct)
        grand["kept"] += len(kept)
        print(f"\n  {code}: retarget={len(retarget)} unwrap={len(unwrap)} "
              f"keep_valid={len(kept)} skip={len(skip)} struct(log)={len(struct)} changed={changed}")
        for rs, ss, rt in retarget:
            print(f"      RETARGET  {rs:28} -> {ss:28} | {rt[:50]}")
        for rs, rt in unwrap:
            print(f"      UNWRAP    {rs:28} (снять линк-мусор) | {rt[:50]}")
        for rs, rt, claim, tcode in kept:
            print(f"      KEEP_VALID {rs:27} ст.{claim} есть в {tcode} (structured потерял) | {rt[:40]}")
        for row in skip:
            print(f"      SKIP      {row[0]:28} -> {row[1]:18} | {row[3]} | {row[2][:40]}")
        for row in struct:
            print(f"      STRUCT    {row[0]:14} ready={row[1]}  struct={row[2]}")
    print("\n" + "-" * 100)
    print(f"  ИТОГО: retarget={grand['retarget']} unwrap={grand['unwrap']} "
          f"keep_valid={grand['kept']} skip={grand['skip']} struct(log)={grand['struct']}")
    if not APPLY:
        print("  (dry-run) перезапусти с --apply чтобы записать _ready.")
    else:
        print("  Записано. Перепроверь: python scripts/29_diff_ready_structured.py")


if __name__ == "__main__":
    main()
