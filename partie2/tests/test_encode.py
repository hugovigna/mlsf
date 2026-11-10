"""Tests de la traduction en FNC (Q1 et Q4).

Principe : pour un petit modèle, la FNC doit avoir EXACTEMENT les mêmes solutions que le modèle
(restreintes aux variables du modèle, donc sans les variables auxiliaires). On énumère les
solutions de la FNC avec le solveur et celles du modèle avec l'interprète de référence
(tests/oracle.py), qui ne compile rien, et on compare les deux ensembles.
"""
import random
import unittest

from tests import helpers
from tests.helpers import sat_solutions, as_set
from tests.oracle import all_solutions
import csp
import encode


def same_solutions(test, text, amo="pairwise"):
    attendu = as_set(all_solutions(text))
    obtenu = as_set(sat_solutions(text, amo))
    test.assertEqual(obtenu, attendu, text)
    return len(attendu)


class TestDomaines(unittest.TestCase):
    def test_encodage_direct(self):
        model, enc = csp.compile_text("var x : 1..3;")
        self.assertEqual(enc.nvars, 3)
        # (x1 ou x2 ou x3) et les trois clauses binaires
        self.assertEqual(sorted(map(sorted, enc.clauses)), [[-3, -2], [-3, -1], [-2, -1], [1, 2, 3]])

    def test_booleen_sans_clause(self):
        model, enc = csp.compile_text("var b : bool;")
        self.assertEqual((enc.nvars, enc.clauses), (1, []))

    def test_chaque_case_a_une_seule_valeur(self):
        self.assertEqual(same_solutions(self, "var x : 1..3; var b : bool;"), 6)


class TestComparaisons(unittest.TestCase):
    def test_toutes_les_comparaisons_entre_deux_cases(self):
        for op in ("=", "!=", "<", "<=", ">", ">="):
            texte = f"var x : 1..4; var y : 2..5; constraint x {op} y;"
            same_solutions(self, texte)

    def test_case_et_constante_des_deux_cotes(self):
        for op in ("=", "!=", "<", "<=", ">", ">="):
            for k in (0, 1, 2, 3, 4):       # y compris hors du domaine 1..3
                same_solutions(self, f"var x : 1..3; constraint x {op} {k};")
                same_solutions(self, f"var x : 1..3; constraint {k} {op} x;")

    def test_taille_des_formules(self):
        # x <= 2 sur 1..3 : un seul littéral négatif, pas de variable auxiliaire
        model, enc = csp.compile_text("var x : 1..3; constraint x <= 2;")
        self.assertIn([-3], enc.clauses)
        self.assertEqual(enc.nvars, 3)
        # x != y : une clause binaire par valeur commune
        model, enc = csp.compile_text("var x : 1..3; var y : 1..3; constraint x != y;")
        self.assertEqual(len(enc.clauses), 4 + 4 + 3)

    def test_enum(self):
        texte = "enum C = { R, G, B }; var x : C; var y : C; constraint x < y; constraint y != B;"
        self.assertEqual(same_solutions(self, texte), 1)

    def test_booleens(self):
        for op in ("=", "!="):
            same_solutions(self, f"var a : bool; var b : bool; var c : bool; constraint (a and b) {op} c;")


class TestGlobales(unittest.TestCase):
    def test_globales_sur_booleens(self):
        for amo in ("pairwise", "sinz"):
            for g in ("atLeastOne", "atMostOne", "exactlyOne"):
                texte = f"array b[6] : bool; constraint {g}(b[*]);"
                same_solutions(self, texte, amo)

    def test_all_different(self):
        for amo in ("pairwise", "sinz"):
            self.assertEqual(same_solutions(self, "array a[3] : 1..3; constraint allDifferent(a[*]);", amo), 6)
            same_solutions(self, "var x : 1..3; var y : 2..4; constraint allDifferent(x, y, 3);", amo)

    def test_globale_sous_negation_ou_implication(self):
        # Le compteur séquentiel n'est correct qu'en position positive : sous un not ou à gauche
        # d'une implication, l'encodage doit retomber sur le deux à deux.
        for amo in ("pairwise", "sinz"):
            base = "array b[6] : bool; var p : bool; "
            same_solutions(self, base + "constraint not atMostOne(b[*]);", amo)
            same_solutions(self, base + "constraint p -> not atMostOne(b[*]);", amo)
            same_solutions(self, base + "constraint atMostOne(b[*]) -> p;", amo)
            same_solutions(self, base + "constraint p or exactlyOne(b[*]);", amo)

    def test_sinz_est_plus_court(self):
        texte = "array b[20] : bool; constraint atMostOne(b[*]);"
        _, deux_a_deux = csp.compile_text(texte, "pairwise")
        _, sinz = csp.compile_text(texte, "sinz")
        self.assertEqual(len(deux_a_deux.clauses), 20 * 19 // 2)
        self.assertEqual(len(sinz.clauses), 3 * 20 - 4)
        self.assertEqual(sinz.nvars, 20 + 19)


class TestTseitin(unittest.TestCase):
    def test_formules_booleennes_aleatoires(self):
        """Q1 : sur des formules propositionnelles aléatoires, la FNC est équivalente à la formule."""
        rng = random.Random(1)
        noms = ["a", "b", "c", "d"]

        def formule(prof):
            if prof == 0 or rng.random() < 0.2:
                return rng.choice(noms)
            op = rng.choice(["not", "and", "or", "->"])
            if op == "not":
                return f"not ({formule(prof - 1)})"
            return f"({formule(prof - 1)}) {op} ({formule(prof - 1)})"

        decl = "".join(f"var {n} : bool; " for n in noms)
        for _ in range(60):
            texte = decl + f"constraint {formule(4)};"
            same_solutions(self, texte)

    def test_clause_sans_variable_auxiliaire(self):
        for f in ("a or b or c", "a -> b", "not (a and b)", "a -> b or c"):
            model, enc = csp.compile_text(f"var a : bool; var b : bool; var c : bool; constraint {f};")
            self.assertEqual(enc.nvars, 3, f)
            self.assertEqual(len(enc.clauses), 1, f)

    def test_contrainte_fausse(self):
        model, enc = csp.compile_text("constraint 1 = 2;")
        self.assertEqual(enc.clauses, [[]])


class TestDimacs(unittest.TestCase):
    def test_sortie_dimacs_et_decodage(self):
        model, enc = csp.compile_text("enum C = { R, G }; var c : C; var b : bool; constraint c = G and b;")
        texte = encode.to_dimacs(enc, model)
        self.assertIn("c var 1 c = R", texte)
        self.assertIn("c var 3 b", texte)
        self.assertIn(f"p cnf {enc.nvars} {len(enc.clauses)}", texte)
        valeurs = encode.decode(enc, model, csp.solve(enc.clauses, enc.nvars))
        self.assertEqual(valeurs, [("c", "G"), ("b", "true")])


if __name__ == "__main__":
    unittest.main()
