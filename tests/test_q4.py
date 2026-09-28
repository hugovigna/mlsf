import os, random, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import dpll, generator, heuristics, meowdoku
from tests.test_q2_2 import force_brute, modele_ok

# exemple du sujet : (x1 v x2 v -x4) ^ (x2 v x3) ^ (x1 v -x2 v x4 v -x5)
EX = {frozenset(c) for c in ([1, 2, -4], [2, 3], [1, -2, 4, -5])}


class Q4(unittest.TestCase):
    def test_exemple_du_sujet(self):
        h = lambda nom: heuristics.creer(nom, EX)(EX)
        self.assertEqual(h("H1"), 1)
        self.assertEqual(h("H2d"), 2)    # #(x2)=3, 2 positifs >= 1 negatif
        self.assertEqual(h("H3d"), 1)    # occ(x1)=occ(x2)=2 -> plus petite variable
        self.assertEqual(h("H4d"), 2)    # k=2 : x2 et x3 a egalite -> plus petite
        self.assertEqual(h("H7d"), 2)    # 1/8+1/4 = 3/8
        self.assertEqual(h("H8"), 2)
        self.assertEqual(h("H2s"), 2)
        self.assertEqual(h("H7s"), 2)

    def test_polarite_negative(self):
        F = {frozenset(c) for c in ([-1, 2], [-1, 3], [-1, -2, 3], [1, 2, 3])}
        self.assertEqual(heuristics.creer("H2d", F)(F), -1)   # 1 : 1 positif, 3 negatifs
        self.assertEqual(heuristics.creer("H3d", F)(F), -1)

    def test_correction_toutes_heuristiques(self):
        rng = random.Random(1)
        for nom in heuristics.NOMS:
            for _ in range(100):
                n = rng.randint(1, 8)
                F = {frozenset(rng.choice([-1, 1]) * v for v in rng.sample(range(1, n + 1), rng.randint(1, min(3, n))))
                     for _ in range(rng.randint(1, 30))}
                attendu = force_brute(F, n)
                self.assertEqual(dpll.dpll_sat(F, heuristics.creer(nom, F)), attendu, nom)
                s, v = dpll.dpll(F, heuristics.creer(nom, F))
                self.assertEqual(s, attendu, nom)
                if s:
                    self.assertTrue(modele_ok(F, v), nom)

    def test_meowdoku(self):
        for nom in heuristics.NOMS:
            for n in (5, 6, 8):
                g, _ = generator.generate(n, n)
                F = {frozenset(c) for c in meowdoku.encode(g)}
                s, v = dpll.dpll(F, heuristics.creer(nom, F))
                self.assertTrue(s and modele_ok(F, v), nom)
                self.assertTrue(meowdoku.is_valid(g, [((x - 1) // n, (x - 1) % n) for x in v if x > 0]), nom)


if __name__ == "__main__":
    unittest.main()
