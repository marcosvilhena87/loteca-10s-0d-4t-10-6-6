"""Run training and selection, printing an auditable final ticket."""

from scripts.common import features, read_matches
from scripts.predict_results import predict
from scripts.train_model import train


def main() -> None:
    upcoming = read_matches("data/proximo_concurso.csv")
    contest = upcoming[0].contest
    model = train("data/concursos_anteriores.csv", "models/model.json", before_contest=contest)
    result = predict("data/proximo_concurso.csv", "models/model.json", "output/predictions.csv")
    print(f"Concurso {contest} | histórico: {model['training_matches']} jogos | score: {result['score']:.6f}")
    for row in result["detail"]:
        m, f = row["match"], features(row["match"])
        ranking = " > ".join(f"{o} ({m.probabilities[o]:.3f})" for o in m.ranking)
        position = "triplo" if row["role"] is None else f"seco top{row['role']}"
        factors = ", ".join(f"{k}={v:+.3f}" for k, v in row["contributions"].items())
        print(f"J{m.game:02d} {m.home} x {m.away}: {row['pick']:<3} [{position}] | {ranking}")
        print(f"    p(1)={m.probabilities['1']:.3f} p(X)={m.probabilities['X']:.3f} p(2)={m.probabilities['2']:.3f}; balance={f['balance']:.3f}; {factors}")
    check = result["validation"]
    print("\n=== SCORE DO BILHETE ===")
    print(f"Score P14: {result['score_p14']:.6f}")
    for role in ("triple", "dry_top1", "dry_top2", "dry_top3"):
        balance = result["ticket_features"][f"{role}_balance_mean"]
        print(f"{role:>8}: equilíbrio médio={balance:.3f}")
    print("Hard Constraints:", "OK" if check["valid"] else "FALHA", check)
    print("Regra Flamengo:", "OK" if check["flamengo_ok"] else "FALHA")
    print("Preferência Palmeiras:", "vitória excluída" if result["avoids_palmeiras_win"] else "não aplicada sem perda relevante")
    print("Saída: output/predictions.csv")


if __name__ == "__main__":
    main()
