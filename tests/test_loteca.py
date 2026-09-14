import tempfile
import unittest

from scripts.common import Match, validate_ticket
from scripts.predict_results import select_ticket
from scripts.train_model import train


class LotecaTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with tempfile.NamedTemporaryFile(suffix=".json") as file:
            cls.model = train("data/concursos_anteriores.csv", file.name, before_contest=900)

    def test_training_is_temporal(self):
        self.assertEqual(self.model["trained_before"], 900)
        self.assertGreater(self.model["training_matches"], 0)
        self.assertLess(self.model["trained_until"], 900)
        self.assertGreater(self.model["p14_profile_contests"], 0)
        self.assertEqual(set(self.model["ticket_profiles"]),
                         {"triple", "dry_top1", "dry_top2", "dry_top3"})
        self.assertIn("triple_balance_mean", self.model["global_ticket_profile"])
        self.assertIn("dry_top3_gap23_mean", self.model["global_ticket_profile"])

    def test_constraints_and_team_rules(self):
        matches = []
        for i in range(14):
            home = "FLAMENGO/RJ" if i == 0 else ("PALMEIRAS/SP" if i == 1 else f"A{i}")
            matches.append(Match(1, i+1, home, f"B{i}", {"1": .6, "X": .25, "2": .15}, ("1", "X", "2")))
        result = select_ticket(matches, self.model)
        self.assertTrue(result["validation"]["valid"])
        self.assertIn("1", result["picks"][1])
        self.assertNotIn("1", result["picks"][2])
        self.assertEqual(result["validation"]["rank_counts"], {1: 10, 2: 6, 3: 6})
        self.assertIn("triple_balance_mean", result["ticket_features"])
        self.assertIn("min_dry_probability", result["ticket_features"])
        self.assertAlmostEqual(result["score_p14"],
                               result["score_local"] + result["score_global_p14"])
        self.assertLessEqual(result["score_global_p14"], 0)
        self.assertTrue(any(row["role"] is None and row["contributions"] for row in result["detail"]))

    def test_rejects_incomplete_ticket(self):
        with self.assertRaises(ValueError):
            validate_ticket([], {})


if __name__ == "__main__":
    unittest.main()
