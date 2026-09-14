"""Validate and summarize the source CSV files."""

from __future__ import annotations

from collections import Counter

from scripts.common import features, read_matches


def preprocess(path: str, require_results: bool = True):
    matches = read_matches(path, require_results=require_results)
    return [{**features(m), "contest": m.contest, "game": m.game,
             "actual_rank": m.actual_rank} for m in matches]


def summary(path: str) -> dict[str, object]:
    rows = preprocess(path)
    contests = {r["contest"] for r in rows}
    return {"matches": len(rows), "contests": len(contests),
            "actual_ranks": dict(Counter(r["actual_rank"] for r in rows))}


if __name__ == "__main__":
    print(summary("data/concursos_anteriores.csv"))
