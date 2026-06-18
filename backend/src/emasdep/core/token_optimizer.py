"""Token Optimization: context compression, relevant slicing, minimal history."""

from __future__ import annotations

from .types import CompressedContext


class TokenOptimizer:
    def __init__(self, max_chars: int = 8000, max_history: int = 3) -> None:
        """  init  .

Args:
    max_chars: Descrição do parâmetro max_chars.
    max_history: Descrição do parâmetro max_history.

Retorna:
    Descrição do valor retornado."""
        self.max_chars = max_chars
        self.max_history = max_history

    def compress(self, text: str, preserve_sections: list[str] | None = None) -> CompressedContext:
        """compress.

Args:
    text: Descrição do parâmetro text.
    preserve_sections: Descrição do parâmetro preserve_sections.

Retorna:
    Descrição do valor retornado."""
        if len(text) <= self.max_chars:
            return CompressedContext(
                original_length=len(text),
                compressed_length=len(text),
                content=text,
            )

        removed: list[str] = []
        result = text
        preserve = preserve_sections or []

        for section in preserve:
            result = result.replace(section, "", 1)

        if len(result) > self.max_chars:
            lines = result.splitlines()
            if len(lines) > 200:
                kept = lines[:100] + ["... [truncated] ..."] + lines[-100:]
                removed.append(f"{len(lines) - 200} lines removed from middle")
                result = "\n".join(kept)

        if len(result) > self.max_chars:
            result = result[: self.max_chars] + "\n... [truncated] ..."
            removed.append(f"Truncated at {self.max_chars} chars")

        return CompressedContext(
            original_length=len(text),
            compressed_length=len(result),
            content=result,
            removed_sections=removed,
        )

    def slice_relevant(self, context: list[str], query: str, max_items: int = 5) -> list[str]:
        """slice relevant.

Args:
    context: Descrição do parâmetro context.
    query: Descrição do parâmetro query.
    max_items: Descrição do parâmetro max_items.

Retorna:
    Descrição do valor retornado."""
        if not context:
            return []

        query_lower = query.lower()
        scored = []
        for item in context:
            score = 0
            item_lower = item.lower()
            for word in query_lower.split():
                if word in item_lower:
                    score += 1
            scored.append((score, item))

        scored.sort(key=lambda x: -x[0])
        return [item for _, item in scored[:max_items]]

    @staticmethod
    def trim_history(history: list[dict], max_entries: int = 3) -> list[dict]:
        return history[-max_entries:]
