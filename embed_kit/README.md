# embed_kit — эмбеддинг вектор-слоя на RTX 5090 (по RDP)

Кладёт векторы для faiss-индекса корпуса законов РК. Модель `intfloat/multilingual-e5-large`
(в `model/`, офлайн). Вход `chunks.jsonl`, выход `out/vectors.npy` + `out/ids.jsonl`.

## Запуск в 5 строк (RDP)

```
nvidia-smi                                                        # 1. карта видна? (RTX 5090)
pip install torch --index-url https://download.pytorch.org/whl/cu128 && pip install -r requirements.txt   # 2. окружение (cu128!)
python embed.py --limit 200                                       # 3. СМОУК: замер пасс/с, проверка sm_120
python embed.py                                                   # 4. ПОЛНЫЙ прогон (resume при обрыве)
#  5. забрать назад: out/vectors.npy + out/ids.jsonl  ->  ноут: derived/vector_layer/
```

## Что важно

- **CUDA 12.8+ обязательна.** 5090 — Blackwell (sm_120); torch под cu121/cu124 карту НЕ
  увидит. `embed.py` проверяет capability и падает внятно, если torch старый.
- **Смоук (`--limit 200`)** — сначала: подтверждает, что карта считает, и даёт пасс/с
  (ожидаем десятки-сотни/с против 0.75 на ноутном CPU).
- **Resume**: полный прогон при обрыве продолжается с последнего сохранённого
  (`out/progress.json` + memmap), НЕ с нуля. Чтобы начать заново — удали `out/`.
- **Офлайн-сервер** (нет интернета): см. requirements.txt (раздел «ОФЛАЙН») — colёса
  скачать заранее; модель уже в `model/`.
- Секретов/ключей в ките НЕТ (только тексты НПА). fp16 на GPU, батч 64 (правь `--batch`).

## Обратно на ноут (BLOCK E)

`out/vectors.npy` + `out/ids.jsonl` → `derived/vector_layer/` → `scripts/vector/g_build_index.py`
(вариант «из готовых векторов») соберёт `index.faiss` + `index_meta.jsonl` + `index_config.json`.
