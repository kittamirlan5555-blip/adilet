# -*- coding: utf-8 -*-
"""R3 БЛОК 5: хвосты прошлых раундов. READ-ONLY — финальные файлы НЕ трогаются.

python scripts/audit/r3_08_tails.py
-> reports/r3/tails_phrases16.md   (Класс 3 R2: фразы без НГР + вердикты)
-> reports/r3/tails_selfrefs18.md  (Класс 4 R2: самоотсылки наготове,
                                    применять ТОЛЬКО после вето-ответа Анары)
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import auditlib as al

sys.path.insert(0, str(HERE.parent))
import paths

QT = str.maketrans({"«": '"', "»": '"', "“": '"', "”": '"', "„": '"'})
RE_NOTE = re.compile(r'<(span|p)\b[^>]*class="note"[^>]*>.*?</\1\s*>', re.I | re.S)
RE_ART_HEAD = re.compile(r"Статья\s+(\d+(?:-\d+)*)\s*[.\s]")

# ── Класс 3: вердикты по фразам без НГР (кандидаты; в маппинг НЕ вносится) ──
VERDICTS = [
    (r"техническ\w+\s+регулировани", "Z2000000396",
     "ВЕБ 2026-06-11: закон «О техническом регулировании» №396-VI от "
     "30.12.2020, действует (ред. 01.01.2026)",
     "добавить A-ключ -> Z2000000396, линковать на корень"),
    (r"противодействи\w+\s+легализации", "Z090000191_",
     "ВЕБ 2026-06-11: страница Z090000191_ на adilet существует (закон "
     "№191-IV от 28.08.2009). Кандидат R2 «Z1600000191» — ОПЕЧАТКА, такого "
     "НГР на adilet нет. ОТЛИЧИЕ от уже внесённого ключа: в маппинге есть "
     "только B-ключ «Законом РК \"О противодействии легализации (отмыванию) "
     "доходов, полученных преступным путем, финансированию терроризма и "
     "финансированию распространения оружия массового уничтожения\"» -> "
     "Z090000191_; фразы notariat — A-семейство «законодательством РК о "
     "противодействии легализации…» (без слова «Закон» и без полного "
     "хвоста названия), поэтому ключом не покрываются",
     "добавить A-ключ(и) точным падежом -> Z090000191_"),
    (r"искусственн\w+\s+интеллект", "Z2500000230",
     "ВЕБ 2026-06-11: закон «Об искусственном интеллекте» №230-VIII от "
     "17.11.2025, ВВЕДЁН В ДЕЙСТВИЕ 18.01.2026 — свежий, действует",
     "добавить A-ключ -> Z2500000230, линковать на корень"),
    (r"государственно-частн\w+\s+партн", "Z1500000379",
     "кандидат по №379-V от 31.10.2015 «О ГЧП» — СВЕРИТЬ на adilet при внесении",
     "после сверки добавить A-ключ -> Z1500000379"),
    (r"государственной\s+служб", "Z1500000416",
     "кандидат по №416-V от 23.11.2015 «О государственной службе РК» — "
     "СВЕРИТЬ на adilet при внесении",
     "после сверки добавить A-ключ -> Z1500000416"),
    (r"об\s+информатизации", "Z1500000418",
     "наш же закон informatizacii (codes.json); в notariat это ВНЕШНЯЯ отсылка",
     "A-ключ -> Z1500000418 (корень)"),
    (r"обязательном\s+страховании\s+граж", "Z030000435_",
     "ВЕБ 2026-06-11: закон «Об обязательном страховании ГПО частных "
     "нотариусов» №435-II от 11.06.2003, действует",
     "добавить A-ключ -> Z030000435_"),
]


def class3_rows():
    """A-строки без ключа из текущих gap-отчётов informatizacii/notariat."""
    rows = []
    for slug in ("informatizacii", "notariat"):
        rp = paths.REPORTS / f"mapping_gap_{slug}.md"
        for line in rp.read_text(encoding="utf-8").splitlines():
            if not line.startswith("| A:"):
                continue
            cells = [c.strip() for c in line.split("|")]
            # | _ | семейство | фраза | ключ | спан |
            phrase, key = cells[2].strip("«»… "), cells[3]
            if key != "нет":
                continue
            # самоотсылки (класс 4) — в таблице 5.2, не здесь
            if slug == "informatizacii" and re.search(
                    r"об информатизации|в сфере информатизации", phrase):
                continue
            if slug == "notariat" and re.search(r"о нотариате", phrase):
                continue
            rows.append((slug, phrase))
    return rows


def main():
    # ── таблица фраз без НГР ──
    rows = class3_rows()
    L = ["# Блок 5.1 — фразы без НГР (Класс 3 раунда R2) — таблица вердиктов",
         "",
         "В npa_mapping НИЧЕГО не внесено (по заданию — только решения).",
         "Применение: после «да» владельца добавить ключи и прогнать линкер",
         "по laws3 ПОСЛЕ возврата документов от Анары.", "",
         "| № | документ | фраза (как в тексте) | кандидат-цель | проверка | рекомендация |",
         "|---|---|---|---|---|---|"]
    n = 0
    for slug, phrase in rows:
        verdict = None
        for rx, ngr, proof, rec in VERDICTS:
            if re.search(rx, phrase, re.I):
                verdict = (ngr, proof, rec)
                break
        n += 1
        if verdict:
            L.append(f"| {n} | {slug} | «{phrase[:70]}» | {verdict[0]} "
                     f"| {verdict[1][:150]} | {verdict[2]} |")
        else:
            L.append(f"| {n} | {slug} | «{phrase[:70]}» | — | кандидата нет "
                     f"| СТОП-вопрос исполнителю (НГР не гадаем, §5) |")
    (paths.REPORTS / "r3" / "tails_phrases16.md").write_text(
        "\n".join(L) + "\n", encoding="utf-8")
    print(f"фраз без НГР: {n} -> reports/r3/tails_phrases16.md")

    # ── самоотсылки (Класс 4) ──
    SELF = {
        "informatizacii": (r"законодательств\w*\s+Республики\s+Казахстан\s+"
                           r"(?:об\s+информатизации|в\s+сфере\s+информатизации)",
                           "#z2h",
                           "статья 2 «Законодательство РК в сфере информатизации» "
                           "(прецедент: флаги 14/19 R2 переведены на #z2h)"),
        "notariat": (r"законодательств\w*\s+Республики\s+Казахстан\s+о\s+нотариате",
                     None, "статья «Законодательство РК о нотариате» — якорь "
                           "определить по заголовку"),
        "obrazovanie": (r"законодательств\w*\s+Республики\s+Казахстан\s+в\s+"
                        r"области\s+(?:высшего\s+и\s*\(или\)\s*послевузовского\s+)?"
                        r"образования",
                        None, "статья «Законодательство РК в области образования» "
                              "— якорь определить по заголовку"),
    }
    M = ["# Блок 5.2 — самоотсылки laws3 (Класс 4 R2) — НАГОТОВЕ",
         "",
         "ПРИМЕНЯТЬ ТОЛЬКО после вето-ответа Анары по SDACHA_R2 (документы у неё",
         "на ревью). Правило §4: самоотсылка -> внутренний якорь статьи",
         "«Законодательство о X». READ-ONLY список.", "",
         "| № | документ | статья | фраза (plain) | цель по §4 |",
         "|---|---|---|---|---|"]
    k = 0
    for slug, (rx_s, target, note) in SELF.items():
        raw = (paths.FINAL / f"{slug}_structured.html").read_text(encoding="utf-8")
        # якорь статьи «Законодательство…», если цель не задана
        target_art = "2"
        if target is None:
            mh = re.search(r'<a id="(z[\w-]+)" name="\1"></a>\s*Статья\s+'
                           r"(\d+(?:-\d+)*)\s*\.\s*Законодательство", raw)
            if mh:
                target = f"#{mh.group(1)} (статья {mh.group(2)})"
                target_art = mh.group(2)
            else:
                target = "ЯКОРЬ НЕ НАЙДЕН — инжекция пустого <a id> по прецеденту УК/f03"
        tmap = al.TextMap(raw)
        notes = [(m.start(), m.end()) for m in RE_NOTE.finditer(raw)]
        links = [(m.start(2), m.end(2)) for m in al.RE_A_PAIR.finditer(raw)]
        rx = re.compile(rx_s, re.I)
        for m in rx.finditer(tmap.text):
            rs, re_ = tmap.pos[m.start()], tmap.pos[m.end() - 1] + 1
            if any(a <= rs and re_ <= b for a, b in notes):
                continue
            if any(cs <= rs and re_ <= ce for cs, ce in links):
                continue  # уже залинковано (флаги R2)
            head = "?"
            for hm in RE_ART_HEAD.finditer(tmap.text, 0, m.start()):
                head = hm.group(1)
            if head == target_art:
                continue  # вхождение внутри самой статьи-цели — не линкуем в себя
            k += 1
            M.append(f"| {k} | {slug} | ст.{head} | «{m.group(0)[:60]}» | {target} |")
        M.append(f"|  | {slug} |  | примечание | {note} |")
    (paths.REPORTS / "r3" / "tails_selfrefs18.md").write_text(
        "\n".join(M) + "\n", encoding="utf-8")
    print(f"самоотсылок plain: {k} -> reports/r3/tails_selfrefs18.md")


if __name__ == "__main__":
    main()
