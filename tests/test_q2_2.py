import os, random, sys, unittest
from itertools import product
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import dpll, generator, meowdoku


def force_brute(F, n):
    return any(all(any((l > 0) == a[abs(l) - 1] for l in c) for c in F)
               for a in product([False, True], repeat=n))


def modele_ok(F, v):
    return all(-l not in v for l in v) and all(c & v for c in F)


class Q2_2(unittest.TestCase):
    def test_lampes(self):
        F = {frozenset(c) for c in ([1, 2, 3], [-1, -2], [-2, -3], [2, 3])}
        self.assertTrue(dpll.dpll_sat(F))
        s, v = dpll.dpll(F)
        self.assertTrue(s and modele_ok(F, v))

    def test_cas_limites(self):
        self.assertEqual(dpll.dpll(set()), (True, set()))
        self.assertFalse(dpll.dpll_sat({frozenset()}))
        self.assertFalse(dpll.dpll_sat({frozenset({1}), frozenset({-1})}))

    def test_aleatoire_vs_force_brute(self):
        rng = random.Random(0)
        for _ in range(300):
            n = rng.randint(1, 8)
            F = {frozenset(rng.choice([-1, 1]) * v for v in rng.sample(range(1, n + 1), rng.randint(1, min(3, n))))
                 for _ in range(rng.randint(1, 30))}
            attendu = force_brute(F, n)
            self.assertEqual(dpll.dpll_sat(F), attendu)
            s, v = dpll.dpll(F)
            self.assertEqual(s, attendu)
            if s:
                self.assertTrue(modele_ok(F, v))

    def test_meowdoku(self):
        for n in (4, 5, 6, 8):
            g, _ = generator.generate(n, n)
            F = {frozenset(c) for c in meowdoku.encode(g)}
            s, v = dpll.dpll(F)
            self.assertTrue(s and modele_ok(F, v))
            chats = [((x - 1) // n, (x - 1) % n) for x in v if x > 0]
            self.assertTrue(meowdoku.is_valid(g, chats))


if __name__ == "__main__":
    unittest.main()
