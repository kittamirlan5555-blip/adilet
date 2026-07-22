# -*- coding: utf-8 -*-
"""ТОЧЕЧНЫЙ headless-фетчер (D1) для client-render страниц adilet (класс FETCH_THIN).

НЕ универсальный краулер: берёт ЯВНЫЙ список НГР (файл, по одному в строке), рендерит
chromium'ом (adilet отдаёт тело статей JS-ом на старых актах 1991-96), сохраняет
готовый DOM в source/{НГР}.html и делает шейп-чек (те же сигнатуры, что 01_ingest).
Старый тонкий файл — в source/_thin_bak/ (страховка: source/ вне git).

Запуск: python pilot/03_headless_fetch.py pilot/batches/headless_list.txt
Дальше: python pilot/01_ingest_adilet.py <тот же список> --manifest … (прочтёт с диска).
"""
import io
import re
import sys
import time
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "source"
BAK = SOURCE / "_thin_bak"
BAK.mkdir(parents=True, exist_ok=True)

# те же сигнатуры, что 01_ingest/preflight — единый критерий
RE_ZNAME = re.compile(r"^z\d+")
RE_ART_B = re.compile(r"^Статья\s+\d+(?:-\d+)?\s*\.")


def shape_sig(html: str) -> tuple:
    soup = BeautifulSoup(html, "html.parser")
    for t in soup.find_all(["script", "style", "template"]):
        t.decompose()
    a_name = sum(1 for a in soup.find_all("a", attrs={"name": True})
                 if RE_ZNAME.match(a.get("name", "")))
    h3_id = sum(1 for h in soup.find_all("h3", id=True) if RE_ZNAME.match(h.get("id", "")))
    b_art = sum(1 for b in soup.find_all("b") if RE_ART_B.match(b.get_text(" ", strip=True)))
    txt = soup.get_text(" ", strip=True)
    return a_name + h3_id + b_art, len(txt)


def main():
    if len(sys.argv) < 2:
        sys.exit("дай файл со списком НГР")
    # ПО-СТРОЧНО (не .split()!): '#' режет комментарий (иначе слова комментария
    # становились «НГР» — баг первого прогона), из строки берём первый токен.
    ngrs = []
    for line in Path(sys.argv[1]).read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            ngrs.append(line.split()[0])
    print(f"headless-рендер: {len(ngrs)} НГР")
    got = 0
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        for i, ngr in enumerate(ngrs, 1):
            url = f"https://adilet.zan.kz/rus/docs/{ngr}"
            try:
                page.goto(url, wait_until="networkidle", timeout=60000)
                try:  # дождаться тела (первое «Статья» в DOM); не фатально
                    page.wait_for_selector("text=Статья", timeout=15000)
                except Exception:
                    pass
                html = page.content()
            except Exception as e:
                print(f"[{i}/{len(ngrs)}] {ngr}: РЕНДЕР-ОШИБКА {type(e).__name__}: {e}")
                continue
            sig, tlen = shape_sig(html)
            old = SOURCE / f"{ngr}.html"
            if old.exists():
                osig, otlen = shape_sig(old.read_text(encoding="utf-8", errors="replace"))
            else:
                osig, otlen = -1, 0
            verdict = "OK" if sig > 0 else "ПО-ПРЕЖНЕМУ-ТОНКИЙ"
            print(f"[{i}/{len(ngrs)}] {ngr}: sig {osig}->{sig}, текст {otlen}->{tlen}  => {verdict}")
            if sig > 0 and sig >= osig:
                if old.exists():
                    (BAK / f"{ngr}.html").write_text(
                        old.read_text(encoding="utf-8", errors="replace"), encoding="utf-8")
                old.write_text(html, encoding="utf-8")
                got += 1
            time.sleep(1.2)
        browser.close()
    print(f"\nсохранено рендеров с валидной структурой: {got}/{len(ngrs)}")


if __name__ == "__main__":
    main()
