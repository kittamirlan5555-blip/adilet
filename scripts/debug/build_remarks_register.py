"""
Parse all docx-extracted .txt files (Anara's per-codex remark lists) into
a single structured JSON of remarks + emit a human-readable Markdown register.

Output:
    data/reports/01_master_remarks.json
    data/reports/01_anara_master_remarks_register.md
"""
import os, re, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = ROOT / "anara_review" / "docx_extracted" / "en"
OUT_JSON = ROOT / "data" / "reports" / "01_master_remarks.json"
OUT_MD = ROOT / "data" / "reports" / "01_anara_master_remarks_register.md"

# Map of docx filename → code key. Use the LATEST version per codex.
LATEST_PER_CODE = {
    "appk": "appk.txt",
    "byudzhet": "byudzhet.txt",
    "ekologicheskiy": "ekologicheskiy.txt",     # both files identical
    "koap": "koap_2.txt",                      # (2) is latest per Telegram convention
    "predprinimatel": "predprinimatel_3.txt",
    "socialnyy": "socialnyy_2.txt",
    "trudovoy": "trudovoy.txt",
    "upk": "upk_1.txt",
    "zemelnyy": "zemelnyy_2.txt",
}

CODE_TITLES = {
    "appk": "Административный процедурно-процессуальный кодекс",
    "byudzhet": "Бюджетный кодекс",
    "ekologicheskiy": "Экологический кодекс",
    "koap": "Кодекс об административных правонарушениях",
    "predprinimatel": "Предпринимательский кодекс",
    "socialnyy": "Социальный кодекс",
    "trudovoy": "Трудовой кодекс",
    "upk": "Уголовно-процессуальный кодекс",
    "zemelnyy": "Земельный кодекс",
    "ugolovniy": "Уголовный кодекс",
    "nalog": "Налоговый кодекс",
    "grazhdanskiy": "Гражданский кодекс",
}

# Regex to match a leading place reference like:
#   пункт 5 статья 245
#   подпункт 36) пункт 1 статья 1
#   статья 143-1
#   пункт 5) статья 12
#   подпункт 1) пункт 9 статья 724
#   глава 38
PLACE_RE = re.compile(
    # Require dash/en-dash to be SURROUNDED BY WHITESPACE — otherwise hyphens
    # inside article numbers like "283-1" or "1-1" would be misread as separators.
    r"^\s*(?P<place>(?:Пункт|пункт|Подпункт|подпункт|Статья|статья|Глава|глава)[^\n]*?)\s+[\-–—]\s+(?P<rest>.*)$",
    re.UNICODE | re.DOTALL,
)


def classify(fragment: str) -> str:
    """Heuristic classification of a remark fragment text into a problem type."""
    txt = fragment.lower()
    has_external_code = any(t in txt for t in [
        "налогового кодекс", "налоговым кодекс",
        "гражданского кодекс", "гражданским кодекс",
        "уголовного кодекс", "уголовным кодекс",
        "уголовно-процессуального", "уголовно-процессуальным",
        "трудового кодекс", "трудовым кодекс",
        "земельного кодекс", "земельным кодекс",
        "экологического кодекс", "экологическим кодекс",
        "бюджетного кодекс", "бюджетным кодекс",
        "социального кодекс", "социальным кодекс",
        "предпринимательского кодекс", "предпринимательским кодекс",
        "административным процедурно", "административного процедурно",
        "о таможенном регулирован", "таможенном регулирован",
        "о здоровье народа", "о недрах и недропользован",
        "административных правонарушени", "об административных правонарушени",
        "гражданским процессуальным", "гражданского процессуального",
        "лесным кодекс", "лесного кодекс",
        "водным кодекс", "водного кодекс",
    ])
    has_external_law = any(t in txt for t in [
        "закон", "конституции", "конституцион",
    ]) and ("кодекс" not in txt[:60])
    has_inside_self = "настоящего кодекса" in txt or "настоящем кодексе" in txt or "настоящим кодексом" in txt
    has_inside_article = "настоящей статьи" in txt or "настоящей части" in txt or "настоящего пункта" in txt or "настоящей статье" in txt
    has_paragraph = "параграф" in txt or "раздел" in txt or "главой" in txt or "главы" in txt or "глава" in txt
    if has_external_code:
        return "EXTERNAL_LINK_MISSING_CROSSCODE"
    if has_external_law:
        return "EXTERNAL_LINK_MISSING_LAW"
    if has_inside_article and not has_inside_self:
        return "INTERNAL_LINK_MISSING_SELFREF"
    if has_inside_self and has_paragraph:
        return "INTERNAL_LINK_MISSING_SECTION_OR_PARAGRAPH"
    if has_inside_self:
        return "INTERNAL_LINK_MISSING_ARTICLE"
    return "UNKNOWN"


