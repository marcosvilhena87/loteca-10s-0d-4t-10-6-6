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

    def test_rejects_incomplete_ticket(self):
        with self.assertRaises(ValueError):
            validate_ticket([], {})


if __name__ == "__main__":
    unittest.main()
