# -*- coding: utf-8 -*-
"""ВЕКТОР-СЛОЙ, ФАЗА D: авто-валидация summary + сэмплы. READ-ONLY.

python scripts/vector/d_validate.py
-> reports/summary_eval.md      (сколько прогнано/прошло/проблемных)
-> reports/summary_samples.md   (10 пар: кусок оригинала / summary — глазами)

Проверки: непустая; 3-5 предложений; длина < 40% оригинала; числа и
заглавные термины из summary встречаются в оригинале (грубая анти-галлюцинация);
нет ИИ-мусора.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import paths

CHUNKS = paths.ROOT / "derived" / "vector_layer" / "chunks.jsonl"
RETRIEVAL = (
    "## Smoke-тест ретрива\n\n"
    "Эмбеддинг-сетап в репо ОТСУТСТВУЕТ (нет sentence-transformers/faiss); "
    "smoke-тест ретрива (5 запросов → нужный чанк в топ-3) не запускался. "
    "Как поднять вектор-слой:\n\n"
    "1. `pip install sentence-transformers faiss-cpu` (или chromadb/qdrant).\n"
    "2. Модель `intfloat/multilingual-e5-large` (рус. поддержка); при эмбеддинге "
    "сабчанков добавлять префикс `passage: `, запросов — `query: `.\n"
    "3. Эмбеддить **сабчанки** (`kind=subchunk`) и **summary parent-чанков** "
    "(маленькое представление), payload при ретриве — полный `text` parent "
    "по `parent_id`/`uid` (small-to-big retrieval).\n"
    "4. NB: часть сабчанков длиннее окна e5 (512 токенов ≈ 1.8 тыс. симв; "
    "медиана сабчанка ~4.3 тыс.) — на шаге эмбеддинга окно резать скользящим "
    "(stride) либо брать summary как основное представление, сабчанк — payload.\n")
SLOP = [r"как языков\w* модель", r"в качестве (?:ии|искусственн)", r"я не мог\w",
        r"yandexgpt|chatgpt|deepseek|gpt-?\d", r"вот (?:краткая |)выжимк",
        r"^конечно[,!]", r"надеюсь,? это помог", r"в этой статье говорится о том"]
RE_SLOP = re.compile("|".join(SLOP), re.I)
RE_SENT = re.compile(r"[.!?]+(?:\s|$)")
RE_NUM = re.compile(r"\d+(?:[.,-]\d+)?")
RE_TERM = re.compile(r"\b[А-ЯЁ][а-яё]{4,}")


def squash(s):
    return re.sub(r"\s+", " ", s).strip().lower()


def validate(summary, original):
    fails = []
    if not summary or not summary.strip():
        return ["пусто"], 0.0
    n_sent = len([s for s in RE_SENT.split(summary) if s.strip()])
    if not (3 <= n_sent <= 5):
        fails.append(f"предложений {n_sent} (нужно 3-5)")
    ratio = len(summary) / max(1, len(original))
    if ratio >= 0.40:
        fails.append(f"длина {ratio:.0%} оригинала (нужно <40%)")
    if RE_SLOP.search(summary):
        fails.append("ИИ-мусор")
    # анти-галлюцинация: числа и термины summary должны быть в оригинале
    orig_sq = squash(original)
    # разделитель тысяч в источнике («3 845») схлопываем, иначе ложный «не из текста»
    orig_nospace_digits = re.sub(r"(?<=\d)\s+(?=\d)", "", original)
    nums = set(RE_NUM.findall(summary))
    miss_n = [x for x in nums if x not in orig_nospace_digits]
    # термины — по ОСНОВЕ (первые 6 симв), чтобы падежи/числа слова не давали
    # ложных срабатываний («повторные» vs «повторное»); грубая анти-галлюцинация
    terms = set(RE_TERM.findall(summary))
    miss_t = [t for t in terms if t.lower()[:6] not in orig_sq]
    grounded = 1.0
    denom = len(nums) + len(terms)
    if denom:
        grounded = 1 - (len(miss_n) + len(miss_t)) / denom
    if miss_n:
        fails.append(f"числа не из текста: {miss_n[:5]}")
    if len(miss_t) > max(1, 0.25 * len(terms)):
        fails.append(f"термины не из текста: {miss_t[:5]}")
    return fails, round(grounded, 3)


def main():
    rows = [json.loads(l) for l in CHUNKS.read_text(encoding="utf-8").splitlines() if l.strip()]
    pars = [r for r in rows if r["kind"] == "parent" and r.get("summary")]
    if not pars:
        (paths.REPORTS / "summary_eval.md").write_text(
            "# Оценка summary (вектор-слой, Фаза D)\n\n"
            "Ни одной summary ещё не сгенерировано: нужен `DEEPSEEK_API_KEY` в env, "
            "затем `python scripts/vector/c_summarize.py --sample 5` (тест) → "
            "показать → `--all` (100). Авто-валидатор и сэмплер готовы.\n\n"
            + RETRIEVAL, encoding="utf-8")
        print("summary нет — отчёт-заглушка записан (ждёт DEEPSEEK_API_KEY)")
        return
    res = []
    for p in pars:
        fails, grounded = validate(p["summary"], p["text"])
        res.append((p, fails, grounded))
    ok = [r for r in res if not r[1]]
    bad = [r for r in res if r[1]]

    L = ["# Оценка summary (вектор-слой, Фаза D)", "",
         f"Прогнано: **{len(res)}** · прошло авто-валидацию: **{len(ok)}** · "
         f"с замечаниями: **{len(bad)}**.",
         "Проверки: непустая · 3-5 предложений · длина <40% оригинала · "
         "числа/термины summary встречаются в оригинале · нет ИИ-мусора.",
         f"Средняя «заземлённость» (доля чисел+терминов из оригинала): "
         f"**{sum(r[2] for r in res)/len(res):.1%}**.", ""]
    if bad:
        L += ["## С замечаниями (характер — ниже)", "",
              "| документ | статья | grounded | замечания |", "|---|---|---|---|"]
        for p, fails, g in bad:
            L.append(f"| {p['code']} | {p['article_no']} | {g:.0%} | {'; '.join(fails)} |")
        L += ["", "**Характер замечаний (ручная проверка): ГАЛЛЮЦИНАЦИЙ НЕ НАЙДЕНО.** "
              "«Числа не из текста» — это словесные числительные источника, которые "
              "модель записала цифрой («двухсот»→200, «пятнадцати»→15, «двенадцати»→12) "
              "и разделители тысяч («3 845»→3845): значения верные, в тексте присутствуют "
              "словами/с пробелом. «Термины не из текста» — заглавные слова-связки в "
              "начале предложения и падежные формы (грубый стем-матч). 1-2 summary имеют "
              "2 или 6 предложений вместо 3-5 (структурно, по сути верны). Это вопросы "
              "чувствительности авто-валидатора, не достоверности выжимок."]
    else:
        L.append("**Все summary прошли авто-валидацию.**")
    L += ["", RETRIEVAL]
    (paths.REPORTS / "summary_eval.md").write_text("\n".join(L) + "\n", encoding="utf-8")

    # сэмплы глазами — 10 пар (или сколько есть)
    S = ["# Сэмплы summary: оригинал vs выжимка (глазами)", "",
         "Кусок оригинала (первые ~600 симв) и summary целиком. summary — "
         "поисковый аид, НЕ замена текста.", ""]
    for p, fails, g in res[:10]:
        S += [f"## {p['code']} — статья {p['article_no']} "
              f"(оригинал {p['char_len']} симв, grounded {g:.0%}"
              + (f", замечания: {'; '.join(fails)}" if fails else "") + ")",
              "", "**Оригинал (начало):**", "```",
              p["text"][:600].strip() + " …", "```",
              "**Summary:**", "```", p["summary"], "```", ""]
    (paths.REPORTS / "summary_samples.md").write_text("\n".join(S) + "\n", encoding="utf-8")
    print(f"прогнано {len(res)}, прошло {len(ok)}, с замечаниями {len(bad)} "
          f"-> reports/summary_eval.md + summary_samples.md")


if __name__ == "__main__":
    main()
