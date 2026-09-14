"""Exhaustively select the best valid 10-dry/4-triple ticket."""

from __future__ import annotations

import csv
import itertools
import json
import math
from pathlib import Path

from scripts.common import OUTCOMES, features, is_team, read_matches, validate_ticket


def _role_score(match, rank: int, model: dict) -> tuple[float, dict[str, float]]:
    probability = match.ranked_probabilities[rank-1]
    bucket = min(9, int(probability * 10))
    hits, total = model["calibration_bins"][str(rank)][bucket]
    contributions = {"calibrated_hit": math.log(max(hits / total, 1e-9))}
    # A small profile term breaks ties in favour of P14-like probability shapes.
    f = features(match)
    for name in ("gap12", "gap23", "balance"):
        profile = model["profiles"][str(rank)][name]
        contributions[name] = -.04 * ((f[name] - profile["mean"]) / profile["std"]) ** 2
    ticket_profile = model.get("ticket_profiles", {}).get(f"dry_top{rank}")
    if ticket_profile:
        contributions["ticket_p14"] = -.025 * sum(
            ((f[name] - ticket_profile[name]["mean"]) / ticket_profile[name]["std"]) ** 2
            for name in FEATURE_NAMES
        )
    return sum(contributions.values()), contributions


FEATURE_NAMES = ("top1", "top2", "top3", "gap12", "gap23", "balance")


def _triple_score(match, model: dict) -> tuple[float, dict[str, float]]:
    profile = model.get("ticket_profiles", {}).get("triple")
    if not profile:  # backwards compatibility with version-1 model files
        return 0.0, {}
    f = features(match)
    contributions = {name: -.025 * ((f[name] - profile[name]["mean"]) /
                                     profile[name]["std"]) ** 2
                     for name in FEATURE_NAMES}
    return sum(contributions.values()), contributions


def select_ticket(matches, model: dict, palmeiras_tolerance: float = .03) -> dict:
    if len(matches) != 14:
        raise ValueError(f"esperados 14 jogos; recebidos {len(matches)}")
    options = {}
    for i, match in enumerate(matches):
        options[i] = {r: _role_score(match, r, model) for r in (1, 2, 3)}
    triple_options = {i: _triple_score(match, model) for i, match in enumerate(matches)}
    indices = range(14)
    def optimize(avoid_palmeiras: bool):
        best = None
        for triples in itertools.combinations(indices, 4):
            triple_set = set(triples)
            if avoid_palmeiras and any(is_team(matches[i].home, "PALMEIRAS/SP") or
                                       is_team(matches[i].away, "PALMEIRAS/SP") for i in triples):
                continue
            # Dynamic programming visits every rank-count state without materializing
            # all 1,260 combinations for each set of triples.
            states = {(0, 0): (sum(triple_options[i][0] for i in triples), {})}
            for i in (j for j in indices if j not in triple_set):
                allowed = []
                for rank in (1, 2, 3):
                    outcome = matches[i].ranking[rank-1]
                    required = ("1" if is_team(matches[i].home, "FLAMENGO/RJ") else
                                "2" if is_team(matches[i].away, "FLAMENGO/RJ") else None)
                    forbidden = ("1" if is_team(matches[i].home, "PALMEIRAS/SP") else
                                 "2" if is_team(matches[i].away, "PALMEIRAS/SP") else None)
                    if required and outcome != required:
                        continue
                    if avoid_palmeiras and forbidden and outcome == forbidden:
                        continue
                    allowed.append(rank)
                new_states = {}
                for (n2, n3), (score, roles) in states.items():
                    for rank in allowed:
                        key = (n2 + (rank == 2), n3 + (rank == 3))
                        if key[0] > 2 or key[1] > 2:
                            continue
                        candidate = (score + options[i][rank][0], {**roles, i: rank})
                        if key not in new_states or candidate[0] > new_states[key][0]:
                            new_states[key] = candidate
                states = new_states
            if (2, 2) in states:
                score, roles = states[(2, 2)]
                if best is None or score > best[0]:
                    best = (score, roles, triples)
        return best

    unrestricted = optimize(False)
    preferred = optimize(True)
    if preferred and unrestricted and unrestricted[0] - preferred[0] <= palmeiras_tolerance:
        chosen, avoids_palmeiras = preferred, True
    else:
        chosen, avoids_palmeiras = unrestricted, False
    best = chosen
    if best is None:
        raise ValueError("nenhum palpite satisfaz as Hard Constraints")
    score, roles, triples = best
    picks = {m.game: ("1X2" if i in triples else m.ranking[roles[i]-1])
             for i, m in enumerate(matches)}
    validation = validate_ticket(matches, picks)
    if not validation["valid"]:
        raise AssertionError(f"falha interna de validação: {validation}")
    detail = []
    for i, match in enumerate(matches):
        role = None if i in triples else roles[i]
        detail.append({"match": match, "pick": picks[match.game], "role": role,
                       "contributions": (triple_options[i][1] if role is None
                                         else options[i][role][1])})
    grouped = {"dry_top1": [], "dry_top2": [], "dry_top3": [], "triple": []}
    for row in detail:
        grouped["triple" if row["role"] is None else f"dry_top{row['role']}"].append(
            features(row["match"]))
    ticket_features = {}
    for role, values in grouped.items():
        for name in FEATURE_NAMES:
            ticket_features[f"{role}_{name}_mean"] = sum(v[name] for v in values) / len(values)
    return {"score": score, "avoids_palmeiras_win": avoids_palmeiras,
            "score_p14": score, "ticket_features": ticket_features,
            "picks": picks, "validation": validation, "detail": detail}


def predict(next_path: str, model_path: str, output_path: str) -> dict:
    matches = read_matches(next_path)
    model = json.loads(Path(model_path).read_text(encoding="utf-8"))
    result = select_ticket(matches, model)
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, delimiter=";", lineterminator="\n")
        writer.writerow(["Concurso", "Jogo", "Mandante", "Visitante", "Palpite", "Posicao"])
        for row in result["detail"]:
            m = row["match"]
            writer.writerow([m.contest, m.game, m.home, m.away, row["pick"],
                             "triplo" if row["role"] is None else f"top{row['role']}"])
    return result
