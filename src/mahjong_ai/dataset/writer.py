"""JSONL writer for extracted Bayesian samples."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from .schema import BayesianSample


def save_samples(samples: Iterable[BayesianSample], path: str | Path) -> int:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with target.open("w", encoding="utf-8") as handle:
        for sample in samples:
            handle.write(json.dumps(sample.to_dict(), ensure_ascii=False, separators=(",", ":")) + "\n")
            count += 1
    return count


def load_samples(path: str | Path) -> list[dict[str, object]]:
    with Path(path).open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]
