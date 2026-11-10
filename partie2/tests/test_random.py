"""Test aléatoire de tout le compilateur contre l'interprète de référence (tests/oracle.py).

On tire de petits modèles au hasard (comparaisons, arithmétique connue, connecteurs, tableaux,
boucles, énumérés, contraintes globales) et on vérifie que la FNC a exactement les mêmes
solutions que le modèle, avec les deux encodages de « au plus un ». Les graines sont fixes :
le test est reproductible.
"""
import random
import unittest

from tests.helpers import sat_solutions, as_set
from tests.oracle import all_solutions

PRELUDE = """
enum Color = { Red, Green, Blue };
const K = 2;
var a : 1..2;
var c : Color;
var p : bool;
var q : bool;
array t[3] : 1..2;
array u[2] : bool;
"""


MAX_SOLUTIONS = 80


class Generateur:
    def __init__(self, rng):
        self.rng = rng

    def entier(self):
        """Un terme entier : variable, case de tableau, constante, arithmétique sur du connu."""
        return self.rng.choice(["a", "t[1]", "t[2]", "t[3]", "t[K]", "t[K + 1]", "a", "t[2]",
                                "0", "1", "2", "3", "K", "(K - 1)", "abs(1 - 3)"])

    def atome(self):
        r = self.rng
        k = r.randrange(7)
        if k == 0:
            return f"{self.entier()} {r.choice(['=', '!=', '<', '<=', '>', '>='])} {self.entier()}"
        if k == 1:
            return f"c {r.choice(['=', '!=', '<', '<='])} {r.choice(['Red', 'Green', 'Blue', 'c'])}"
        if k == 2:
            return r.choice(["p", "q", "u[1]", "u[2]", "p = q", "p != u[1]"])
        if k == 3:
            return r.choice(["allDifferent(t[*])", "allDifferent(a, t[1], 2)", "allDifferent(t[1], t[2])",
                             "allDifferent(c, Red)"])
        if k == 4:
            args = r.choice(["p, q, u[1]", "u[*]", "p, a = 1, a = 2, a = 3, q, t[1] < 2",
                             "u[1], c = Red, c = Green, c = Blue, p, q"])
            return f"{r.choice(['atLeastOne', 'atMostOne', 'exactlyOne'])}({args})"
        if k == 5:
            return f"{r.choice(['atLeastOne', 'atMostOne', 'exactlyOne'])}(t[j] = 2 for j in 1..3 where j != K)"
        return r.choice(["1 < 2", "2 < 1"])

    def formule(self, prof):
        r = self.rng
        if prof == 0 or r.random() < 0.25:
            return self.atome()
        op = r.choice(["not", "and", "or", "->"])
        if op == "not":
            return f"not ({self.formule(prof - 1)})"
        return f"({self.formule(prof - 1)}) {op} ({self.formule(prof - 1)})"

    def modele(self):
        lignes = [PRELUDE]
        for _ in range(self.rng.randint(1, 3)):
            if self.rng.random() < 0.25:
                lignes.append(f"forall i in 1..K {{ constraint {self.formule(2).replace('K + 1', 'i')}; }}")
            else:
                lignes.append(f"constraint {self.formule(3)};")
        return "\n".join(lignes)


class TestAleatoire(unittest.TestCase):
    def test_compilateur_contre_oracle(self):
        gen = Generateur(random.Random(2026))
        testes = 0
        for n in range(150):
            texte = gen.modele()
            attendu = as_set(all_solutions(texte))
            if len(attendu) > MAX_SOLUTIONS:
                continue            # énumérer des centaines de solutions avec DPLL serait trop lent
            testes += 1
            for amo in ("pairwise", "sinz"):
                obtenu = as_set(sat_solutions(texte, amo))
                self.assertEqual(obtenu, attendu, f"modèle {n} ({amo}) :\n{texte}")
        self.assertGreater(testes, 20, "trop peu de modèles testés")


if __name__ == "__main__":
    unittest.main()
