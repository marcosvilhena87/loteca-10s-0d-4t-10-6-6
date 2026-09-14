"""Shared data, ranking, feature and constraint utilities for Loteca."""

from __future__ import annotations

import csv
import math
import unicodedata
from dataclasses import dataclass
from pathlib import Path

OUTCOMES = ("1", "X", "2")
RANK_PRIORITY = {"1": 0, "2": 1, "X": 2}


def _number(value: str) -> float:
    return float(value.strip().replace(",", "."))


def normalize_team(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return value.upper().replace("-", " ").strip()


def is_team(value: str, name: str) -> bool:
    """Match both the canonical ``TEAM/UF`` form and names without state."""
    actual, wanted = normalize_team(value), normalize_team(name)
    return actual == wanted or actual.split("/")[0] == wanted.split("/")[0]


@dataclass(frozen=True)
class Match:
    contest: int
    game: int
    home: str
    away: str
    probabilities: dict[str, float]
    ranking: tuple[str, str, str]
    actual: str | None = None

    @property
    def ranked_probabilities(self) -> tuple[float, float, float]:
        return tuple(self.probabilities[x] for x in self.ranking)

    @property
    def actual_rank(self) -> int | None:
        return self.ranking.index(self.actual) + 1 if self.actual else None


def read_matches(path: str | Path, require_results: bool = False) -> list[Match]:
    matches: list[Match] = []
    # The supplied exports are Latin-1; utf-8-sig supports clean future exports.
    raw = Path(path).read_bytes()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("latin-1")
    for row in csv.DictReader(text.splitlines(), delimiter=";"):
        probabilities = {o: _number(row[f"p({o.lower()})"]) for o in OUTCOMES}
        total = sum(probabilities.values())
        if total <= 0:
            raise ValueError(f"probabilidades inválidas no jogo {row['Jogo']}")
        probabilities = {o: p / total for o, p in probabilities.items()}
        ranking = tuple(sorted(OUTCOMES, key=lambda o: (-probabilities[o], RANK_PRIORITY[o])))
        marked = [o for o in OUTCOMES if row.get(o, "0").strip() == "1"]
        actual = marked[0] if len(marked) == 1 else None
        if require_results and actual is None:
            raise ValueError(f"resultado ausente/ambíguo no concurso {row['Concurso']}, jogo {row['Jogo']}")
        matches.append(Match(int(row["Concurso"]), int(row["Jogo"]), row["Mandante"],
                             row["Visitante"], probabilities, ranking, actual))
    return matches


def features(match: Match) -> dict[str, float]:
    a, b, c = match.ranked_probabilities
    entropy = -sum(p * math.log(max(p, 1e-12)) for p in (a, b, c)) / math.log(3)
    return {"top1": a, "top2": b, "top3": c, "gap12": a-b,
            "gap23": b-c, "balance": entropy}


def validate_ticket(matches: list[Match], picks: dict[int, str]) -> dict[str, object]:
    if len(matches) != 14 or set(picks) != {m.game for m in matches}:
        raise ValueError("o bilhete deve conter exatamente os 14 jogos")
    triples = sum(p == "1X2" for p in picks.values())
    doubles = sum(len(p) == 2 for p in picks.values())
    dry = sum(p in OUTCOMES for p in picks.values())
    counts = {1: 0, 2: 0, 3: 0}
    flamengo_ok = True
    for match in matches:
        pick = picks[match.game]
        included = set(OUTCOMES if pick == "1X2" else pick)
        for rank, outcome in enumerate(match.ranking, 1):
            counts[rank] += outcome in included
        if is_team(match.home, "FLAMENGO/RJ"):
            flamengo_ok &= "1" in included
        if is_team(match.away, "FLAMENGO/RJ"):
            flamengo_ok &= "2" in included
    valid = (triples, doubles, dry) == (4, 0, 10) and counts == {1: 10, 2: 6, 3: 6} and flamengo_ok
    return {"valid": valid, "triples": triples, "doubles": doubles, "dry": dry,
            "rank_counts": counts, "flamengo_ok": flamengo_ok}
