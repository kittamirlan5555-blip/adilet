# -*- coding: utf-8 -*-
"""
ИНГЕСТ ИЗ ADILET (замена мёртвого Swagger :9096).

Качает сырой HTML НПА прямо с adilet.zan.kz по списку НГР, кладёт в source/{НГР}.html,
сам выводит doc_id из панельных self-ссылок (history|info|links|...) и сразу делает
ШЕЙП-ЧЕК (есть ли article-сигнатуры). Регистрирует чистые доки в maps/codes.json
(slug = НГР, чтобы не возиться с транслитерацией имён).

ЗАПУСК (на твоей машине — у песочницы Клода нет доступа к adilet):
    python pilot/01_ingest_adilet.py pilot_100.txt
где pilot_100.txt — по одному НГР в строке (напр. Z1500000418). # и пустые строки игнорятся.

ВЫХОД:
    source/{НГР}.html            — сырьё (read-only для пайплайна)
    pilot/ingest_manifest.csv    — НГР, http, КБ, doc_id, сигнатуры, вердикт
    maps/codes.json              — дополнен чистыми (OK) доками

ВАЖНО — САМОПРОВЕРКА RAW-GET vs Ctrl+S:
    Если у дока sig=0 (нет ни <a name=z>, ни <b>Статья>) — это либо чужой формат
    (ратификация/договор/поправки → КРИВО, в карантин), ЛИБО raw-GET вернул не тот
    DOM, что Ctrl+S. Манифест пометит такие FETCH_THIN. Если их МНОГО и среди них
    заведомо «нормальные» законы — значит adilet рендерит клиентом, и нужен playwright
    (headless), а не requests. Проверь это на ПЕРВОМ же прогоне, до масштаба.
"""
import csv
import json
import re
import sys
import time
from collections import Counter
from pathlib import Path

try:
    import requests
except ImportError:
    sys.exit("нужен requests:  pip install requests")
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "source"
CODES_JSON = ROOT / "maps" / "codes.json"
MANIFEST = ROOT / "pilot" / "ingest_manifest.csv"
SOURCE.mkdir(exist_ok=True)

URL_TMPL = "https://adilet.zan.kz/rus/docs/{ngr}"
HEADERS = {"User-Agent": "Mozilla/5.0 (ADILETkz pilot ingester; contact: team)"}
SLEEP_SEC = 1.0          # вежливость к adilet
RETRIES = 3

# те же сигнатуры, что в scripts/audit/preflight_new.py — единый критерий
SELF_SUFFIX = re.compile(r"/docs/([KZ][0-9A-Za-z_]+)/(?:history|info|links|compare|print|word|pdf)")
RE_ZNAME = re.compile(r"^z\d+")
RE_ART_B = re.compile(r"^Статья\s+\d+(?:-\d+)?\s*\.")
# Документ-уровневый статус «утратил силу»: adilet ставит «Сноска. Утратил силу …»
# в ШАПКЕ (до первой «Статья N.»).
# ФИНИТНЫЙ глагол «утратил[а/о/и] силу» — статус ЭТОГО акта. НЕ причастие
# «утративш…» («в связи с признанием утративш­им силу Закона X», «Признать
# утратившими силу…») — это про ДРУГИЕ акты и НЕ означает отмену текущего
# (иначе ловушка: живой закон/«о введении в действие» ложно = REPEALED).
# Ищем ТОЛЬКО в шапке: полнотекстовый поиск ложно флагает действующие акты,
# упоминающие «утратил силу» в теле (проверено: appk/arbitrazh/konstsud/lesnoy).
# Обратная сторона — сноску отмены НИЖЕ первой «Статьи» пропустим (см. night_notes,
# надёжного признака без ложных срабатываний не нашли — оставлено как есть).
RE_ARTICLE_ANY = re.compile(r"Стать[яиею]\s+\d")
RE_REPEALED = re.compile(r"[Уу]тратил[аио]?\s+силу")


def fetch(ngr: str) -> tuple[int, bytes]:
    url = URL_TMPL.format(ngr=ngr)
    last = None
    for attempt in range(1, RETRIES + 1):
        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
            return r.status_code, r.content
        except requests.RequestException as e:
            last = e
            time.sleep(2 * attempt)
    print(f"  [сеть] {ngr}: {last}")
    return 0, b""


