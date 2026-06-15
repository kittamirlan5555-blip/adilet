# -*- coding: utf-8 -*-
"""ВЕКТОР-СЛОЙ, ФАЗА C: суммаризация больших статей через DeepSeek.

python scripts/vector/c_summarize.py --sample 5     # тест: 5 разнородных статей
python scripts/vector/c_summarize.py --all           # полный прогон по оставшимся

deepseek-chat, OpenAI-совместимый REST. Ключ — ТОЛЬКО из env DEEPSEEK_API_KEY
(никогда не логируется и не пишется в файлы). summary кладётся в parent-чанк
(представление для эмбеддинга; полный текст — payload). Идемпотентно: уже
заполненные summary не перезапрашиваются. Инкрементальное сохранение.
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import paths

CHUNKS = paths.ROOT / "derived" / "vector_layer" / "chunks.jsonl"
URL = "https://api.deepseek.com/chat/completions"
PROMPT = ("Сделай краткую фактологическую выжимку статьи закона на русском, "
          "3-5 предложений, строго по тексту, ничего не добавляй и не "
          "интерпретируй; сохрани ключевые понятия и нормы для семантического "
          "поиска.")


def load():
    return [json.loads(l) for l in CHUNKS.read_text(encoding="utf-8").splitlines() if l.strip()]


def save(rows):
    with CHUNKS.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def summarize(text, key):
    payload = {"model": "deepseek-chat", "temperature": 0.2,
               "messages": [{"role": "system", "content": PROMPT},
                            {"role": "user", "content": "Текст статьи закона:\n\n" + text}]}
    for attempt in range(3):
        r = requests.post(URL, json=payload, timeout=180, headers={
            "Authorization": f"Bearer {key}", "Content-Type": "application/json"})
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"].strip()
        # не ретраим аутентификацию/баланс — это не временная ошибка
        if r.status_code in (401, 402, 403):
            msg = ""
            try:
                msg = r.json().get("error", {}).get("message", "")
            except Exception:
                pass
            raise SystemExit(f"STOP DeepSeek HTTP {r.status_code}: {msg or r.text[:120]}"
                             + (" — пополни баланс аккаунта DeepSeek "
                                "(platform.deepseek.com), ключ рабочий."
                                if r.status_code == 402 else ""))
        if attempt == 2:
            r.raise_for_status()
        time.sleep(2 * (attempt + 1))


def pick_sample(parents, n):
    """n разнородных статей: разные документы, разброс по длине."""
    todo = [p for p in parents if not p.get("summary")]
    todo.sort(key=lambda p: p["char_len"])
    if len(todo) <= n:
        return todo
    idx = [int(i * (len(todo) - 1) / (n - 1)) for i in range(n)]
    seen, out = set(), []
    for i in idx:
        j = i
        while j < len(todo) and todo[j]["code"] in seen:
            j += 1
        j = j if j < len(todo) else i
        seen.add(todo[j]["code"])
        out.append(todo[j])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int)
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()
    key = os.environ.get("DEEPSEEK_API_KEY")
    if not key:
        sys.exit("STOP: переменная окружения DEEPSEEK_API_KEY не задана. "
                 "Задай ключ и повтори (он не пишется в файлы/логи).")
    rows = load()
    parents = [r for r in rows if r["kind"] == "parent"]
    targets = (pick_sample(parents, args.sample) if args.sample
               else [p for p in parents if not p.get("summary")])
    print(f"к суммаризации: {len(targets)} статей "
          f"(всего без summary: {sum(1 for p in parents if not p.get('summary'))})")
    done = 0
    for p in targets:
        try:
            s = summarize(p["text"], key)
        except Exception as e:
            print(f"  ОШИБКА {p['code']} ст.{p['article_no']}: {type(e).__name__}")
            continue
        p["summary"] = s
        done += 1
        save(rows)   # инкрементально — прогресс не теряется
        print(f"  [{done}/{len(targets)}] {p['code']} ст.{p['article_no']} "
              f"({p['char_len']}→{len(s)} симв)")
        time.sleep(0.4)
    print(f"готово: {done} summary записано в {CHUNKS.name}")


if __name__ == "__main__":
    main()