def parse_file(code: str, fname: str):
    """Parse a docx-extracted .txt file into a list of remark dicts."""
    fpath = SRC_DIR / fname
    if not fpath.exists():
        return []
    text = fpath.read_text(encoding="utf-8")
    # Trudovoy has a numbered table format ("1\n\nПодпункт 27 пункта 2 стать 23 …\n\n<long text>")
    # Other files have single-line "place - fragment" entries.
    remarks = []
    if code == "trudovoy":
        # Parse numbered blocks 1..N. Pattern: lookahead for ^\d+\n then "Подпункт/Пункт/Статья ... (отсутствует ссылка)"
        blocks = re.split(r"^\s*\d+\s*$", text, flags=re.MULTILINE)
        # blocks[0] is the header. blocks[1..] each correspond to numbered items.
        for i, block in enumerate(blocks[1:], 1):
            lines = [ln.strip() for ln in block.strip().splitlines() if ln.strip()]
            if not lines:
                continue
            # First line(s) before "(отсутствует ссылка)" are place
            place_lines = []
            text_lines = []
            seen_marker = False
            for ln in lines:
                if "(отсутствует ссылка)" in ln:
                    seen_marker = True
                    place_lines.append(ln.replace("(отсутствует ссылка)", "").strip())
                    continue
                if not seen_marker:
                    place_lines.append(ln)
                else:
                    text_lines.append(ln)
            place = " ".join(place_lines).strip()
            fragment = "\n".join(text_lines).strip()
            if place and fragment:
                remarks.append({
                    "id": f"{code}_{i:03d}",
                    "code": code,
                    "source": f"docx:{fname}",
                    "place_raw": place,
                    "fragment": fragment,
                    "problem_type": classify(fragment),
                })
        return remarks
    # Generic format: "<place> - <fragment>"
    idx = 0
    cur_lines = []
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line.strip():
            # flush
            blob = "\n".join(cur_lines).strip()
            cur_lines = []
            if not blob:
                continue
            m = PLACE_RE.match(blob)
            if m:
                idx += 1
                place = m.group("place").strip()
                fragment = m.group("rest").strip()
                remarks.append({
                    "id": f"{code}_{idx:03d}",
                    "code": code,
                    "source": f"docx:{fname}",
                    "place_raw": place,
                    "fragment": fragment,
                    "problem_type": classify(fragment),
                })
            else:
                # Multi-line wrap of previous remark? attach to previous
                if remarks:
                    remarks[-1]["fragment"] += " " + blob
        else:
            cur_lines.append(line)
    # final flush
    blob = "\n".join(cur_lines).strip()
    if blob:
        m = PLACE_RE.match(blob)
        if m:
            idx += 1
            place = m.group("place").strip()
            fragment = m.group("rest").strip()
            remarks.append({
                "id": f"{code}_{idx:03d}",
                "code": code,
                "source": f"docx:{fname}",
                "place_raw": place,
                "fragment": fragment,
                "problem_type": classify(fragment),
            })
    return remarks


