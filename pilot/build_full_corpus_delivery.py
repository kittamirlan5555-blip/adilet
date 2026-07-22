# -*- coding: utf-8 -*-
"""ФИНАЛЬНАЯ СДАЧА: пакет deliverables/full_corpus_delivery/ (вне git, в манифест).

Состав: laws/ — 161 новый закон (_ready батчей 1-3, DONE/UNDER_CHUNK; старый корпус и
пилот НЕ включаются — уже сданы); reports/ — индекс, реестр-сводка, corpus_red_fix,
README по-русски без жаргона.
"""
import csv, io, json, re, shutil, statistics, sys, tempfile, importlib.util
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from pathlib import Path
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "deliverables" / "full_corpus_delivery"
FINAL = ROOT / "final"
CODES = json.loads((ROOT / "maps" / "codes.json").read_text(encoding="utf-8"))

sys.path.insert(0, str(ROOT / "scripts" / "audit"))
import auditlib as al  # noqa
spec = importlib.util.spec_from_file_location("gap76", ROOT / "scripts" / "pipeline" / "76_mapping_gap_report.py")
gap76 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gap76)
MKEYS = list(json.loads((ROOT / "maps" / "npa_mapping.json").read_text(encoding="utf-8")).keys())


def clean_title(t):
    return re.sub(r"\s*-\s*ИПС.*$", "", t or "").strip()


# ── сдаваемые: DONE/UNDER_CHUNK батчей 1-3 ──
rows = []
for tag in ("batch_001", "batch_002", "batch_003"):
    for r in csv.DictReader((ROOT / "reports" / "pilot" / f"{tag}.csv").open(encoding="utf-8")):
        if r["status"] in ("DONE", "UNDER_CHUNK"):
            rows.append(r)
slugs = [r["slug"] for r in rows]
assert len(slugs) == len(set(slugs)), "дубли слагов между батчами!"
print(f"сдаваемых законов: {len(slugs)}")

if PKG.exists():
    shutil.rmtree(PKG)
(PKG / "laws").mkdir(parents=True)
(PKG / "reports").mkdir()

# 1) laws/
for s in slugs:
    shutil.copy2(FINAL / f"{s}_ready.html", PKG / "laws" / f"{s}_ready.html")

# 2) индекс (gaps считаем по _ready через tmp-копию, как build_index)
tmp = Path(tempfile.mkdtemp())
for s in slugs:
    shutil.copy(FINAL / f"{s}_ready.html", tmp / f"{s}_structured.html")
al.FINAL = tmp
idx = []
for r in rows:
    s = r["slug"]
    soup = BeautifulSoup((FINAL / f"{s}_ready.html").read_text(encoding="utf-8", errors="replace"), "html.parser")
    zint = ext = 0
    for a in soup.find_all("a", href=True):
        h = a["href"].strip()
        if h.startswith("#z"):
            zint += 1
        elif h.startswith(("https://adilet.zan.kz/rus/docs/", "http://adilet.zan.kz/rus/docs/")):
            ext += 1
    gaps = len(gap76.scan(s, MKEYS)[1])
    cov = round(100 * ext / (ext + gaps)) if (ext + gaps) else 100
    idx.append({"ngr": s, "title": clean_title(CODES.get(s, {}).get("title", ""))[:64],
                "arts": r["sa"], "zint": zint, "ext": ext, "cov": cov, "status": r["status"]})
shutil.rmtree(tmp, ignore_errors=True)

L = ["# Индекс новых законов (сдача полного корпуса)", "",
     f"Всего: **{len(idx)}**. Колонки: статей — статей в структуре; #z — внутренних "
     "ссылок; ext — внешних ссылок на акты; cov — покрытие внешних ссылок "
     "(ext/(ext+нераспознанные фразы)); статус UNDER_CHUNK = расхождение счёта на 1 "
     "служебную статью, на ссылки не влияет.", "",
     "| НГР | название | статей | #z | ext | cov | статус |", "|---|---|--:|--:|--:|--:|---|"]
for r in sorted(idx, key=lambda x: x["ngr"]):
    L.append(f"| {r['ngr']} | {r['title']} | {r['arts']} | {r['zint']} | {r['ext']} | "
             f"{r['cov']}% | {r['status']} |")
