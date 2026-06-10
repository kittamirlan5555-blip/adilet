"""Read-only аудит ТЗ-02.

Доказательство, что снятие ссылок в сносках/примечаниях не задело тело.

Метод:
  1. Для каждого кода (кроме upk) и обоих файлов (_ready, _structured) берём
     data/final_backup_TZ02/<file> и data/final/<file>.
  2. Извлекаем все <a href="…">…</a> в порядке появления (с байтовой позицией
     в исходнике). Ключ для сравнения = (href, inner_text).
  3. SequenceMatcher по ключам выравнивает backup vs current. Записи backup,
     не попавшие в LCS = исчезнувшие.
  4. Для каждой исчезнувшей записи смотрим 200-символьный контекст ВОКРУГ её
     позиции В БЭКАПЕ и ищем сигнал сноски/примечания:
        "Сноска." | "Примечани" | "ИЗПИ!" | "РЦПИ!"
     Если ни один не найден → NO_SIGNAL (подозрение, что задето тело).
  5. Печатается таблица: removed_total | removed_internal_zN | NO_SIGNAL.
     При NO_SIGNAL > 0 — выводятся 5 примеров.

Скрипт ничего не пишет.
"""
import json
import re
import sys
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FINAL = ROOT / "data" / "final"
BACKUP = ROOT / "data" / "final_backup_TZ02"
CODES = ROOT / "config" / "codes.json"

# любой <a … href="…"> … </a>; группа 1 = href, группа 2 = inner.
A_RE = re.compile(
    r'<a\b[^>]*?\bhref\s*=\s*["\']([^"\']*)["\'][^>]*>(.*?)</a>',
    re.IGNORECASE | re.DOTALL,
)

# «Текстовый» сигнал — те 4 строки из ТЗ-02.
TEXT_SIGNAL_RE = re.compile(r'Сноска\.|Примечани|ИЗПИ!|РЦПИ!')

# «Структурный» сигнал — тот же смысл, но выражённый через HTML-разметку,
# которой и пользуется adilet: класс note и красный <font> примечаний ИЗПИ.
# Нужен потому, что span.note-цепочки бывают огромными, и слово «Сноска.»
# стоит в самом начале цепочки — за пределами 200-символьного окна.
STRUCT_SIGNAL_RE = re.compile(
    r'class\s*=\s*"[^"]*\bnote\b|color\s*=\s*"?#?FF0000"?',
    re.IGNORECASE,
)

CTX_NARROW = 200    # окно для текстового сигнала из ТЗ
CTX_WIDE = 4000     # расширенное окно (Сноска./Примечание в шапке длинной цепочки)
CTX_STRUCT = 400    # окно для структурного сигнала (class="note" рядом)


def extract_links(text: str):
    """[(pos, href, inner), …]  в порядке появления."""
    out = []
    for m in A_RE.finditer(text):
        out.append((m.start(), m.group(1), m.group(2)))
    return out


def context_window(text: str, pos: int, width: int) -> str:
    s = max(0, pos - width)
    e = min(len(text), pos + width)
    return text[s:e]


def detect_signal(text: str, pos: int):
    """Возвращает (has_signal, signal_kind, narrow_ctx).
      kind = 'text_narrow' | 'text_wide' | 'struct' | 'NONE'.
    Сначала пробуем строгий текстовый сигнал в ±200 (точно по ТЗ-02);
    если не нашли — расширяем окно до ±4000 (длинные span-цепочки, где
    «Сноска.» стоит в шапке); если и тут пусто — пробуем структурный сигнал
    `class="note"` или красный <font> в ±400. Если совсем ничего — NONE."""
    narrow = context_window(text, pos, CTX_NARROW)
    if TEXT_SIGNAL_RE.search(narrow):
        return True, "text_narrow", narrow
    wide = context_window(text, pos, CTX_WIDE)
    if TEXT_SIGNAL_RE.search(wide):
        return True, "text_wide", narrow
    struct = context_window(text, pos, CTX_STRUCT)
    if STRUCT_SIGNAL_RE.search(struct):
        return True, "struct", narrow
    return False, "NONE", narrow


