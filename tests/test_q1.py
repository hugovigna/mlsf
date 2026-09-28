import os, sys, tempfile, unittest
from itertools import permutations
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import generator, meowdoku


def sat(cl, true_vars):
    return all(any((l > 0) == (abs(l) in true_vars) for l in c) for c in cl)


class Q1(unittest.TestCase):
    def test_placements_count(self):
        # nombre de permutations sans adjacence : 0,0,2,14 pour N=2,3,4,5
        for n, cnt in ((2, 0), (3, 0), (4, 2), (5, 14)):
            self.assertEqual(sum(all(abs(p[i] - p[i + 1]) >= 2 for i in range(n - 1))
                                 for p in permutations(range(n))), cnt)

    def test_generated_grids(self):
        for n in range(4, 9):
            for seed in range(20):
                g, cats = generator.generate(n, seed)
                self.assertTrue(meowdoku.is_valid(g, cats))
                cl = meowdoku.encode(g)
                self.assertTrue(sat(cl, {meowdoku.var(i, j, n) for i, j in cats}))
                self.assertTrue(self.connected(g, n))

    def test_encoding_equiv_rules(self):
        # modèles à N chats (permutations) <=> configurations valides, sur grilles quelconques
        for n in (4, 5, 6):
            for seed in range(5):
                g, _ = generator.generate(n, seed)
                cl = meowdoku.encode(g)
                for p in permutations(range(n)):
                    cats = list(enumerate(p))
                    self.assertEqual(sat(cl, {meowdoku.var(i, j, n) for i, j in cats}),
                                     meowdoku.is_valid(g, cats))

    def test_files(self):
        with tempfile.TemporaryDirectory() as d:
            g, _ = generator.generate(6, 1)
            generator.write_grid(d + "/g.txt", g)
            self.assertEqual(meowdoku.parse_grid(d + "/g.txt"), g)

    @staticmethod
    def connected(g, n):
        for z in set(x for r in g for x in r):
            cells = {(i, j) for i in range(n) for j in range(n) if g[i][j] == z}
            seen, st = set(), [next(iter(cells))]
            while st:
                i, j = st.pop()
                if (i, j) in seen: continue
                seen.add((i, j))
                st += [c for c in ((i+1, j), (i-1, j), (i, j+1), (i, j-1)) if c in cells]
            if seen != cells: return False
        return True


if __name__ == "__main__":
    unittest.main()
