"""Learn calibrated rank-hit rates without using future contests."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from scripts.common import features, read_matches

FEATURE_NAMES = ("top1", "top2", "top3", "gap12", "gap23", "balance")


def train(history_path: str, model_path: str, before_contest: int | None = None) -> dict:
    rows = read_matches(history_path, require_results=True)
    if before_contest is not None:
        rows = [m for m in rows if m.contest < before_contest]
    if not rows:
        raise ValueError("não há histórico anterior suficiente")
    bins = {str(rank): [[1, 3] for _ in range(10)] for rank in (1, 2, 3)}  # beta(1,2)
    stats = {str(rank): defaultdict(list) for rank in (1, 2, 3)}
    for match in rows:
        f = features(match)
        for rank, probability in enumerate(match.ranked_probabilities, 1):
            bucket = min(9, int(probability * 10))
            bins[str(rank)][bucket][1] += 1
            bins[str(rank)][bucket][0] += match.actual_rank == rank
        for name, value in f.items():
            stats[str(match.actual_rank)][name].append(value)
    profiles = {}
    for rank in (1, 2, 3):
        profiles[str(rank)] = {}
        for name in FEATURE_NAMES:
            values = stats[str(rank)][name]
            mean = sum(values) / len(values)
            variance = sum((x-mean) ** 2 for x in values) / max(1, len(values)-1)
            profiles[str(rank)][name] = {"mean": mean, "std": max(variance ** .5, .01)}
    model = {"version": 1, "trained_before": before_contest,
             "training_matches": len(rows), "calibration_bins": bins, "profiles": profiles}
    Path(model_path).parent.mkdir(parents=True, exist_ok=True)
    Path(model_path).write_text(json.dumps(model, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return model


if __name__ == "__main__":
    model = train("data/concursos_anteriores.csv", "models/model.json")
    print(f"Modelo treinado com {model['training_matches']} partidas.")