def shape(html: str) -> dict:
    """doc_id + счётчики article-сигнатур (без полного build_article_map — быстро)."""
    soup = BeautifulSoup(html, "html.parser")
    for t in soup.find_all(["script", "style", "template"]):
        t.decompose()
    a_name = sum(1 for a in soup.find_all("a", attrs={"name": True})
                 if RE_ZNAME.match(a.get("name", "")))
    h3_id = sum(1 for h in soup.find_all("h3", id=True)
                if RE_ZNAME.match(h.get("id", "")))
    b_art = sum(1 for b in soup.find_all("b")
                if RE_ART_B.match(b.get_text(" ", strip=True)))
    did = Counter(SELF_SUFFIX.findall(html)).most_common(1)
    title = ""
    if soup.title and soup.title.string:
        title = soup.title.string.strip()
    og = soup.find("meta", property="og:title")
    if og and og.get("content"):
        title = og["content"].strip()
    # статус: «утратил силу» в шапке (до первой «Статья N.»)
    art = soup.find("article") or soup
    atext = art.get_text(" ", strip=True)
    mA = RE_ARTICLE_ANY.search(atext)
    header = atext[:mA.start()] if mA else atext[:2000]
    repealed = bool(RE_REPEALED.search(header))
    return {"a_name": a_name, "h3_id": h3_id, "b_art": b_art,
            "sig": a_name + h3_id + b_art,
            "doc_id": did[0][0] if did else "", "title": title,
            "repealed": repealed}


def load_codes() -> dict:
    return json.loads(CODES_JSON.read_text(encoding="utf-8")) if CODES_JSON.exists() else {}


def save_codes(codes: dict) -> None:
    CODES_JSON.write_text(json.dumps(codes, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    argv = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not argv:
        sys.exit("укажи файл со списком НГР:  python pilot/01_ingest_adilet.py pilot_100.txt [--manifest PATH]")
    listfile = Path(argv[0])
    global MANIFEST
    if "--manifest" in sys.argv:
        MANIFEST = Path(sys.argv[sys.argv.index("--manifest") + 1])
    ngrs = [ln.strip() for ln in listfile.read_text(encoding="utf-8").splitlines()
            if ln.strip() and not ln.strip().startswith("#")]
    print(f"НГР в списке: {len(ngrs)}")

    codes = load_codes()
    rows, added, quarantine, repealed_l = [], 0, [], []

    for i, ngr in enumerate(ngrs, 1):
        dst = SOURCE / f"{ngr}.html"
        if dst.exists():
            html = dst.read_text(encoding="utf-8", errors="replace")
            status, kb = 200, round(len(html.encode()) / 1024)
            print(f"[{i}/{len(ngrs)}] {ngr}: уже на диске ({kb} КБ)")
        else:
            status, content = fetch(ngr)
            time.sleep(SLEEP_SEC)
            if status != 200 or not content:
                print(f"[{i}/{len(ngrs)}] {ngr}: HTTP {status} — пропуск")
                rows.append([ngr, status, 0, "", 0, "FETCH_FAIL"])
                continue
            html = content.decode("utf-8", errors="replace")
            dst.write_text(html, encoding="utf-8")
            kb = round(len(content) / 1024)

        sh = shape(html)
        if sh["repealed"]:
            verdict = "REPEALED"            # документ утратил силу — в корпус НЕ берём
            repealed_l.append(ngr)          # в codes.json НЕ регистрируем, только в манифест
            codes.pop(ngr, None)            # если был зарегистрирован раньше — вычищаем (идемпотентно)
        elif sh["sig"] == 0:
            verdict = "FETCH_THIN"          # 0 сигнатур: чужой формат ИЛИ raw-GET не тот DOM
            quarantine.append(ngr)
        elif not sh["doc_id"]:
            verdict = "NO_DOCID"            # панельных ссылок нет — подозрительно
            quarantine.append(ngr)
        else:
            verdict = "OK"
            # регистрируем slug=НГР; doc_id из панели (надёжнее, чем НГР с суффиксом)
            codes[ngr] = {"doc_id": sh["doc_id"], "title": sh["title"][:120] or ngr}
            added += 1
        print(f"    {ngr}: {kb}КБ  sig={sh['sig']} (a={sh['a_name']} h3={sh['h3_id']} b={sh['b_art']})"
              f"  doc_id={sh['doc_id'] or '—'}  -> {verdict}")
        rows.append([ngr, status, kb, sh["doc_id"], sh["sig"], verdict])

    save_codes(codes)
    MANIFEST.parent.mkdir(exist_ok=True)
    with MANIFEST.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["ngr", "http", "kb", "doc_id", "sig", "verdict"])
        w.writerows(rows)

    print("\n" + "=" * 60)
    print(f"скачано/на диске: {sum(1 for r in rows if r[5] != 'FETCH_FAIL')}/{len(ngrs)}")
    print(f"зарегистрировано в codes.json (OK): {added}")
    print(f"утратили силу (REPEALED, не регистрированы): {len(repealed_l)} -> {' '.join(repealed_l) or '—'}")
    print(f"в карантин (FETCH_THIN/NO_DOCID): {len(quarantine)} -> {' '.join(quarantine) or '—'}")
    print(f"манифест: {MANIFEST.relative_to(ROOT)}")
    if quarantine and len(quarantine) > 0.15 * len(ngrs):
        print("\n[ВНИМАНИЕ] карантина >15%. Если среди них нормальные законы —")
        print("          adilet рендерит клиентом: переходи на playwright/headless, а не requests.")


if __name__ == "__main__":
    main()