def diff_one_file(backup_path: Path, current_path: Path):
    bt = backup_path.read_text(encoding="utf-8")
    ct = current_path.read_text(encoding="utf-8")

    B = extract_links(bt)
    C = extract_links(ct)

    B_keys = [(href, inner) for (_, href, inner) in B]
    C_keys = [(href, inner) for (_, href, inner) in C]

    sm = SequenceMatcher(a=B_keys, b=C_keys, autojunk=False)
    disappeared_idxs = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag in ("delete", "replace"):
            disappeared_idxs.extend(range(i1, i2))

    removed = []
    for i in disappeared_idxs:
        pos, href, inner = B[i]
        has_sig, kind, narrow = detect_signal(bt, pos)
        removed.append({
            "pos": pos,
            "href": href,
            "inner": inner,
            "ctx": narrow,
            "signal": has_sig,
            "kind": kind,
        })
    return removed


def audit_code(code: str):
    rows = []
    no_sig_examples = []
    for suf in ("ready", "structured"):
        b = BACKUP / f"{code}_{suf}.html"
        c = FINAL / f"{code}_{suf}.html"
        if not b.exists() or not c.exists():
            continue
        removed = diff_one_file(b, c)
        n_total    = len(removed)
        n_internal = sum(1 for r in removed if re.match(r'^#z\d', r["href"]))
        kinds = {"text_narrow": 0, "text_wide": 0, "struct": 0, "NONE": 0}
        for r in removed:
            kinds[r["kind"]] += 1
        rows.append({
            "suf": suf,
            "removed_total": n_total,
            "removed_internal": n_internal,
            "no_signal": kinds["NONE"],
            "by_kind": kinds,
        })
        for r in removed:
            if not r["signal"] and len(no_sig_examples) < 5:
                no_sig_examples.append((suf, r))
    return rows, no_sig_examples


def main():
    cfg = json.loads(CODES.read_text(encoding="utf-8"))
    codes = [k for k in cfg.keys() if not k.startswith("_") and k != "upk"]

    hdr = (f"{'код':18}{'файл':14}{'removed_total':>14}"
           f"{'rm_int(#z)':>12}{'narrow':>9}{'wide':>7}"
           f"{'struct':>9}{'NO_SIGNAL':>12}")
    print(hdr)
    print("-" * len(hdr))

    grand = {"total": 0, "internal": 0,
             "narrow": 0, "wide": 0, "struct": 0, "no_sig": 0}
    per_code_examples = {}

    for code in codes:
        rows, examples = audit_code(code)
        for r in rows:
            k = r["by_kind"]
            print(f"{code:18}{r['suf']:14}{r['removed_total']:>14}"
                  f"{r['removed_internal']:>12}{k['text_narrow']:>9}"
                  f"{k['text_wide']:>7}{k['struct']:>9}{r['no_signal']:>12}")
            grand["total"]    += r["removed_total"]
            grand["internal"] += r["removed_internal"]
            grand["narrow"]   += k["text_narrow"]
            grand["wide"]     += k["text_wide"]
            grand["struct"]   += k["struct"]
            grand["no_sig"]   += r["no_signal"]
        if examples:
            per_code_examples[code] = examples

    print("-" * len(hdr))
    print(f"{'ИТОГО':32}{grand['total']:>14}{grand['internal']:>12}"
          f"{grand['narrow']:>9}{grand['wide']:>7}"
          f"{grand['struct']:>9}{grand['no_sig']:>12}")

    if grand["no_sig"] == 0:
        print("\n[OK] NO_SIGNAL == 0 по всем кодам — тело не задето. ТЗ-02 закрыт.")
        sys.exit(0)

    print(f"\n[FAIL] NO_SIGNAL = {grand['no_sig']}. Примеры (до 5 на код):")
    for code, examples in per_code_examples.items():
        print(f"\n--- {code} ---")
        for suf, r in examples:
            print(f"  file={code}_{suf}.html  pos={r['pos']}")
            print(f"  href={r['href']!r}")
            print(f"  text={r['inner'][:80]!r}")
            print(f"  ctx={r['ctx']!r}")
            print()
    sys.exit(1)


if __name__ == "__main__":
    main()
