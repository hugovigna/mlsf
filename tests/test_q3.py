import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import generator, meowdoku, solve_grid

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Q3(unittest.TestCase):
    def test_grille_du_sujet(self):
        g = meowdoku.parse_grid(RACINE + "/data/grids/sujet.txt")
        self.assertTrue(meowdoku.is_valid(g, solve_grid.resoudre(g)))

    def test_grilles_generees(self):
        for n in range(4, 11):
            g, _ = generator.generate(n, n)
            self.assertTrue(meowdoku.is_valid(g, solve_grid.resoudre(g)))

    def test_sans_solution(self):
        # les 2 seuls placements de N=4 ont un chat dans chacune des lignes 1 et 2, donc deux dans A
        g = [list("AAAA"), list("AAAA"), list("BBBB"), list("CCCD")]
        self.assertIsNone(solve_grid.resoudre(g))


if __name__ == "__main__":
    unittest.main()
