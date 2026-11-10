"""Les exemples du dossier exemples/, lancés par la ligne de commande, vérifiés par des
vérificateurs indépendants (Q5 de l'énoncé) : on ne regarde que le texte affiché."""
import os
import re
import subprocess
import sys
import unittest

from tests.helpers import RACINE


def lancer(fichier, *options):
    """Exécute `python csp.py exemples/fichier --solve` et renvoie (statut, {nom: valeur})."""
    p = subprocess.run([sys.executable, "csp.py", os.path.join("exemples", fichier), "--solve", *options],
                       cwd=RACINE, capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    lignes = p.stdout.splitlines()
    valeurs = {}
    for l in lignes[1:]:
        nom, valeur = l.split(" = ")
        valeurs[nom] = valeur
    return lignes[0], valeurs


def tableau(valeurs, nom, *dims):
    """Lit nom[i] ou nom[i][j] dans le dictionnaire de la sortie."""
    return valeurs[nom + "".join(f"[{d}]" for d in dims)]


class TestExemples(unittest.TestCase):
    def test_reines(self):
        statut, v = lancer("queens.csp")
        self.assertEqual(statut, "s SATISFIABLE")
        q = [int(tableau(v, "queen", i)) for i in range(1, 9)]
        self.assertEqual(sorted(q), list(range(1, 9)))                # une reine par colonne
        for i in range(8):
            for j in range(i + 1, 8):
                self.assertNotEqual(abs(q[i] - q[j]), j - i)          # pas de diagonale

    def test_coloriage_de_petersen(self):
        statut, v = lancer("coloring.csp")
        self.assertEqual(statut, "s SATISFIABLE")
        aretes = [(1, 2), (2, 3), (3, 4), (4, 5), (5, 1), (6, 8), (8, 10), (10, 7), (7, 9),
                  (9, 6), (1, 6), (2, 7), (3, 8), (4, 9), (5, 10)]
        for a, b in aretes:
            self.assertNotEqual(tableau(v, "color", a), tableau(v, "color", b))
        self.assertEqual(len(v), 10)

    def test_sudoku(self):
        statut, v = lancer("sudoku.csp")
        self.assertEqual(statut, "s SATISFIABLE")
        g = [[int(tableau(v, "grid", i, j)) for j in range(1, 10)] for i in range(1, 10)]
        chiffres = list(range(1, 10))
        for i in range(9):
            self.assertEqual(sorted(g[i]), chiffres)                                  # lignes
            self.assertEqual(sorted(g[r][i] for r in range(9)), chiffres)             # colonnes
        for bi in range(3):
            for bj in range(3):
                boite = [g[3 * bi + a][3 * bj + b] for a in range(3) for b in range(3)]
                self.assertEqual(sorted(boite), chiffres)                             # boîtes
        # les indices donnés (relus dans le fichier : la ligne 1 est 5 3 0 0 7 ...)
        self.assertEqual(g[0][:5], [5, 3, g[0][2], g[0][3], 7])
        self.assertEqual(g[8][8], 9)

    def test_pigeons(self):
        statut, v = lancer("pigeonhole.csp")
        self.assertEqual(statut, "s UNSATISFIABLE")
        self.assertEqual(v, {})

    def test_les_deux_solveurs_et_les_deux_encodages_sont_d_accord(self):
        for options in (["--solver", "dpll"], ["--amo", "sinz"]):
            self.assertEqual(lancer("coloring.csp", *options)[0], "s SATISFIABLE")
            self.assertEqual(lancer("pigeonhole.csp", *options)[0], "s UNSATISFIABLE")

    def test_dimacs(self):
        p = subprocess.run([sys.executable, "csp.py", "exemples/pigeonhole.csp"],
                           cwd=RACINE, capture_output=True, text=True)
        entete = [l for l in p.stdout.splitlines() if l.startswith("p cnf")]
        self.assertEqual(len(entete), 1)
        nvars, nclauses = map(int, entete[0].split()[2:])
        clauses = [l for l in p.stdout.splitlines() if l and l[0] not in "pc"]
        self.assertEqual(len(clauses), nclauses)
        for l in clauses:                                       # chaque clause finit par 0
            nombres = list(map(int, l.split()))
            self.assertEqual(nombres[-1], 0)
            self.assertTrue(all(0 < abs(x) <= nvars for x in nombres[:-1]))

    def test_erreur_de_modele(self):
        chemin = os.path.join(RACINE, "tests", "_faux.csp")
        with open(chemin, "w") as f:
            f.write("var x : bool;\nconstraint y;\n")
        try:
            p = subprocess.run([sys.executable, "csp.py", chemin], cwd=RACINE,
                               capture_output=True, text=True)
        finally:
            os.remove(chemin)
        self.assertEqual(p.returncode, 1)
        self.assertRegex(p.stderr, r"line 2, column \d+")


if __name__ == "__main__":
    unittest.main()
