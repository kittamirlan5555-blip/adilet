# -*- coding: utf-8 -*-
"""ФИКС-РАУНД БЛОК 1: восстановление испорченных диапазонов по SOURCE.

python scripts/audit/f01_restore_ranges.py [--apply]
-> data/reports/audit/06_fixround_block1.md

Источник истины — data/source/{slug}.html (READ-ONLY). Для каждого кейса из
аудита Ф2.4: находим расхождение nows-текстов статьи (final vs source),
заменяем «соединитель» в final (текстовые узлы МЕЖДУ тегами, сами теги <a>
не трогаем) на ТОЧНЫЙ текст source (entity-развёрнутый, схлопнутые пробелы).

ГЕЙТ пер-кейс: collapsed get_text статьи final == статьи source.
ГЕЙТ пер-файл: вложенных </a></a> == 0, двойных href == 0, постатейный дифф
vs source после правки пуст для починенных статей.
Без --apply: dry-run (отчёт, файлы не пишутся).
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import auditlib as al

# (slug, статья) — все кейсы Ф2.4 (02_structure_*.md, «### Статья N»)
CASES = [
    ("byudzhet", "75"), ("byudzhet", "152"),
    ("ekologicheskiy", "60"), ("ekologicheskiy", "73"),
    ("ekologicheskiy", "115"), ("ekologicheskiy", "366"),
    # grazhdanskiy 146 ИСКЛЮЧЁН: это артефакт сегментации из-за слитого
    # заголовка «Глава 4. Сделки Статья 147» (ready: 0 расхождений) — Блок 3.
    ("grazhdanskiy", "220"),
    ("koap", "41"), ("koap", "730-1"), ("koap", "876"),
    ("nalog", "371"),
    ("obrazovanie", "57"),
    ("predprinimatel", "129"), ("predprinimatel", "169"), ("predprinimatel", "196"),
    ("socialnyy", "100"), ("socialnyy", "212"), ("socialnyy", "213"),
    ("zemelnyy", "37"),
    ("zhilishniy", "42"),
]

RE_TAG = re.compile(r"(<[^>]+>)")


def article_span(raw, num):
    """(start, end) сегмента статьи num в raw (первый кластер с этим номером)."""
    cl = al.article_clusters(raw)
    for i, (pos, n, _a, _f) in enumerate(cl):
        if n == num:
            end = cl[i + 1][0] if i + 1 < len(cl) else len(raw)
            return pos, end
    return None, None


def collapse_src(s):
    """Сырой source-фрагмент -> канонический текст (entity, пробелы)."""
    for ent, rep in al.ENTITIES.items():
        s = s.replace(ent, rep)
    return re.sub(r"[\s\xa0]+", " ", s)


def patch_article(form_raw, num, src_raw, src_a, src_b, log):
    """Итеративно чинит сегмент статьи num в form_raw по source.
    Возвращает (новый form_raw, n_patches, ok)."""
    n_patches = 0
    for _round in range(12):
        a, b = article_span(form_raw, num)
        if a is None:
            log.append(f"    FAIL: статья {num} не найдена в форме")
            return form_raw, n_patches, False
        tf = al.TextMap(form_raw[a:b], strip_labels=True)
        ts = al.TextMap(src_raw[src_a:src_b])
        F, S = tf.nows, ts.nows
        if F == S:
            return form_raw, n_patches, True
        n = min(len(F), len(S))
        k = next((i for i in range(n) if F[i] != S[i]), n)
        if k == 0:
            log.append(f"    FAIL: статья {num} расходится с нулевой позиции")
            return form_raw, n_patches, False
        # ресинк: следующая цифра с обеих сторон; сверяем ЧИСЛОВОЙ ТОКЕН
        # (не 40-символьное окно — в окне может сидеть ВТОРАЯ порча той же
        # фразы, как у predprinimatel 196: «90-6-120 … 160, 231»), вторую
        # порчу добьёт следующая итерация цикла.
        jf = next((i for i in range(k, len(F)) if F[i].isdigit()), None)
        js = next((i for i in range(k, len(S)) if S[i].isdigit()), None)
        tok_f = re.match(r"\d+", F[jf:]) if jf is not None else None
        tok_s = re.match(r"\d+", S[js:]) if js is not None else None
        if (jf is None or js is None or tok_f is None or tok_s is None
                or tok_f.group(0) != tok_s.group(0)):
            log.append(f"    FAIL: статья {num} — не-соединительный дифф @{k} "
                       f"(final …{F[max(0,k-30):k+30]}… vs source "
                       f"…{S[max(0,k-30):k+30]}…) — ручной разбор")
            return form_raw, n_patches, False
        rawA = a + tf.nows_pos[k - 1] + 1          # после последнего общего симв.
        rawB = a + tf.nows_pos[jf]                 # начало второго числа
        src_mid = collapse_src(src_raw[src_a + ts.nows_pos[k - 1] + 1:
                                       src_a + ts.nows_pos[js]])
        interval = form_raw[rawA:rawB]
        pieces = RE_TAG.split(interval)
        text_slots = [i for i in range(0, len(pieces), 2)]
        # соединитель кладём в слот, где был старый текст; прочие зануляем
        best = max(text_slots, key=lambda i: len(pieces[i].strip()), default=0)
        before_txt = "".join(pieces[i] for i in text_slots)
        for i in text_slots:
            pieces[i] = ""
        pieces[best] = src_mid
        log.append(f"    патч: {before_txt.strip()!r} -> {src_mid.strip()!r} "
                   f"(@raw {rawA}, тегов в интервале: {(len(pieces)-1)//2})")
        form_raw = form_raw[:rawA] + "".join(pieces) + form_raw[rawB:]
        n_patches += 1
    log.append(f"    FAIL: статья {num} — не сошлось за 12 итераций")
    return form_raw, n_patches, False


def patch_spaces(form_raw, num, src_raw, src_a, src_b, log):
    """Второй проход: ПРОБЕЛЬНЫЕ расхождения collapsed-текста статьи vs source
    (потерянные/лишние пробелы — класс «ЗаконаРеспублики»; nows их не видит,
    но текст source = мандат блока). Правит только текстовые узлы."""
    n_patches = 0
    for _round in range(20):
        a, b = article_span(form_raw, num)
        tf = al.TextMap(form_raw[a:b], strip_labels=True)
        ts = al.TextMap(src_raw[src_a:src_b])
        Fx = re.sub(r"\s+", " ", tf.text).strip()
        Sx = re.sub(r"\s+", " ", ts.text).strip()
        if Fx == Sx:
            return form_raw, n_patches, True
        F, S = tf.text, ts.text
        n = min(len(F), len(S))
        k = next((i for i in range(n) if F[i] != S[i]), n)
        if k >= len(F) or k >= len(S):
            return form_raw, n_patches, False
        if S[k] == " " and F[k] != " ":            # в финале потерян пробел
            rp = a + tf.pos[k]
            log.append(f"    пробел-патч: вставка ' ' перед "
                       f"{F[k:k+18]!r} (@raw {rp})")
            form_raw = form_raw[:rp] + " " + form_raw[rp:]
            n_patches += 1
            continue
        if F[k] == " " and S[k] != " ":            # в финале лишний пробел
            rp = a + tf.pos[k]
            log.append(f"    пробел-патч: удаление ' ' перед "
                       f"{F[k+1:k+19]!r} (@raw {rp})")
            form_raw = form_raw[:rp] + form_raw[rp + 1:]
            n_patches += 1
            continue
        return form_raw, n_patches, False          # не пробельный дифф
    return form_raw, n_patches, False


def main():
    apply_mode = "--apply" in sys.argv
    L = ["# ФИКС-РАУНД БЛОК 1 — восстановление диапазонов по source", "",
         f"Режим: {'APPLY' if apply_mode else 'DRY-RUN'}. "
         "Гейт пер-кейс: collapsed-текст статьи final == source.", "",
         "| документ | статья | форма | патчей | до | после | гейт |", "|---|---|---|---|---|---|---|"]
    by_slug = {}
    for slug, num in CASES:
        by_slug.setdefault(slug, []).append(num)

    total_ok = total_fail = 0
    for slug, nums in by_slug.items():
        src = al.source_file(slug).read_text(encoding="utf-8")
        for form in ("ready", "structured"):
            p = al.FINAL / f"{slug}_{form}.html"
            if not p.exists():
                continue
            raw = p.read_text(encoding="utf-8")
            nested0 = len(al.RE_NESTED_CLOSE.findall(raw))
            dbl0 = len(al.RE_DOUBLE_HREF.findall(raw))
            details = []
            for num in nums:
                sa, sb = article_span(src, num)
                if sa is None:
                    details.append(f"    FAIL: статья {num} не найдена в source")
                    total_fail += 1
                    continue
                # до/после: фрагмент вокруг первого диффа
                a0, b0 = article_span(raw, num)
                t0 = al.TextMap(raw[a0:b0], strip_labels=True)
                ts0 = al.TextMap(src[sa:sb])
                n = min(len(t0.nows), len(ts0.nows))
                k0 = next((i for i in range(n) if t0.nows[i] != ts0.nows[i]), n)
                frag_before = t0.nows[max(0, k0 - 25):k0 + 25]
                raw, np_, ok = patch_article(raw, num, src, sa, sb, details)
                if ok:
                    raw, np2, ok2 = patch_spaces(raw, num, src, sa, sb, details)
                    np_ += np2
                    ok = ok and ok2
                a1, b1 = article_span(raw, num)
                t1 = al.TextMap(raw[a1:b1], strip_labels=True)
                gate = (re.sub(r"\s+", " ", t1.text).strip()
                        == re.sub(r"\s+", " ", ts0.text).strip())
                frag_after = t1.nows[max(0, k0 - 25):k0 + 25]
                L.append(f"| {slug} | {num} | {form} | {np_} | …{frag_before}… "
                         f"| …{frag_after}… | {'PASS' if ok and gate else '**FAIL**'} |")
                total_ok += (ok and gate)
                total_fail += not (ok and gate)
            nested1 = len(al.RE_NESTED_CLOSE.findall(raw))
            dbl1 = len(al.RE_DOUBLE_HREF.findall(raw))
            assert nested1 == nested0 == 0, f"{slug}_{form}: nested </a></a>!"
            assert dbl1 == dbl0 == 0, f"{slug}_{form}: двойной href!"
            if details:
                L.append(f"\nдетали {slug}_{form}:")
                L += details
                L.append("")
            if apply_mode:
                p.write_text(raw, encoding="utf-8")

    L += ["", f"**Итого кейс-форм: PASS={total_ok} FAIL={total_fail}**", "",
          "Гейты пер-файл: вложенных `</a></a>`=0 и двойных href=0 во всех "
          "затронутых файлах (assert)."]
    al.AUDIT_OUT.mkdir(parents=True, exist_ok=True)
    (al.AUDIT_OUT / "06_fixround_block1.md").write_text("\n".join(L) + "\n",
                                                        encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
