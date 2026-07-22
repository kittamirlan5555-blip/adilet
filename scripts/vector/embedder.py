# -*- coding: utf-8 -*-
"""ЕДИНЫЙ эмбеддер вектор-слоя — модель и e5-префиксы в ОДНОМ месте, чтобы
ИНДЕКСАЦИЯ (g_build_index) и ПОИСК (i_retrieval_eval / e_retrieval_smoke) были
СОГЛАСОВАНЫ: одна модель, правильные префиксы с обеих сторон.

Модель: intfloat/multilingual-e5-large (1024-dim, сильный русский).
e5 ТРЕБУЕТ асимметричные префиксы (без них качество заметно падает):
  • индексируемый пассаж -> "passage: " + текст
  • поисковый запрос     -> "query: "   + текст
Эмбеддинги L2-нормируются → cosine == dot (faiss IndexFlatIP).
Лимит модели — 512 токенов: всё сверх e5 МОЛЧА обрезает (см. h_token_audit).

Бэкенд: sentence-transformers (torch). Модель грузится лениво и кэшируется.
"""
MODEL = "intfloat/multilingual-e5-large"
DIM = 1024
PASSAGE_PREFIX = "passage: "
QUERY_PREFIX = "query: "
MAX_TOKENS = 512

_model = None


def _resolve_model_path(name):
    """Тот же e5-large лежит офлайн в embed_kit/model (им же собран индекс).
    Предпочитаем ЛОКАЛЬНУЮ копию: идентичные веса + без интернета/HF-докачки."""
    from pathlib import Path
    local = Path(__file__).resolve().parents[2] / "embed_kit" / "model"
    if local.exists() and (local / "config.json").exists():
        return str(local)
    return name


def get_model(name=MODEL):
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(_resolve_model_path(name))
        # e5-large: max_seq_length=512 (модель сама обрежет сверх — см. h_token_audit)
        _model.max_seq_length = MAX_TOKENS
    return _model


def _encode(texts, prefix, batch_size=32, show=True):
    import numpy as np
    m = get_model()
    vecs = m.encode([prefix + t for t in texts], batch_size=batch_size,
                    normalize_embeddings=True, convert_to_numpy=True,
                    show_progress_bar=show)
    return np.asarray(vecs, dtype="float32")


def encode_passages(texts, **kw):
    """Пассажи для индекса: 'passage: ' + текст, L2-норм. -> np.float32[N,1024]."""
    return _encode(texts, PASSAGE_PREFIX, **kw)


def encode_queries(texts, **kw):
    """Запросы поиска: 'query: ' + текст, L2-норм. -> np.float32[N,1024]."""
    return _encode(texts, QUERY_PREFIX, **kw)


def get_tokenizer(name=MODEL):
    """Токенайзер e5 (XLM-RoBERTa/sentencepiece) — для аудита лимита 512 токенов."""
    from transformers import AutoTokenizer
    return AutoTokenizer.from_pretrained(name)
