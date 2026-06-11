"""Вернуть в _structured ВАЛИДНЫЕ ссылки, которые структуризатор потерял
(оставил голым текстом), на реальные якоря существующих статей.

Контекст: при синхроне 30 эти 7 отсылок были временно сняты из _ready по неверной
логике «нет в structured → мусор». Проверка показала: статьи-цели СУЩЕСТВУЮТ и якоря
резолвятся — значит ссылки ВАЛИДНЫЕ, их потерял _structured. _ready уже восстановлен
из бэкапа; здесь добавляем те же ссылки в _structured (оборачиваем токен в <a href>).

Цель — точечно, по конкретной статье и токену, с проверкой что токен в этой статье
встречается ровно ожидаемое число раз и сейчас НЕ в ссылке. Идемпотентно: уже
обёрнутые пропускаются.

  python scripts/31_add_lost_links_structured.py            # dry-run
  python scripts/31_add_lost_links_structured.py --apply     # писать _structured
"""
import re
import sys
import shutil
from pathlib import Path
from bs4 import BeautifulSoup, NavigableString

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import paths

ROOT = paths.ROOT
FINAL = paths.FINAL
APPLY = "--apply" in sys.argv
BACKUP = paths.BACKUPS / "final_backup_ADDLINKS"

UK = "https://adilet.zan.kz/rus/docs/K1400000226"   # внешний таргет = Уголовный кодекс

# (code, article, token, expected_unlinked, href)  href-стиль = как у соседних ссылок
TARGETS = [
    ("upk", "32",  "108-1", 1, f"{UK}#z2902"),
    ("upk", "32",  "109-1", 1, f"{UK}#z2915"),
    ("upk", "32",  "115-1", 1, f"{UK}#z3099"),
    ("upk", "63",  "192-1", 1, "#z5161"),
    ("upk", "63",  "192-2", 1, "#z5164"),
    ("upk", "136", "108-1", 1, f"{UK}#z2902"),
    ("upk", "136", "109-1", 1, f"{UK}#z2915"),
]


def find_article(soup, num):
    for d in soup.find_all("div", attrs={"data-type": "статья"}):
        if d.get("data-number") == num:
            return d
    return None


def wrap_token(soup, art, token, href):
    """Обернуть ПЕРВОЕ нессылочное вхождение token (как самостоятельный номер) в <a>.
    Возвращает (ok, before_ctx, after_ctx)."""
    pat = re.compile(r"(?<!\d)" + re.escape(token) + r"(?!\d)")
    for tn in art.find_all(string=pat):
        if tn.find_parent("a"):
            continue
        s = str(tn)
        m = pat.search(s)
        if not m:
            continue
        i, j = m.start(), m.end()
        before, after = s[:i], s[j:]
        a = soup.new_tag("a", href=href)
        a.string = token
        before_ns = NavigableString(before)
        after_ns = NavigableString(after)
        tn.replace_with(before_ns)
        before_ns.insert_after(a)
        a.insert_after(after_ns)
        return True, before[-30:], after[:30]
    return False, None, None


REPORT = paths.REPORTS / "31_addlinks_report.txt"
OUT = []


def emit(s=""):
    OUT.append(s)


def main():
    mode = "APPLY" if APPLY else "DRY-RUN"
    emit(f"ADD LOST LINKS -> _structured — режим: {mode}")
    emit("=" * 96)
    by_code = {}
    for code, art, tok, exp, href in TARGETS:
        by_code.setdefault(code, []).append((art, tok, exp, href))
    for code, items in by_code.items():
        sp = FINAL / f"{code}_structured.html"
        raw_orig = sp.read_text(encoding="utf-8")
        soup = BeautifulSoup(raw_orig, "html.parser")
        done = 0
        for art_num, tok, exp, href in items:
            art = find_article(soup, art_num)
            if art is None:
                emit(f"  [{code}] ст.{art_num}: НЕ НАЙДЕНА — пропуск {tok}")
                continue
            pat = re.compile(r"(?<!\d)" + re.escape(tok) + r"(?!\d)")
            unlinked = sum(len(pat.findall(str(tn))) for tn in art.find_all(string=pat)
                           if not tn.find_parent("a"))
            if unlinked != exp:
                emit(f"  [{code}] ст.{art_num} {tok}: unlinked={unlinked}≠{exp} — ПРОПУСК (ручная проверка)")
                continue
            ok, b, a_ = wrap_token(soup, art, tok, href)
            if ok:
                done += 1
                emit(f"  [{code}] ст.{art_num} {tok:6} -> <a href=\"{href}\">  "
                     f"before→after: ...{b}[{tok}]{a_}...")
        if APPLY and done:
            # ГЕЙТ §6.1: оборачиваются токены — текст обязан совпасть
            if "".join(re.sub(r"<[^>]+>", " ", raw_orig).split()) != \
                    "".join(re.sub(r"<[^>]+>", " ", str(soup)).split()):
                raise SystemExit(f"TEXT-INVARIANCE FAIL: {sp.name}")
            bk = BACKUP / f"{code}_structured.html"
            if not bk.exists():
                BACKUP.mkdir(parents=True, exist_ok=True)
                shutil.copy2(sp, bk)
            sp.write_text(str(soup), encoding="utf-8")
            emit(f"  [{code}] записано правок: {done}")
        else:
            emit(f"  [{code}] (dry-run) обернётся: {done}")
    REPORT.write_text("\n".join(OUT) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