# Manually-added remarks for codes without docx (nalog, grazhdanskiy, ugolovniy)
# and chat-only remarks for codes that do have docx (extra items / photo issues).
MANUAL_REMARKS = [
    # ---- Nalog (chat 05.05 + 15.05) ----
    {"code": "nalog", "source": "chat:2026-05-05", "place_raw": "подпункт 1) пункт 3 статья 13",
     "fragment": "законодательством Республики Казахстан о трансфертном ценообразовании"},
    {"code": "nalog", "source": "chat:2026-05-05", "place_raw": "пункт 2 статья 14",
     "fragment": "в соответствии с законодательством Республики Казахстан о трансфертном ценообразовании"},
    {"code": "nalog", "source": "chat:2026-05-05", "place_raw": "подпункт 1) пункт 2 статья 15",
     "fragment": "законодательством Республики Казахстан субъектом здравоохранения, имеющим лицензию на медицинскую деятельность (Закон РК О здоровье народа и системе здравоохранения)"},
    {"code": "nalog", "source": "chat:2026-05-05", "place_raw": "пункт 1 статья 16",
     "fragment": "законодательством Республики Казахстан о сельскохозяйственных кооперативах (Закон РК О сельскохозяйственных кооперативах)"},
    {"code": "nalog", "source": "chat:2026-05-05", "place_raw": "подпункт 1) пункт 1 статья 17",
     "fragment": "законодательством Республики Казахстан об инновационном кластере (Закон РК Об инновационном кластере «Астана Хаб»)"},
    {"code": "nalog", "source": "chat:2026-05-05", "place_raw": "пункт 8) статья 21",
     "fragment": "в соответствии с Законом Республики Казахстан \"О стандартизации\""},
    {"code": "nalog", "source": "chat:2026-05-05", "place_raw": "пункт 8 статья 43",
     "fragment": "законодательством Республики Казахстан о реабилитации и банкротстве"},
    {"code": "nalog", "source": "chat:2026-05-05", "place_raw": "подпункт 2) пункт 5 статья 44",
     "fragment": "законодательством Республики Казахстан о социальной защите"},
    {"code": "nalog", "source": "chat:2026-05-05", "place_raw": "подпункт 10 пункт 2 статья 45",
     "fragment": "законодательством Республики Казахстан о реабилитации и банкротстве"},
    {"code": "nalog", "source": "chat:2026-05-05", "place_raw": "подпункт 7) пункт 3 статья 45",
     "fragment": "законодательством Республики Казахстан о восстановлении платежеспособности и банкротстве граждан Республики Казахстан"},
    {"code": "nalog", "source": "chat:2026-05-05", "place_raw": "пункт 2 статья 49",
     "fragment": "законодательства Республики Казахстан об электронном документе и электронной цифровой подписи"},
    {"code": "nalog", "source": "chat:2026-05-05", "place_raw": "подпункт 2) пункт 1 статья 275",
     "fragment": "в соответствии с Законом Республики Казахстан \"О концессиях\""},
    {"code": "nalog", "source": "chat:2026-05-05", "place_raw": "подпункт 3) пункт 2 статья 320",
     "fragment": "в соответствии с пунктом 5 настоящей статьи"},
    {"code": "nalog", "source": "chat:2026-05-05", "place_raw": "подпункт 7) пункт 1 статья 337",
     "fragment": "пункта 2 и [...] настоящей статьи"},
    {"code": "nalog", "source": "chat:2026-05-05", "place_raw": "подпункт 2) пункт 2 статья 357",
     "fragment": "кроме соответствующих подпункту 1) настоящего пункта"},
    {"code": "nalog", "source": "chat:2026-05-05 + 15.05", "place_raw": "подпункт 4) статья 363",
     "fragment": "установленном подпунктом 4) настоящей статьи, с доходов"},
    {"code": "nalog", "source": "chat:2026-05-05", "place_raw": "подпункт 2) пункт 5 статья 422",
     "fragment": "в соответствии с Конституционным законом Республики Казахстан \"О выборах в Республике Казахстан\""},
    {"code": "nalog", "source": "chat:2026-05-05", "place_raw": "подпункт 10) пункт 1 статья 479",
     "fragment": "в соответствии с Законом Республики Казахстан \"О драгоценных металлах и драгоценных камнях\""},
    {"code": "nalog", "source": "chat:2026-05-05", "place_raw": "подпункт 12) пункт 1 статья 479",
     "fragment": "в соответствии с Законом Республики Казахстан \"Об официальной помощи развитию\""},
    {"code": "nalog", "source": "chat:2026-05-05 + 15.05", "place_raw": "подпункт 1) пункт 9 статья 724",
     "fragment": "имущественного дохода – в соответствии с параграфом 3 раздела 6 настоящего Кодекса"},
    {"code": "nalog", "source": "chat:2026-05-05 + 15.05", "place_raw": "пункт 1 статья 820",
     "fragment": "в соответствии с положениями раздела 6 настоящего Кодекса"},

    # ---- Grazhdanskiy (chat 04.05 + 15.05) ----
    {"code": "grazhdanskiy", "source": "chat:2026-05-04", "place_raw": "пункт 1 статья 3",
     "fragment": "указанные в пунктах 1, [...] настоящей статьи"},
    {"code": "grazhdanskiy", "source": "chat:2026-05-04", "place_raw": "пункт 1 статья 5",
     "fragment": "когда предусмотренные пунктами 1 и [...] настоящей статьи"},
    {"code": "grazhdanskiy", "source": "chat:2026-05-04", "place_raw": "пункт 1 статья 20-1",
     "fragment": "Законом Республики Казахстан \"О восстановлении платежеспособности и банкротстве граждан Республики Казахстан\""},
    {"code": "grazhdanskiy", "source": "chat:2026-05-04", "place_raw": "пункт 2 статья 21",
     "fragment": "законодательством Республики Казахстан о реабилитации и банкротстве (Закон РК О реабилитации и банкротстве)"},
    {"code": "grazhdanskiy", "source": "chat:2026-05-04", "place_raw": "статья 21-1",
     "fragment": "законодательством Республики Казахстан о реабилитации и банкротстве (Закон РК О реабилитации и банкротстве)"},
    {"code": "grazhdanskiy", "source": "chat:2026-05-04", "place_raw": "пункт 4 статья 49",
     "fragment": "законодательством Республики Казахстан о реабилитации и банкротстве"},
    {"code": "grazhdanskiy", "source": "chat:2026-05-04 + 16:11", "place_raw": "пункт 6 статья 50",
     "fragment": "законодательством Республики Казахстан об акционерных обществах (Закон РК Об акционерных обществах)"},
    {"code": "grazhdanskiy", "source": "chat:2026-05-04", "place_raw": "статья 52",
     "fragment": "законодательством Республики Казахстан о реабилитации и банкротстве"},
    {"code": "grazhdanskiy", "source": "chat:2026-05-04", "place_raw": "статья 54",
     "fragment": "законодательством Республики Казахстан о реабилитации и банкротстве"},
    {"code": "grazhdanskiy", "source": "chat:2026-05-04", "place_raw": "пункт 6 статья 58",
     "fragment": "указанных в пунктах 4 и [...] настоящей статьи"},
    {"code": "grazhdanskiy", "source": "chat:2026-05-04", "place_raw": "статья 64",
     "fragment": "законодательством Республики Казахстан о микрофинансовой деятельности (Закон РК О микрофинансовой деятельности)"},
    {"code": "grazhdanskiy", "source": "chat:2026-05-04", "place_raw": "статья 64 (вариант 2)",
     "fragment": "законодательством Республики Казахстан о коллекторской деятельности (Закон РК О коллекторской деятельности)"},
    {"code": "grazhdanskiy", "source": "chat:2026-05-04", "place_raw": "пункт 2 статья 74",
     "fragment": "законодательством Республики Казахстан о микрофинансовой деятельности + о коллекторской деятельности"},
    {"code": "grazhdanskiy", "source": "chat:2026-05-04", "place_raw": "статья 78",
     "fragment": "о микрофинансовой деятельности + о коллекторской деятельности + о платежах и платежных системах"},
    {"code": "grazhdanskiy", "source": "chat:2026-05-04 + 16:11", "place_raw": "статья 82",
     "fragment": "Законом Республики Казахстан \"О товариществах с ограниченной и дополнительной ответственностью\""},
    {"code": "grazhdanskiy", "source": "chat:2026-05-04", "place_raw": "пункт 3 статья 132",
     "fragment": "законодательным актом Республики Казахстан об ипотеке недвижимого имущества"},
    {"code": "grazhdanskiy", "source": "chat:2026-05-04", "place_raw": "пункт 1 статья 133",
     "fragment": "законодательным актом Республики Казахстан об ипотеке недвижимого имущества"},
    {"code": "grazhdanskiy", "source": "chat:2026-05-04", "place_raw": "пункт 3 статья 139",
     "fragment": "законодательством Республики Казахстан о рынке ценных бумаг"},
    {"code": "grazhdanskiy", "source": "chat:2026-05-04", "place_raw": "пункт 4 статья 156",
     "fragment": "Законом Республики Казахстан \"О противодействии легализации (отмыванию) доходов…\""},
    {"code": "grazhdanskiy", "source": "chat:2026-05-04", "place_raw": "пункт 7 статья 157-1",
     "fragment": "предусмотренных пунктами 5 и [...] настоящей статьи"},
    {"code": "grazhdanskiy", "source": "chat:2026-05-04", "place_raw": "пункт 8 статья 159",
     "fragment": "или отменительного условия (статья 150 настоящего Кодекса)"},
    {"code": "grazhdanskiy", "source": "chat:2026-05-04", "place_raw": "пункт 12 статья 159",
     "fragment": "сделки, предусмотренные пунктами 3, [...] настоящей статьи"},
    {"code": "grazhdanskiy", "source": "chat:2026-05-04", "place_raw": "пункт 2 статья 162",
     "fragment": "предусмотренным пунктами 9 и [...] настоящей статьи"},
    {"code": "grazhdanskiy", "source": "chat:2026-05-04", "place_raw": "пункт 1 статья 171",
     "fragment": "указанным в пунктах 5 и [...] настоящей статьи"},
    {"code": "grazhdanskiy", "source": "chat:2026-05-04", "place_raw": "пункт 3 статья 178",
     "fragment": "Правила статей 177, 179-186 настоящего Кодекса"},
    {"code": "grazhdanskiy", "source": "chat:2026-05-04 + 16:11", "place_raw": "подпункт 6) пункт 1 статья 182",
     "fragment": "в соответствии с законодательством Республики Казахстан о возврате государству незаконно приобретенных активов"},
    {"code": "grazhdanskiy", "source": "chat:2026-05-04", "place_raw": "пункт 6 статья 192",
     "fragment": "законодательным актом Республики Казахстан о государственном имуществе"},
    {"code": "grazhdanskiy", "source": "chat:2026-05-04", "place_raw": "пункт 7 статья 192",
     "fragment": "законодательным актом Республики Казахстан о государственном имуществе"},
    {"code": "grazhdanskiy", "source": "chat:2026-05-04", "place_raw": "пункт 2 статья 196",
     "fragment": "законодательным актом Республики Казахстан о государственном имуществе"},
    {"code": "grazhdanskiy", "source": "chat:2026-05-04 + 16:11", "place_raw": "пункт 2 статья 202",
     "fragment": "определяются законами Республики Казахстан \"О государственном имуществе\" и …"},
    {"code": "grazhdanskiy", "source": "chat:2026-05-04", "place_raw": "пункт 7 статья 209",
     "fragment": "законодательным актом Республики Казахстан об инвестиционных и венчурных фондах"},
    {"code": "grazhdanskiy", "source": "chat:2026-05-04", "place_raw": "пункт 5 статья 218",
     "fragment": "в соответствии с пунктами 3 и [...] настоящей статьи"},
    {"code": "grazhdanskiy", "source": "chat:2026-05-04", "place_raw": "пункт 4 статья 220",
     "fragment": "Пункты 1-3 настоящей статьи"},
    {"code": "grazhdanskiy", "source": "chat:2026-05-04", "place_raw": "пункт 3 статья 225",
     "fragment": "предусмотренных пунктами 1 и [...] настоящей статьи"},
    {"code": "grazhdanskiy", "source": "chat:2026-05-04", "place_raw": "статья 229",
     "fragment": "законодательством Республики Казахстан о проектном финансировании и секьюритизации"},
    {"code": "grazhdanskiy", "source": "chat:2026-05-04", "place_raw": "пункт 5 статья 235",
     "fragment": "регулируются Законом Республики Казахстан \"О долевом участии в жилищном строительстве\""},
    {"code": "grazhdanskiy", "source": "chat:2026-05-04", "place_raw": "пункт 2 статья 244",
     "fragment": "предусмотренных пунктами 3 и [...] настоящей статьи"},
    {"code": "grazhdanskiy", "source": "chat:2026-05-04", "place_raw": "подпункт 9) пункт 2 статья 249",
     "fragment": "о возврате государству незаконно приобретенных активов"},
    {"code": "grazhdanskiy", "source": "chat:2026-05-04", "place_raw": "подпункт 1) пункт 3 статья 249",
     "fragment": "законодательным актом Республики Казахстан о государственном имуществе"},
    {"code": "grazhdanskiy", "source": "chat:2026-05-04", "place_raw": "статья 258",
     "fragment": "установленным статьями 249-257 настоящего Кодекса"},
    {"code": "grazhdanskiy", "source": "chat:2026-05-04", "place_raw": "пункт 1 статья 263",
     "fragment": "Истребуя имущество на основании статей 260, 261 настоящего Кодекса"},
    {"code": "grazhdanskiy", "source": "chat:2026-05-04", "place_raw": "статья 265",
     "fragment": "предусмотренные статьями 259-264 настоящего Кодекса"},
    {"code": "grazhdanskiy", "source": "chat:2026-05-04 + 16:11", "place_raw": "пункт 2 статья 267",
     "fragment": "в соответствии с правилами пункта 1 [...] настоящей статьи"},
    {"code": "grazhdanskiy", "source": "chat:2026-05-04 + 16:11", "place_raw": "подпункт 2) пункт 2 статья 321",
     "fragment": "подпунктами 1 и [...] настоящего пункта"},
    {"code": "grazhdanskiy", "source": "chat:2026-05-04", "place_raw": "пункт 1 статья 282",
     "fragment": "законодательством Республики Казахстан о платежах и платежных системах"},
    {"code": "grazhdanskiy", "source": "chat:2026-05-04", "place_raw": "пункт 2 статья 282",
     "fragment": "банковским законодательством + о микрофинансовой деятельности"},
    {"code": "grazhdanskiy", "source": "chat:2026-05-04", "place_raw": "пункт 2 статья 291",
     "fragment": "законодательством Республики Казахстан о нотариате"},
    {"code": "grazhdanskiy", "source": "chat:2026-05-04", "place_raw": "пункт 2 статья 318",
     "fragment": "законодательным актом Республики Казахстан об ипотеке недвижимого имущества"},
    {"code": "grazhdanskiy", "source": "chat:2026-05-04", "place_raw": "пункт 1 статья 328",
     "fragment": "законодательством Республики Казахстан о микрофинансовой деятельности"},
    {"code": "grazhdanskiy", "source": "chat:2026-05-04 + 15.05", "place_raw": "пункт 2-1 статья 328",
     "fragment": "установленном Законом Республики Казахстан \"О микрофинансовой деятельности\""},
    {"code": "grazhdanskiy", "source": "chat:2026-05-04", "place_raw": "пункт 3 статья 334",
     "fragment": "установленные пунктами 1 и [...] настоящей статьи"},
    {"code": "grazhdanskiy", "source": "chat:2026-05-04", "place_raw": "пункт 3 статья 348",
     "fragment": "содержащиеся в пунктах 1 и [...] настоящей статьи"},
    {"code": "grazhdanskiy", "source": "chat:2026-05-04 + 16:11", "place_raw": "пункт 1-1 статья 380",
     "fragment": "без соблюдения требований Закона Республики Казахстан \"О долевом участии в жилищном строительстве\""},
    {"code": "grazhdanskiy", "source": "chat:2026-05-04 + 16:11", "place_raw": "пункт 8 статья 390",
     "fragment": "без соблюдения требований Закона Республики Казахстан \"О долевом участии в жилищном строительстве\""},
    {"code": "grazhdanskiy", "source": "chat:2026-05-04", "place_raw": "статья 400",
     "fragment": "В случаях, предусмотренных в пунктах 2 и [...] настоящей статьи"},
    {"code": "grazhdanskiy", "source": "chat:2026-05-04 + 16:11", "place_raw": "подпункт 2) пункт 2 статья 404",
     "fragment": "признания в установленном порядке другой стороны банкротом + о реабилитации и банкротстве"},
    # Image-based (sketch) for ст.50:
    {"code": "grazhdanskiy", "source": "photo:photo_10@19-05-2026", "place_raw": "статья 50",
     "fragment": "TOO_MUCH_TEXT_LINKED — ссылка захватывает слишком много текста (включая «настоящего»)"},

    # ---- Ugolovniy (chat 13.04 + 14.04 + 20.04 + 22.04 + 19.05 photo) ----
    {"code": "ugolovniy", "source": "chat:2026-04-13", "place_raw": "пункт 1-1 статья 3",
     "fragment": "не кликабельны статьи — список статей в скобках"},
    {"code": "ugolovniy", "source": "chat:2026-04-13", "place_raw": "пункт 3) статья 3",
     "fragment": "не кликабельны статьи — список: 189, 190, 194, 195, 202, 204, 233-1, 324, 325, 326, 328, 329, 330, 332, 333, 334, 337, 339, 342, 343"},
    {"code": "ugolovniy", "source": "chat:2026-04-13", "place_raw": "подпункт 5) пункт 2 статья 48",
     "fragment": "указанные в пунктах 1), 2), 3) и 4) настоящей части"},
    {"code": "ugolovniy", "source": "chat:2026-04-13", "place_raw": "пункт 3-2 статья 120",
     "fragment": "или 3-1 настоящей статьи"},
    {"code": "ugolovniy", "source": "chat:2026-04-13", "place_raw": "пункт 3-2 статья 121",
     "fragment": "или 3-1 настоящей статьи"},
    {"code": "ugolovniy", "source": "chat:2026-04-13", "place_raw": "пункт 4 статья 121",
     "fragment": "части 3-1 и частью 3-2 настоящей статьи"},
    {"code": "ugolovniy", "source": "chat:2026-04-13", "place_raw": "пункт 2 статья 150",
     "fragment": "1-1 настоящей статьи"},
    {"code": "ugolovniy", "source": "chat:2026-04-13", "place_raw": "пункт 3 статья 206",
     "fragment": "или 2-1 настоящей статьи"},
    {"code": "ugolovniy", "source": "chat:2026-04-13", "place_raw": "пункт 3 статья 207",
     "fragment": "или 2-1 настоящей статьи"},
    {"code": "ugolovniy", "source": "chat:2026-04-13", "place_raw": "пункт 2 статья 249",
     "fragment": "1-1 настоящей статьи"},
    {"code": "ugolovniy", "source": "chat:2026-04-13", "place_raw": "пункт 3 статья 249",
     "fragment": "1-1 или второй настоящей статьи"},
    {"code": "ugolovniy", "source": "chat:2026-04-13", "place_raw": "пункт 2 статья 339",
     "fragment": "или 1-1 настоящей статьи"},
    {"code": "ugolovniy", "source": "chat:2026-04-13", "place_raw": "пункт 3 статья 339",
     "fragment": "или 1-1 настоящей статьи"},
    {"code": "ugolovniy", "source": "chat:2026-04-13", "place_raw": "пункт 4 статья 361",
     "fragment": "2-1 или … настоящей статьи"},
    {"code": "ugolovniy", "source": "chat:2026-04-13", "place_raw": "пункт 2 статья 366",
     "fragment": "и 1-1 настоящей статьи"},
    {"code": "ugolovniy", "source": "chat:2026-04-13", "place_raw": "пункт 3 статья 366",
     "fragment": "1-1 или … настоящей статьи"},
    {"code": "ugolovniy", "source": "chat:2026-04-13", "place_raw": "пункт 4 статья 366",
     "fragment": "1-1 настоящей статьи"},
    {"code": "ugolovniy", "source": "chat:2026-04-13", "place_raw": "пункт 4 статья 370",
     "fragment": "2-1 или … настоящей статьи"},
    {"code": "ugolovniy", "source": "chat:2026-04-13", "place_raw": "пункт 2 статья 392",
     "fragment": "или 1-1 настоящей статьи"},
    {"code": "ugolovniy", "source": "chat:2026-04-13", "place_raw": "пункт 2 статья 438",
     "fragment": "или 1-1 настоящей статьи"},
    {"code": "ugolovniy", "source": "chat:2026-04-13", "place_raw": "пункт 3 статья 438",
     "fragment": "1-1 или … настоящей статьи"},
    {"code": "ugolovniy", "source": "chat:2026-04-13", "place_raw": "пункт 4 статья 438",
     "fragment": "1-1 настоящей статьи"},
    {"code": "ugolovniy", "source": "chat:2026-04-13", "place_raw": "пункт 2 статья 439",
     "fragment": "или 1-1 настоящей статьи"},
    {"code": "ugolovniy", "source": "chat:2026-04-13", "place_raw": "пункт 3 статья 439",
     "fragment": "1-1 или … настоящей статьи"},
    {"code": "ugolovniy", "source": "chat:2026-04-13", "place_raw": "пункт 4 статья 439",
     "fragment": "1-1 настоящей статьи"},
    {"code": "ugolovniy", "source": "chat:2026-04-13", "place_raw": "пункт 3 статья 440",
     "fragment": "или 2-1 настоящей статьи"},
    {"code": "ugolovniy", "source": "chat:2026-04-13", "place_raw": "пункт 4 статья 440",
     "fragment": "2-1 или … настоящей статьи"},
    {"code": "ugolovniy", "source": "chat:2026-04-15", "place_raw": "пункт 1-1 статья 467",
     "fragment": "и пунктом 1) части 2-1 настоящей статьи"},
    {"code": "ugolovniy", "source": "chat:2026-04-20", "place_raw": "подпункт 2) пункт 5 статья 48",
     "fragment": "в соответствии с Законом Республики Казахстан \"Об амнистии граждан Республики Казахстан, оралманов и лиц, имеющих вид на жительство в Республике Казахстан, в связи с легализацией ими имущества\""},
    {"code": "ugolovniy", "source": "chat:2026-04-20", "place_raw": "пункт 1 статья 218-1",
     "fragment": "Законом Республики Казахстан \"О возврате государству незаконно приобретенных активов\""},
    {"code": "ugolovniy", "source": "chat:2026-04-20", "place_raw": "пункт 2 статья 218-1",
     "fragment": "Законом Республики Казахстан \"О возврате государству незаконно приобретенных активов\""},
    {"code": "ugolovniy", "source": "chat:2026-04-20", "place_raw": "пункт 4 статья 223",
     "fragment": "Законом Республики Казахстан \"Об амнистии граждан Республики Казахстан, оралманов и лиц, имеющих вид на жительство в Республике Казахстан, в связи с легализацией ими имущества\""},
    {"code": "ugolovniy", "source": "chat:2026-04-20", "place_raw": "подпункт 2) пункт 4 статья 361",
     "fragment": "Законом Республики Казахстан \"Об амнистии граждан Республики Казахстан…\""},
    {"code": "ugolovniy", "source": "chat:2026-04-20", "place_raw": "подпункт 4) пункт 3 статья 365",
     "fragment": "Законом Республики Казахстан \"Об амнистии граждан Республики Казахстан…\""},
    {"code": "ugolovniy", "source": "chat:2026-04-22", "place_raw": "статья 98-1",
     "fragment": "законодательством Республики Казахстан о Фонде компенсации потерпевшим (Закон РК О Фонде компенсации потерпевшим)"},
    {"code": "ugolovniy", "source": "chat:2026-04-22", "place_raw": "статья 98-2",
     "fragment": "законодательством Республики Казахстан о Фонде компенсации потерпевшим"},
    {"code": "ugolovniy", "source": "photo:photo_6@19-05-2026", "place_raw": "статья 3 пункт 1-1 (фото)",
     "fragment": "Кликабельность списка статей: 116, 125, 126, 128, 134, 135, 308, 309 в скобках (предусмотренные статьями…)"},

    # ---- Trudovoy: additional from chat 02.04, 14.04, 17.04, 20.04, 22.04, 15.05 not present in docx ----
    {"code": "trudovoy", "source": "chat:2026-04-02 12:52 + 2026-05-15", "place_raw": "пункт 2 статья 146-1",
     "fragment": "предусмотренного подпунктом 2) пункта 1 статьи 30 настоящего Кодекса (статью 30 кликабельным нужно сделать)"},
    {"code": "trudovoy", "source": "chat:2026-05-15", "place_raw": "пункт 4-1 статья 159",
     "fragment": "установленных Законом Республики Казахстан \"О противодействии коррупции\""},
    {"code": "trudovoy", "source": "chat:2026-05-15", "place_raw": "статья 143-1",
     "fragment": "Труд лиц, на которых распространяются требования Закона Республики Казахстан \"О противодействии коррупции\""},
    {"code": "trudovoy", "source": "chat:2026-04-17", "place_raw": "пункт 2 статья 137-1",
     "fragment": "Закона Республики Казахстан \"Об обязательном страховании работника от несчастных случаев при исполнении им трудовых (служебных) обязанностей\""},
    {"code": "trudovoy", "source": "chat:2026-04-22", "place_raw": "подпункт 41-7) пункт 1 статья 16",
     "fragment": "Закон Республики Казахстан \"О персональных данных и их защите\""},
    {"code": "trudovoy", "source": "chat:2026-04-02", "place_raw": "пункт 1 статья 54",
     "fragment": "пунктом 1-1 статьи 52 настоящего Кодекса"},
    {"code": "trudovoy", "source": "chat:2026-04-14", "place_raw": "трудовой текст",
     "fragment": "В файле trudovoy_ready вблизи 4-1 настоящей статьи (ст.159 / 4-1 части) — артефакт от href, нужно проверить, что текст не поломан"},

    # ---- Socialnyy: photo 19.05 + chat ----
    {"code": "socialnyy", "source": "photo:photo_5@19-05-2026 + chat 19.05",
     "place_raw": "пункт 5 статья 245",
     "fragment": "определенный статьей 821 Налогового кодекса Республики Казахстан — кликабельным должен быть ТОЛЬКО фрагмент 'статьей 821 Налогового кодекса Республики Казахстан', НЕ весь пункт"},
    {"code": "socialnyy", "source": "photo:photo_5@19-05-2026 + chat 19.05",
     "place_raw": "пункт 1 статья 245",
     "fragment": "TOO_MUCH_TEXT_LINKED — много выделенных пунктов"},
    {"code": "socialnyy", "source": "chat:2026-05-19", "place_raw": "пункт 10 статья 248",
     "fragment": "TOO_MUCH_TEXT_LINKED — аналогично п.1/5 ст.245"},
    {"code": "socialnyy", "source": "chat:2026-05-19", "place_raw": "пункт 5 статья 246",
     "fragment": "установленные пунктом 5 статьи 823 Налогового кодекса Республики Казахстан — кликабельным должен быть только этот фрагмент"},

    # ---- Zemelnyy: photo 19.05 ----
    {"code": "zemelnyy", "source": "photo:photo_7@19-05-2026", "place_raw": "статья 81 (фото)",
     "fragment": "TOO_MUCH_TEXT_LINKED — слова 'настоящего' и 'настоящим' оказались внутри ссылки"},

    # ---- APPK: photo 19.05 ----
    {"code": "appk", "source": "photo:photo_8@19-05-2026", "place_raw": "статья 107 (фото)",
     "fragment": "TOO_MUCH_TEXT_LINKED — слова 'настоящем', 'настоящим' внутри ссылок"},
    {"code": "appk", "source": "photo:photo_9@19-05-2026 + chat", "place_raw": "статья 115 (структура)",
     "fragment": "ARTICLE_TITLE_NOT_BOLD — заголовок 'Статья 115. ...' не выделен жирным как остальные статьи"},
    # The same global check applies to all codes, but record once globally:
    {"code": "_GLOBAL", "source": "chat:2026-05-19 12:18",
     "place_raw": "все кодексы — заголовки статей",
     "fragment": "в кодексах все статьи выделены жирным черным, а здесь статья 115 не выделена сбилась, такое нужно тоже поправить — проверить во всех кодексах"},

    # ---- UPK: regression note ----
    {"code": "upk", "source": "chat:2026-05-15 00:59 + 2026-05-19", "place_raw": "ВЕСЬ КОДЕКС",
     "fragment": "Регрессия: 'у вас здесь УПК кривой, хуже раннее высланного УПК; данные замечания не исправлены'. Все замечания из УПК.docx должны быть закрыты заново."},
]


