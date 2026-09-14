"""Learn match calibration and ticket-role profiles without future leakage."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

from scripts.common import features, read_matches

FEATURE_NAMES = ("top1", "top2", "top3", "gap12", "gap23", "balance")
DRY_REQUIREMENTS = {1: 6, 2: 2, 3: 2}
GLOBAL_FEATURE_NAMES = tuple(
    [f"triple_{name}_mean" for name in FEATURE_NAMES]
    + [f"dry_top{rank}_{name}_mean" for rank in (1, 2, 3) for name in FEATURE_NAMES]
)


def _weighted_profile(samples: list[tuple[dict[str, float], float]]) -> dict:
    """Return stable weighted moments for one role in historical P14 tickets."""
    total = sum(weight for _, weight in samples)
    if total <= 0:
        raise ValueError("histórico insuficiente para estimar perfil de bilhete P14")
    result = {}
    for name in FEATURE_NAMES:
        mean = sum(row[name] * weight for row, weight in samples) / total
        variance = sum(weight * (row[name] - mean) ** 2 for row, weight in samples) / total
        result[name] = {"mean": mean, "std": max(variance ** .5, .01)}
    return result


def _profile_rows(rows: list[dict[str, float]]) -> dict[str, dict[str, float]]:
    """Estimate stable moments across complete historical P14-compatible tickets."""
    if not rows:
        raise ValueError("histórico insuficiente para estimar perfil global P14")
    profile = {}
    for name in GLOBAL_FEATURE_NAMES:
        values = [row[name] for row in rows]
        mean = sum(values) / len(values)
        variance = sum((value - mean) ** 2 for value in values) / max(1, len(values) - 1)
        profile[name] = {"mean": mean, "std": max(variance ** .5, .01)}
    return profile


def train(history_path: str, model_path: str, before_contest: int | None = None) -> dict:
    rows = read_matches(history_path, require_results=True)
    if before_contest is not None:
        rows = [m for m in rows if m.contest < before_contest]
    if not rows:
        raise ValueError("não há histórico anterior suficiente")
    if before_contest is not None:
        assert max(m.contest for m in rows) < before_contest
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

    # A contest can support a P14 ticket precisely when its realised ranks contain
    # the required 6/2/2 dry outcomes; the remaining four games become triples.
    # Games tied on realised rank are exchangeable, so fractional weights avoid an
    # arbitrary choice and retain one observation per contest/ticket.
    contests = defaultdict(list)
    for match in rows:
        contests[match.contest].append(match)
    ticket_samples = defaultdict(list)
    global_ticket_rows = []
    p14_contests = 0
    for contest_matches in contests.values():
        counts = Counter(m.actual_rank for m in contest_matches)
        if len(contest_matches) != 14 or any(counts[r] < DRY_REQUIREMENTS[r] for r in (1, 2, 3)):
            continue
        p14_contests += 1
        rank_features = {
            rank: [features(match) for match in contest_matches if match.actual_rank == rank]
            for rank in (1, 2, 3)
        }
        role_means = {
            rank: {name: sum(row[name] for row in rank_features[rank]) / counts[rank]
                   for name in FEATURE_NAMES}
            for rank in (1, 2, 3)
        }
        global_row = {
            f"dry_top{rank}_{name}_mean": role_means[rank][name]
            for rank in (1, 2, 3) for name in FEATURE_NAMES
        }
        # Expected aggregate of the four triples over every valid allocation.
        for name in FEATURE_NAMES:
            total_feature = sum(features(match)[name] for match in contest_matches)
            dry_feature = sum(DRY_REQUIREMENTS[rank] * role_means[rank][name]
                              for rank in (1, 2, 3))
            global_row[f"triple_{name}_mean"] = (total_feature - dry_feature) / 4
        global_ticket_rows.append(global_row)
        for match in contest_matches:
            rank = match.actual_rank
            triple_weight = (counts[rank] - DRY_REQUIREMENTS[rank]) / counts[rank]
            ticket_samples["triple"].append((features(match), triple_weight))
            ticket_samples[f"dry_top{rank}"].append((features(match), 1.0 - triple_weight))
    ticket_profiles = {role: _weighted_profile(ticket_samples[role])
                       for role in ("triple", "dry_top1", "dry_top2", "dry_top3")}

    model = {"version": 3, "trained_before": before_contest,
             "training_matches": len(rows), "calibration_bins": bins, "profiles": profiles}
    model["training_contests"] = len(contests)
    model["trained_until"] = max(contests)
    model["p14_profile_contests"] = p14_contests
    model["ticket_profiles"] = ticket_profiles
    model["global_ticket_profile"] = _profile_rows(global_ticket_rows)
    Path(model_path).parent.mkdir(parents=True, exist_ok=True)
    Path(model_path).write_text(json.dumps(model, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return model


if __name__ == "__main__":
    model = train("data/concursos_anteriores.csv", "models/model.json")
    print(f"Modelo treinado com {model['training_matches']} partidas.")