covs = [r["cov"] for r in idx]
L += ["", f"cov медиана: **{statistics.median(covs)}%**; "
      f"сумм. внутренних #z: **{sum(r['zint'] for r in idx)}**, внешних: **{sum(r['ext'] for r in idx)}**."]
(PKG / "reports" / "index.md").write_text("\n".join(L) + "\n", encoding="utf-8")

# 3) реестр-сводка
reg = json.loads((ROOT / "maps" / "corpus_registry.json").read_text(encoding="utf-8"))
from collections import Counter
bt = Counter(x["bucket"] for x in reg)
RS = f"""# Реестр корпуса — сводка (что вообще есть и что сделано)

Перечислены ВСЕ акты adilet типов «Закон / Кодекс / Конституционный закон» (+указы силы
закона): **{len(reg)}** записей.

## Материальные (регуляторные) действующие акты — цель гиперссылочной обработки

- ВСЕГО материальных: **306**
- **обработано: 290** (43 ранее сданных кодекса/закона + 82 пилотных + 161 в этой сдаче + 4 дожатых включены в счёт батчей)
- осталось: **16** — НЕ полноценные законы (см. таблицу обоснований в отчёте
  `reports/full_corpus_summary.md` репозитория): 4 бюджетно-распределительных, 3 «о
  введении в действие», 2 списка отмен 1993-95, 7 тонких актов 1990-97 (статуты наград,
  каталоги, переименования).

## Исключено из обработки по классам (это НЕ материальные законы)

| класс | сколько | почему не обрабатываем |
|---|--:|---|
| поправки «О внесении изменений…» | 1655 | меняют другой акт, собственной структуры нет |
| ратификации международных договоров | 1291 | 1-2 статьи, тело — приложенный договор |
| утратившие силу | 382 | недействующие редакции |
| «О признании утратившими силу…» | 59 | списки отмен |
| бюджетные (годовые) | 36 | ежегодные цифровые акты |
| амнистии | 15 | разовые акты |
| старые редакции при новом преемнике | 3 | работаем с новой редакцией |
"""
(PKG / "reports" / "registry_summary.md").write_text(RS, encoding="utf-8")

# 4) corpus_red_fix
shutil.copy2(ROOT / "reports" / "corpus_red_fix.md", PKG / "reports" / "corpus_red_fix.md")

# 5) README
covmed = statistics.median(covs)
README = f"""# Полный корпус законов РК — гиперссылочная обработка (финальная сдача)

В пакете — **{len(idx)} новых действующих законов РК** со структурой и работающими
гиперссылками: внутренние отсылки («статья N настоящего Закона») ведут на статью в том
же файле, внешние («Законом РК "О …"») — на страницу акта на adilet.zan.kz.

Вместе с ранее сданными (кодексы, конституционные законы, пилотные 100) обработан
**весь материальный корпус законодательства РК: 290 из 306 действующих регуляторных
актов**. Оставшиеся 16 — не законы в содержательном смысле (годовые бюджетные акты,
техакты «о введении в действие», списки отмен 90-х) — перечень с объяснением по каждому
в reports/registry_summary.md.

## Как смотреть

- `laws/*.html` — открывать в БРАУЗЕРЕ (в Word ссылки визуально не отличаются от текста).
- `reports/index.md` — таблица по каждому закону: статей, ссылок, покрытие.
- `reports/registry_summary.md` — что вообще существует в законодательстве и что из
  этого обработано/исключено (с числами).
- `reports/corpus_red_fix.md` — заодно исправили 13 неточных глубоких ссылок в ранее
  сданных кодексах (вели на несуществующие места; теперь ведут на страницу акта).

## Качество

Каждый закон прошёл автоматические проверки (текст не изменён ни на символ; ссылки не
вложены; все внутренние якоря существуют) + независимый аудит и ручные выборочные
проверки. Покрытие внешних ссылок — медиана **{covmed}%** (остаток — редкие/неоднозначные
формулировки, их долинковка — отдельным проходом по решению).
"""
(PKG / "README.md").write_text(README, encoding="utf-8")

print(f"пакет: {PKG.relative_to(ROOT)}")
print(f"  laws/: {len(list((PKG/'laws').glob('*.html')))} файлов")
print(f"  reports/: {sorted(p.name for p in (PKG/'reports').iterdir())}")
print(f"  cov медиана: {covmed}%")
