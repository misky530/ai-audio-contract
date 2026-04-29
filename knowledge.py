# knowledge.py — 知识库加载 + 模糊匹配

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

KNOWLEDGE_FILE = Path(__file__).parent / "knowledge.json"

_cache: dict | None = None


def load() -> dict:
    global _cache
    if _cache is None:
        if KNOWLEDGE_FILE.exists():
            with open(KNOWLEDGE_FILE, encoding="utf-8") as f:
                _cache = json.load(f)
            logger.info(f"知识库已加载: {sum(len(v) for v in _cache.values())} 条")
        else:
            _cache = {}
    return _cache


def reload():
    global _cache
    _cache = None
    return load()


def suggest(field_key: str, text: str, top_n: int = 3, cutoff: int = 35) -> list[dict]:
    """
    对 text 在 field_key 对应的知识库中做模糊匹配。
    返回 [{"text": ..., "score": ...}, ...] 按相似度降序。
    """
    if not text:
        return []

    try:
        from rapidfuzz import process, fuzz
    except ImportError:
        logger.warning("rapidfuzz 未安装，跳过模糊匹配")
        return []

    candidates = load().get(field_key, [])
    if not candidates:
        return []

    results = process.extract(
        text, candidates,
        scorer=fuzz.WRatio,
        limit=top_n,
        score_cutoff=cutoff,
    )
    return [{"text": r[0], "score": round(r[1])} for r in results]
