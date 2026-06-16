# Вектор-слой ADILETkz — пакет

Данные и индекс (каноничны): `derived/vector_layer/`
  • chunks.jsonl       — 13 475 чанков (6961 parent на статью + 6514 сабчанков ≤окна; summary на 401 крупных)
  • index.faiss        — faiss-индекс (MiniLM, 384-dim, 12 013 векторов)
  • index_meta.jsonl   — строка индекса → parent uid/код/статья
  • index_config.json  — модель, dim, префиксы

Скрипты: `scripts/vector/` (a..i): аудит, чанкинг, summary (DeepSeek), валидация,
индекс, ретрив-эвал. Отчёты — здесь рядом.

Якоря статей zX не менялись; суб-id additive (zX_1..). Summary строго по тексту.
