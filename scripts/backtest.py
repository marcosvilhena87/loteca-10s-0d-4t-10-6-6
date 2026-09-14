"""Leakage-safe walk-forward evaluation with one row per historical ticket."""

from __future__ import annotations

import argparse
import csv
import tempfile
from collections import defaultdict
from pathlib import Path

from scripts.common import read_matches
from scripts.predict_results import select_ticket
from scripts.train_model import train


def run_backtest(history_path: str, output_path: str,
                 min_training_contests: int = 20) -> list[dict[str, object]]:
    """Generate and score exactly one valid ticket for every eligible contest."""
    matches = read_matches(history_path, require_results=True)
    contests = defaultdict(list)
    for match in matches:
        contests[match.contest].append(match)
    contest_ids = sorted(contests)
    rows = []
    with tempfile.TemporaryDirectory() as directory:
        model_path = str(Path(directory) / "model.json")
        for position, target in enumerate(contest_ids):
            target_matches = contests[target]
            if position < min_training_contests or len(target_matches) != 14:
                continue
            try:
                model = train(history_path, model_path, before_contest=target)
            except ValueError:  # no P14 profile exists yet in the early window
                continue
            assert model["trained_until"] < target
            result = select_ticket(target_matches, model)
            points = sum(m.actual in set(result["picks"][m.game]) for m in target_matches)
            row = {
                "Concurso": target, "Pontos": points, "P14": int(points == 14),
                "P13_plus": int(points >= 13), "P12_plus": int(points >= 12),
                "Score_P14": result["score_p14"],
                "trained_until": model["trained_until"],
                "training_matches": model["training_matches"],
                "training_contests": model["training_contests"],
                **result["ticket_features"],
            }
            rows.append(row)
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if rows:
        with path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=rows[0], delimiter=";",
                                    lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
    return rows


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--history", default="data/concursos_anteriores.csv")
    parser.add_argument("--output", default="output/backtest.csv")
    parser.add_argument("--min-training-contests", type=int, default=20)
    args = parser.parse_args()
    result = run_backtest(args.history, args.output, args.min_training_contests)
    print(f"Backtest concluído: {len(result)} bilhetes gravados em {args.output}")
