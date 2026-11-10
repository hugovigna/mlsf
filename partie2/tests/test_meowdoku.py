"""Question 6 : les modèles de Meowdoku contre le vérificateur indépendant et la recherche exhaustive."""
import os
import random
import sys
import unittest

import meow_csp as mc
from tests.helpers import RACINE

sys.path.append(os.path.join(RACINE, "..", "partie1"))
import generator                       # générateur de grilles carrées de la partie I

SUJET = """GRID 6 6
ZONES A B C D E F
A B C B B D
A B B B B D
A A B D D D
A A A E D D
A A A A D D
F A D D D D
"""


class TestMeowdoku(unittest.TestCase):
    def test_donnees_du_sujet(self):
        zones, grille = mc.lire_grille(SUJET)
        d = mc.donnees(zones, grille)
        self.assertIn("enum Zone = { A, B, C, D, E, F };", d)
        self.assertIn("[A, B, C, B, B, D]", d)

    def test_noms_de_region_reserves(self):
        # la 11e région du générateur s'appelle K, la 13e M, la 14e N : ils sont renommés
        zones = [chr(65 + z) for z in range(14)]
        self.assertEqual(mc.nom_csp("K"), "ZK")
        self.assertEqual(mc.nom_csp("A"), "A")
        self.assertIn("ZK", mc.donnees(zones, [zones]))

    def test_sujet_tous_les_modeles(self):
        zones, grille = mc.lire_grille(SUJET)
        solutions = mc.recherche_exhaustive(grille)
        for nom in mc.MODELES:
            for amo in ("pairwise", "sinz"):
                chats = mc.chats_depuis_solution(mc.resoudre(mc.modele(SUJET, nom), amo), zones)
                self.assertTrue(mc.est_valide(grille, chats), (nom, amo))
                self.assertIn(chats, solutions)

    def test_verificateur_refuse_les_erreurs(self):
        _, grille = mc.lire_grille(SUJET)
        bonne = mc.recherche_exhaustive(grille)[0]
        self.assertTrue(mc.est_valide(grille, bonne))
        self.assertFalse(mc.est_valide(grille, bonne[:-1]))                      # région sans chat
        self.assertFalse(mc.est_valide(grille, [(1, 1)] + bonne[1:]))            # mauvaise région
        self.assertFalse(mc.est_valide(grille, [(1, 1), (2, 2)] + bonne[2:]))    # voisins

    def test_grilles_carrees_de_la_partie_1(self):
        """Les trois modèles répondent comme la recherche exhaustive (SAT/UNSAT) et leurs
        solutions sont valides ; les modèles 1, 2 et 2alo ont les mêmes solutions."""
        for n in (4, 5, 6):
            for graine in range(8):
                texte = generator_texte(n, graine)
                zones, grille = mc.lire_grille(texte)
                exhaustif = mc.recherche_exhaustive(grille)
                for nom in mc.MODELES:
                    valeurs = mc.resoudre(mc.modele(texte, nom))
                    if not exhaustif:
                        self.assertIsNone(valeurs, (n, graine, nom))
                    else:
                        chats = mc.chats_depuis_solution(valeurs, zones)
                        self.assertIn(chats, exhaustif, (n, graine, nom))

    def test_grilles_rectangulaires_modele_general(self):
        """6.5 : sur de petites grilles quelconques, SAT/UNSAT identique à la recherche
        exhaustive, et toute solution trouvée est valide."""
        rng = random.Random(7)
        vues = {"SAT": 0, "UNSAT": 0}
        for _ in range(40):
            n, m = rng.randint(1, 5), rng.randint(1, 5)
            k = rng.randint(1, min(n * m, 6))
            zones, grille = mc.grille_aleatoire(n, m, k, rng)
            texte = mc.texte_grille(zones, grille)
            exhaustif = mc.recherche_exhaustive(grille)
            for amo in ("pairwise", "sinz"):
                valeurs = mc.resoudre(mc.modele(texte, "general"), amo)
                if valeurs is None:
                    self.assertEqual(exhaustif, [], texte)
                else:
                    chats = mc.chats_depuis_solution(valeurs, zones)
                    self.assertTrue(mc.est_valide(grille, chats), texte)
            vues["UNSAT" if not exhaustif else "SAT"] += 1
        self.assertGreater(vues["SAT"], 3)
        self.assertGreater(vues["UNSAT"], 3)


def generator_texte(n, graine):
    """Une grille n x n : les graines paires viennent du générateur de la partie I (toujours
    satisfaisable), les impaires sont aléatoires avec n régions (souvent insatisfaisables)."""
    if graine % 2 == 0:
        grille, _ = generator.generate(n, graine)
        zones = sorted({z for ligne in grille for z in ligne})
    else:
        zones, grille = mc.grille_aleatoire(n, n, n, random.Random(graine))
    return mc.texte_grille(zones, grille)


if __name__ == "__main__":
    unittest.main()
