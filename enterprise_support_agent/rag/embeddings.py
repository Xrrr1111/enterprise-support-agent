"""Dependency-free hashing embeddings suitable for a small local knowledge base."""

from __future__ import annotations

import hashlib
import math
import re
from collections import Counter


TOKEN_PATTERN = re.compile(r"[a-z0-9]+|[\u4e00-\u9fff]", re.IGNORECASE)


def tokenize(text: str) -> list[str]:
    lowered = text.lower()
    base = TOKEN_PATTERN.findall(lowered)
    normalized: list[str] = []
    for token in base:
        normalized.append(token)
        if token.isascii() and len(token) > 4 and token.endswith("s"):
            normalized.append(token[:-1])
        if token.isascii() and len(token) > 5 and token.endswith("ing"):
            normalized.append(token[:-3])
        if token.isascii() and len(token) > 4 and token.endswith("ed"):
            normalized.append(token[:-2])
    chinese = "".join(character for character in lowered if "\u4e00" <= character <= "\u9fff")
    bigrams = [chinese[index : index + 2] for index in range(max(0, len(chinese) - 1))]
    return normalized + bigrams


class HashingEmbedder:
    """Replaceable local embedding provider using stable feature hashing."""

    provider = "local-hashing"

    def __init__(self, dimensions: int = 512) -> None:
        self.dimensions = dimensions

    def embed(self, text: str) -> list[float]:
        counts = Counter(tokenize(text))
        vector = [0.0] * self.dimensions
        for token, count in counts.items():
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
            value = int.from_bytes(digest, "little")
            index = value % self.dimensions
            sign = 1.0 if (value >> 8) & 1 else -1.0
            vector[index] += sign * (1.0 + math.log(count))
        norm = math.sqrt(sum(item * item for item in vector))
        return [item / norm for item in vector] if norm else vector


def cosine_similarity(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right, strict=True))
