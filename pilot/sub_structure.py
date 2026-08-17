# -*- coding: utf-8 -*-
"""Структуризатор ПОДЗАКОННЫХ актов. Строит карту блоков и пунктов на ГОТОВЫХ якорях
adilet (`id="zN"` уже стоит на каждом пункте/подпункте — изобретать не надо).

Иерархия подзаконного акта (проверено на выборке, см. reports/subordinate_recon.md):
    сам акт (приказ/постановление): преамбула + пункты 1..4 «Утвердить прилагаемые…»
    -> вложенный акт (Правила/Инструкция/Положение/…): Глава N -> пункт N. -> подпункт N)
    -> приложения (формы/бланки)

КЛЮЧЕВОЕ (источник мислинков): нумерация пунктов НАЧИНАЕТСЯ ЗАНОВО в каждом блоке.
Поэтому ведём ОТДЕЛЬНУЮ карту пунктов на КАЖДЫЙ блок и резолвим ссылку только внутри
её блока. Если номер в блоке встречается дважды (нумерация рестартует внутри блока —
7% случаев на выборке) — номер помечается AMBIGUOUS и НЕ линкуется (WRONG=0).

Разметка блоков — СТРУКТУРНАЯ, не угадывание по словам:
    <h3> «Глава N» / «Раздел» / «Параграф» -> подраздел ВНУТРИ текущего блока
    <h3> любой другой                      -> НАЧАЛО НОВОГО блока (заголовок вложенного акта)
Проверка на пилоте-100: в 97% блоков нумерация действительно стартует с 1 и растёт.
"""
import io, sys, re, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from pathlib import Path
from bs4 import BeautifulSoup

SUBDIV = re.compile(r"^(Глава|Раздел|Параграф|§)\b", re.I)
PUNKT = re.compile(r"^(\d{1,3})\.\s")
SUBPUNKT = re.compile(r"^(\d{1,3})\)\s")
APPENDIX = re.compile(r"^Приложени\w*\b", re.I)
# слово-вид вложенного акта -> по нему резолвится «настоящих Правил»
KINDWORD = re.compile(r"^(Правил\w*|Инструкц\w+|Положени\w+|Регламент\w*|Методик\w+|"
                      r"Перечень|Перечн\w+|Норматив\w*|Стандарт\w*|Порядок|Порядк\w+|"
                      r"Требовани\w+|Форм\w+|Устав\w*|Программ\w+|Концепци\w+|План\w*)", re.I)


def stem(word):
    """Грубая основа для сопоставления «Правила» <-> «настоящих Правил»."""
    w = (word or "").lower()
    for suf in ("ами", "ах", "ов", "ям", "ями", "ия", "ии", "ие", "ей", "ой", "ый",
                "ам", "ах", "а", "ы", "и", "е", "у", "ю", "я", "ь"):
        if len(w) > 5 and w.endswith(suf):
            return w[: -len(suf)]
    return w


def parse(html, doc_id):
    soup = BeautifulSoup(html, "html.parser")
    for t in soup(["script", "style"]):
        t.decompose()

    blocks = []
    cur = {"idx": 0, "kind": "act", "title": "(тело акта)", "title_anchor": None,
           "kindword": None, "punkt": {}, "dup": set(), "n_punkt": 0, "n_subpunkt": 0,
           "chapters": []}

    def flush():
        # Пишем ВСЕ блоки, даже пустые (бланки «Заявление», перечни без пунктов):
        # иначе резолвер теряет контекст «в каком блоке стоит ссылка» и вынужден
        # отказываться от линковки там, где блок на самом деле однозначен.
        blocks.append(cur)

    def in_table(node):
        p = node.parent
        while p is not None:
            if getattr(p, "name", None) in ("td", "th", "table"):
                return True
            p = p.parent
        return False

    pending_appendix = False       # видели маркер «Приложение …» в таблице-шапке
    for e in soup.find_all(["h3", "p", "td"]):
        txt = re.sub(r"\s+", " ", e.get_text(" ", strip=True))
        anc = e.get("id") if re.match(r"^z\d+$", e.get("id", "") or "") else None
        if e.name == "td":
            # шапка вложенного акта/приложения идёт ячейкой таблицы, не заголовком.
            # «Приложение 1», «Приложение N к Правилам» -> дальше ПРИЛОЖЕНИЕ (формы);
            # «Приложение к приказу» без номера -> это утверждаемый акт, не приложение.
            if re.match(r"^Приложени\w*\s+\d", txt) or re.search(r"к\s+Правилам|к\s+Инструкции", txt, re.I):
                pending_appendix = True
            continue
        if e.name == "h3":
            if SUBDIV.match(txt):
                cur["chapters"].append({"title": txt[:120], "anchor": anc})
                continue
            flush()
            kw = KINDWORD.match(txt)
            is_app = pending_appendix or APPENDIX.match(txt) or re.match(r"^Форма\b", txt, re.I)
            cur = {"idx": len(blocks), "kind": "appendix" if is_app else "nested",
                   "title": txt[:200], "title_anchor": anc,
                   "kindword": stem(kw.group(1)) if kw else None,
                   "punkt": {}, "dup": set(), "n_punkt": 0, "n_subpunkt": 0, "chapters": []}
            pending_appendix = False
            continue
        # <p> — НОРМАТИВНЫЙ пункт только вне таблиц: нумерованные строки таблиц
        # («2. Очаг токсокароза») — это содержимое формы, а не пункт акта.
        if in_table(e):
            continue
        m = PUNKT.match(txt)
        if m:
            n = int(m.group(1)); cur["n_punkt"] += 1
            if not anc:
                cur["dup"].add(n)          # без якоря сослаться некуда -> не линкуем
            elif n in cur["punkt"]:
                cur["dup"].add(n)          # нумерация рестартует внутри блока -> неоднозначно
            else:
                cur["punkt"][n] = anc
        elif SUBPUNKT.match(txt):
            cur["n_subpunkt"] += 1
    flush()

    for b in blocks:
        b["ambiguous"] = sorted(b.pop("dup"))
        b["punkt"] = {str(k): v for k, v in sorted(b["punkt"].items())}
    return {"doc_id": doc_id, "blocks": blocks}, None


def main():
    src = Path(sys.argv[1]); out = Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
    files = sorted(src.glob("*.html"))
    ok = err = 0
    tot_blocks = tot_punkt = tot_amb = tot_app = 0
    for f in files:
        res, e = parse(f.read_text(encoding="utf-8", errors="replace"), f.stem)
        if e:
            err += 1; print(f"   ОШИБКА {f.stem}: {e}"); continue
        ok += 1
        tot_blocks += len(res["blocks"])
        tot_punkt += sum(len(b["punkt"]) for b in res["blocks"])
        tot_amb += sum(len(b["ambiguous"]) for b in res["blocks"])
        tot_app += sum(1 for b in res["blocks"] if b["kind"] == "appendix")
        (out / f"{f.stem}.json").write_text(json.dumps(res, ensure_ascii=False, indent=1),
                                            encoding="utf-8")
    print(f"структурировано: {ok}/{len(files)}  ошибок={err}")
    print(f"   блоков всего        : {tot_blocks}  (в среднем {tot_blocks/max(1,ok):.1f} на акт)")
    print(f"   пунктов с якорем    : {tot_punkt}")
    print(f"   приложений (kind=appendix): {tot_app}")
    print(f"   НЕОДНОЗНАЧНЫХ номеров (не линкуем): {tot_amb}")


if __name__ == "__main__":
    main()
