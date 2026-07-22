# embed_kit — эмбеддинг вектор-слоя (RTX 5090 по RDP ИЛИ CPU)

Кладёт векторы для faiss-индекса корпуса законов РК. Модель `intfloat/multilingual-e5-large`
(в `model/`, офлайн). Вход `chunks.jsonl`, выход `out/vectors.npy` + `out/ids.jsonl`.
**Работает и на GPU, и на CPU** — `--device auto|cpu|cuda` (auto: GPU если есть, иначе CPU).
GPU на сервере НЕ обязателен; если карты нет — считает на CPU (дольше, но идёт).

## Запуск в 5 строк

```
nvidia-smi   # или: python -c "import torch;print(torch.cuda.is_available())"   # 1. есть ли GPU?
pip install torch --index-url https://download.pytorch.org/whl/cu128 && pip install -r requirements.txt   # 2a. GPU: torch cu128
#   БЕЗ GPU:  pip install torch && pip install -r requirements.txt              # 2b. CPU: обычный torch
python embed.py --limit 200                                       # 3. СМОУК: печатает УСТРОЙСТВО + пасс/с + ETA
python embed.py                                                   # 4. ПОЛНЫЙ (resume при обрыве); --device cpu если карты нет
#  5. забрать назад: out/vectors.npy + out/ids.jsonl  ->  ноут: derived/vector_layer/
```

При старте скрипт печатает выбранное УСТРОЙСТВО и ожидаемую длительность: CPU ≈ 0.75 пасс/с
(полный корпус ~37k → ~14 ч), 5090 — оценка ~40 пасс/с (полный ~15 мин, смоук уточнит).
Полный на CPU долгий — тогда лучше сначала `--limit 200`, либо разбить (resume-able).

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
