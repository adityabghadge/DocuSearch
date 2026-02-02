from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class Chunk:
    chunk_index: int
    text: str
    char_start: int
    char_end: int
    token_count_est: int


def _token_estimate(text: str) -> int:
    # Cheap, deterministic estimate: whitespace tokens.
    return max(1, len(text.split()))


def chunk_text(text: str, chunk_size_chars: int, overlap_chars: int) -> List[Chunk]:
    """
    Deterministic chunking based on character offsets.

    Given the same input text and config, this produces identical chunks
    (indices, boundaries, content) every time.
    """
    if chunk_size_chars <= 0:
        raise ValueError("chunk_size_chars must be > 0")
    if overlap_chars < 0:
        raise ValueError("overlap_chars must be >= 0")
    if overlap_chars >= chunk_size_chars:
        raise ValueError("overlap_chars must be < chunk_size_chars")

    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    n = len(normalized)

    chunks: List[Chunk] = []
    start = 0
    idx = 0

    while start < n:
        end = min(n, start + chunk_size_chars)
        piece = normalized[start:end].strip()

        if piece:
            chunks.append(
                Chunk(
                    chunk_index=idx,
                    text=piece,
                    char_start=start,
                    char_end=end,
                    token_count_est=_token_estimate(piece),
                )
            )
            idx += 1

        if end == n:
            break

        start = max(0, end - overlap_chars)

    return chunks