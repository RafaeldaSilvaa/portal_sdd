"""RAG Memory System: episodic, semantic, and architectural memory with retrieval."""

from __future__ import annotations

import math
import re
from collections import defaultdict


from ..core.types import MemoryEntry, MemoryResult


class RAGMemory:
    def __init__(self) -> None:
        self._entries: list[MemoryEntry] = []

    def store(self, entry_type: str, content: str, metadata: dict | None = None) -> MemoryEntry:
        """store.

Args:
    entry_type: Descrição do parâmetro entry_type.
    content: Descrição do parâmetro content.
    metadata: Descrição do parâmetro metadata.

Retorna:
    Descrição do valor retornado."""
        entry = MemoryEntry.create(entry_type, content, metadata)
        entry.embedding = self._compute_embedding(content)
        self._entries.append(entry)
        return entry

    def store_episodic(self, execution_id: str, result: str, failed: bool = False) -> MemoryEntry:
        """store episodic.

Args:
    execution_id: Descrição do parâmetro execution_id.
    result: Descrição do parâmetro result.
    failed: Descrição do parâmetro failed.

Retorna:
    Descrição do valor retornado."""
        return self.store(
            "episodic",
            result,
            {"execution_id": execution_id, "failed": str(failed)},
        )

    def store_semantic(self, domain: str, knowledge: str) -> MemoryEntry:
        return self.store("semantic", knowledge, {"domain": domain})

    def store_architectural(self, decision: str, rationale: str) -> MemoryEntry:
        return self.store("architectural", decision, {"decision": rationale})

    def retrieve(self, query: str, top_k: int = 3) -> MemoryResult:
        """retrieve.

Args:
    query: Descrição do parâmetro query.
    top_k: Descrição do parâmetro top_k.

Retorna:
    Descrição do valor retornado."""
        if not self._entries:
            return MemoryResult()

        query_embedding = self._compute_embedding(query)
        scored = []
        for entry in self._entries:
            if entry.embedding:
                score = self._cosine_similarity(query_embedding, entry.embedding)
                scored.append((score, entry))
        scored.sort(key=lambda x: -x[0])

        result = MemoryResult()
        for score, entry in scored[:top_k]:
            result.entries.append(entry)
            result.scores.append(score)
        return result

    def retrieve_by_type(self, entry_type: str, top_k: int = 3) -> MemoryResult:
        """retrieve by type.

Args:
    entry_type: Descrição do parâmetro entry_type.
    top_k: Descrição do parâmetro top_k.

Retorna:
    Descrição do valor retornado."""
        filtered = [e for e in self._entries if e.entry_type == entry_type]
        result = MemoryResult()
        for entry in filtered[:top_k]:
            result.entries.append(entry)
            result.scores.append(1.0)
        return result

    def clear(self) -> None:
        self._entries.clear()

    def _compute_embedding(self, text: str) -> list[float]:
        """ compute embedding.

Args:
    text: Descrição do parâmetro text.

Retorna:
    Descrição do valor retornado."""
        words = re.findall(r"\w+", text.lower())
        word_freq: dict[str, float] = defaultdict(float)
        for w in words:
            word_freq[w] += 1.0
        total = len(words) or 1
        return [word_freq[w] / total for w in sorted(word_freq.keys())[:50]]

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        """ cosine similarity.

Args:
    a: Descrição do parâmetro a.
    b: Descrição do parâmetro b.

Retorna:
    Descrição do valor retornado."""
        if not a or not b:
            return 0.0
        max_len = max(len(a), len(b))
        va = a + [0.0] * (max_len - len(a))
        vb = b + [0.0] * (max_len - len(b))
        dot = sum(x * y for x, y in zip(va, vb))
        na = math.sqrt(sum(x * x for x in va))
        nb = math.sqrt(sum(y * y for y in vb))
        if na * nb == 0:
            return 0.0
        return dot / (na * nb)


_memory_instance: RAGMemory | None = None


def get_memory() -> RAGMemory:
    """get memory.

Retorna:
    Descrição do valor retornado."""
    global _memory_instance
    if _memory_instance is None:
        _memory_instance = RAGMemory()
    return _memory_instance
