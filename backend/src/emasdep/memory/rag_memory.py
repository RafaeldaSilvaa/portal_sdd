"""RAG Memory System: episodic, semantic, and architectural memory with retrieval."""

from __future__ import annotations

import math
import re
from collections import defaultdict
from dataclasses import dataclass, field

from ..core.types import MemoryEntry, MemoryResult


class RAGMemory:
    def __init__(self):
        self._entries: list[MemoryEntry] = []

    def store(self, entry_type: str, content: str, metadata: dict | None = None) -> MemoryEntry:
        entry = MemoryEntry.create(entry_type, content, metadata)
        entry.embedding = self._compute_embedding(content)
        self._entries.append(entry)
        return entry

    def store_episodic(self, execution_id: str, result: str, failed: bool = False) -> MemoryEntry:
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
        filtered = [e for e in self._entries if e.entry_type == entry_type]
        result = MemoryResult()
        for entry in filtered[:top_k]:
            result.entries.append(entry)
            result.scores.append(1.0)
        return result

    def clear(self):
        self._entries.clear()

    def _compute_embedding(self, text: str) -> list[float]:
        words = re.findall(r"\w+", text.lower())
        word_freq: dict[str, float] = defaultdict(float)
        for w in words:
            word_freq[w] += 1.0
        total = len(words) or 1
        return [word_freq[w] / total for w in sorted(word_freq.keys())[:50]]

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
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
    global _memory_instance
    if _memory_instance is None:
        _memory_instance = RAGMemory()
    return _memory_instance
