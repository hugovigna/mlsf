import os, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dimacs import parse_dimacs


class Q2_1(unittest.TestCase):
    def lire(self, texte):
        with tempfile.TemporaryDirectory() as d:
            p = d + "/x.cnf"
            open(p, "w").write(texte)
            return parse_dimacs(p)

    def test_lampes(self):
        n, f = self.lire("c lampes\np cnf 3 4\n1 2 3 0\n-1 -2 0\n-2 -3 0\n2 3 0\n")
        self.assertEqual(n, 3)
        self.assertEqual(f, {frozenset({1, 2, 3}), frozenset({-1, -2}),
                             frozenset({-2, -3}), frozenset({2, 3})})

    def test_clause_vide_et_ordre(self):
        n, f = self.lire("p cnf 2 2\n0\n2 -1 0\n")
        self.assertEqual(f, {frozenset(), frozenset({-1, 2})})

    def test_fin_satlib(self):
        n, f = self.lire("p cnf 2 1\n1 -2 0\n%\n0\n")
        self.assertEqual(f, {frozenset({1, -2})})


if __name__ == "__main__":
    unittest.main()