def main():
    all_remarks = []
    for code, fname in LATEST_PER_CODE.items():
        all_remarks.extend(parse_file(code, fname))

    # Then add manual remarks with auto IDs per code
    extra_counters = {}
    for r in MANUAL_REMARKS:
        c = r["code"]
        # find max existing index for that code
        existing = [int(rr["id"].rsplit("_", 1)[1]) for rr in all_remarks if rr["code"] == c]
        n = (max(existing) if existing else 0)
        n += 1
        extra_counters[c] = n
        # but cluster sequentially: continue incrementing
        # actually maintain per code counters
    # second pass cleaner
    code_counters = {}
    for r in all_remarks:
        c = r["code"]
        idx = int(r["id"].rsplit("_", 1)[1])
        code_counters[c] = max(code_counters.get(c, 0), idx)
    for r in MANUAL_REMARKS:
        c = r["code"]
        code_counters[c] = code_counters.get(c, 0) + 1
        rid = f"{c}_{code_counters[c]:03d}"
        full = {"id": rid, "code": c, "source": r["source"], "place_raw": r["place_raw"],
                "fragment": r["fragment"], "problem_type": classify(r["fragment"])}
        # Special types for non-text classification
        frag_l = r["fragment"].lower()
        if "too_much_text_linked" in frag_l or "слишком много" in frag_l or "много выделенных" in frag_l:
            full["problem_type"] = "TOO_MUCH_TEXT_LINKED"
        if "article_title_not_bold" in frag_l or "не выделен жирным" in frag_l:
            full["problem_type"] = "ARTICLE_TITLE_NOT_BOLD"
        if "регрессия" in frag_l:
            full["problem_type"] = "REGRESSION"
        if "не кликабельн" in frag_l:
            full["problem_type"] = "INTERNAL_LINK_MISSING_LIST"
        all_remarks.append(full)

    # Save JSON
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(all_remarks, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(all_remarks)} remarks → {OUT_JSON.relative_to(ROOT)}")

    # Write Markdown
    md = []
    md.append("# Единый реестр замечаний Анары (Этап 2)\n")
    md.append("Источник истины: docx-замечания (по 1 файлу на кодекс, самая поздняя версия) + сообщения и фото из чата 10.03–19.05.2026.\n")
    md.append("Полный машиночитаемый источник: `data/reports/01_master_remarks.json`.\n")
    md.append("\n## Типы проблемы\n")
    md.append("- INTERNAL_LINK_MISSING_ARTICLE — отсутствует внутренняя ссылка на «статью N настоящего Кодекса».\n")
    md.append("- INTERNAL_LINK_MISSING_SELFREF — отсутствует внутренняя ссылка на «N настоящей статьи / пункт настоящей статьи / часть N настоящей статьи».\n")
    md.append("- INTERNAL_LINK_MISSING_SECTION_OR_PARAGRAPH — отсутствует внутренняя ссылка на «параграфом / разделом / главой … настоящего Кодекса».\n")
    md.append("- INTERNAL_LINK_MISSING_LIST — список из множества статей внутри `(статьями A, B, C ...)` не кликабельные.\n")
    md.append("- EXTERNAL_LINK_MISSING_CROSSCODE — отсутствует cross-code ссылка на другой кодекс РК.\n")
    md.append("- EXTERNAL_LINK_MISSING_LAW — отсутствует ссылка на внешний закон РК.\n")
    md.append("- TOO_MUCH_TEXT_LINKED — слишком большой фрагмент текста стал ссылкой (захвачено лишнее).\n")
    md.append("- ARTICLE_TITLE_NOT_BOLD — заголовок статьи не отформатирован как у других статей (структура сбилась).\n")
    md.append("- REGRESSION — целиком кодекс регрессировал относительно предыдущей версии.\n")
    md.append("- UNKNOWN — нужна ручная классификация.\n")
    # Group by code
    by_code = {}
    for r in all_remarks:
        by_code.setdefault(r["code"], []).append(r)
    summary = []
    summary.append("\n## Сводка по кодексам\n\n")
    summary.append("| Кодекс | Замечаний | Внутренние | Внешние | TOO_MUCH | Структура | Прочее |\n|---|---|---|---|---|---|---|\n")
    for code in sorted(by_code):
        lst = by_code[code]
        title = CODE_TITLES.get(code, code)
        internal = sum(1 for r in lst if r["problem_type"].startswith("INTERNAL"))
        external = sum(1 for r in lst if r["problem_type"].startswith("EXTERNAL"))
        too_much = sum(1 for r in lst if r["problem_type"] == "TOO_MUCH_TEXT_LINKED")
        struct = sum(1 for r in lst if r["problem_type"] == "ARTICLE_TITLE_NOT_BOLD")
        other = len(lst) - internal - external - too_much - struct
        summary.append(f"| {title} ({code}) | {len(lst)} | {internal} | {external} | {too_much} | {struct} | {other} |\n")
    md.append("".join(summary))

    for code in sorted(by_code):
        title = CODE_TITLES.get(code, code)
        md.append(f"\n## {title} (`{code}`) — {len(by_code[code])} замечаний\n\n")
        md.append("| # | ID | Источник | Место | Фрагмент | Тип |\n|---|---|---|---|---|---|\n")
        for i, r in enumerate(by_code[code], 1):
            frag = r["fragment"].replace("\n", " ").replace("|", "\\|")
            if len(frag) > 220:
                frag = frag[:217] + "…"
            place = r["place_raw"].replace("|", "\\|")
            md.append(f"| {i} | `{r['id']}` | {r['source']} | {place} | {frag} | {r['problem_type']} |\n")

    OUT_MD.write_text("".join(md), encoding="utf-8")
    print(f"Wrote markdown → {OUT_MD.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
