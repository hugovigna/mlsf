"""Tests Q6 : lecteur DIMACS, solveur CDCL (optimized.py), interface sat.py.

Références indépendantes du solveur : force brute sur les valuations (petites formules),
DPLL de la Q2 (formules moyennes), force brute sur les placements de chats via
meowdoku.is_valid (règles du jeu, sans passer par l'encodage CNF).
"""
import itertools, os, random, subprocess, sys, tempfile, unittest
RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)
import dpll, generator, heuristics, meowdoku
from optimized import lire, luby, resoudre

# Réglages agressifs : redémarrage à chaque conflit, réduction dès qu'il y a des clauses
# apprises, activités doublées à chaque conflit (renormalisation après ~330 conflits).
AGRESSIF = dict(unite_luby=1, min_apprises=0, decroissance=0.5)


def force_brute(n, clauses):
    for bits in itertools.product((False, True), repeat=n):
        if all(any(bits[abs(x) - 1] == (x > 0) for x in c) for c in clauses):
            return True
    return False


def modele_ok(n, clauses, m):
    """m = [±1, ..., ±n] dans l'ordre, et toutes les clauses vraies."""
    if m is None or len(m) != n or any(abs(x) != i + 1 for i, x in enumerate(m)):
        return False
    vrais = set(m)
    return all(any(x in vrais for x in c) for c in clauses)


def aleatoire(rng, n, nb, kmin=1, kmax=4):
    """Formule aléatoire avec doublons et tautologies possibles (tirage avec remise)."""
    return [[rng.choice((-1, 1)) * rng.randint(1, n) for _ in range(rng.randint(kmin, kmax))]
            for _ in range(nb)]


def tiroirs(p, t):
    """p pigeons, t trous : x_{i,j} = i*t + j + 1. SAT ssi p <= t."""
    x = lambda i, j: i * t + j + 1
    cl = [[x(i, j) for j in range(t)] for i in range(p)]
    cl += [[-x(i, j), -x(k, j)] for j in range(t) for i in range(p) for k in range(i + 1, p)]
    return p * t, cl


def ecrire(texte, binaire=False):
    f = tempfile.NamedTemporaryFile("wb" if binaire else "w", suffix=".cnf", delete=False)
    f.write(texte)
    f.close()
    return f.name


class Lecteur(unittest.TestCase):
    def lit(self, texte, binaire=False):
        chemin = ecrire(texte, binaire)
        try:
            return lire(chemin)
        finally:
            os.remove(chemin)

    def test_format_du_sujet(self):
        self.assertEqual(self.lit("c lampes\np cnf 3 4\n1 2 3 0\n-1 -2 0\n-2 -3 0\n2 3 0\n"),
                         (3, [[1, 2, 3], [-1, -2], [-2, -3], [2, 3]]))

    def test_commentaires_partout_et_lignes_vides(self):
        t = "c debut\n\n   \np cnf 2 2\nc 1 2 0 (commentaire avec des nombres)\n1 2 0\n\nc fin\n-1 0\nc\n"
        self.assertEqual(self.lit(t), (2, [[1, 2], [-1]]))

    def test_espaces_tabulations_et_crlf(self):
        t = b"p cnf 3 2\r\n  \t1\t -2   3 0\r\n\t-3 0\r\n"
        self.assertEqual(self.lit(t, binaire=True), (3, [[1, -2, 3], [-3]]))

    def test_clause_sur_plusieurs_lignes_et_plusieurs_par_ligne(self):
        self.assertEqual(self.lit("p cnf 4 3\n1 2\n3 0 -1 0 4\n-4 0\n"),
                         (4, [[1, 2, 3], [-1], [4, -4]]))

    def test_dernier_zero_manquant(self):
        self.assertEqual(self.lit("p cnf 2 2\n1 0\n-1 2"), (2, [[1], [-1, 2]]))

    def test_fin_satlib(self):
        self.assertEqual(self.lit("p cnf 2 1\n1 -2 0\n%\n0\n"), (2, [[1, -2]]))

    def test_entete_trop_grand_ou_trop_petit(self):
        self.assertEqual(self.lit("p cnf 10 1\n1 0\n"), (10, [[1]]))
        self.assertEqual(self.lit("p cnf 2 1\n1 -7 0\n"), (7, [[1, -7]]))   # -7 > en-tête
        self.assertEqual(self.lit("p cnf 0 1\n-3 0\n"), (3, [[-3]]))

    def test_formule_vide_et_clause_vide(self):
        self.assertEqual(self.lit("p cnf 0 0\n"), (0, []))
        self.assertEqual(self.lit(""), (0, []))
        self.assertEqual(self.lit("p cnf 1 2\n0\n1 0\n"), (1, [[], [1]]))


class Solveur(unittest.TestCase):
    def verifie(self, n, cl, attendu=None, **reglages):
        m = resoudre(n, [list(c) for c in cl], **reglages)   # copie : le solveur permute
        if attendu is None:
            attendu = force_brute(n, cl)
        self.assertEqual(m is not None, attendu, cl)
        if m is not None:
            self.assertTrue(modele_ok(n, cl, m), (cl, m))

    def test_luby(self):
        self.assertEqual([luby(i) for i in range(1, 16)], [1, 1, 2, 1, 1, 2, 4, 1, 1, 2, 1, 1, 2, 4, 8])

    def test_formules_triviales(self):
        self.assertEqual(resoudre(0, []), [])
        self.assertEqual(len(resoudre(3, [])), 3)              # variables libres affectées
        self.assertIsNone(resoudre(0, [[]]))
        self.assertIsNone(resoudre(2, [[1, 2], [], [-1]]))     # clause vide au milieu
        self.assertIsNone(resoudre(2, [[1, 2], [-1]] + [[]]))  # clause vide en dernier

    def test_indices_extremes(self):
        # n = 1 : val a 3 cases, val[-1] = val[2] ; la variable n est la dernière case.
        for cl, sat in (([[1]], True), ([[-1]], True), ([[1], [-1]], False),
                        ([[1, 1]], True), ([[-1, -1], [1]], False), ([[1, -1]], True)):
            self.verifie(1, cl, sat)
        self.assertEqual(resoudre(1, [[-1]]), [-1])
        self.assertEqual(resoudre(1, [[1]]), [1])
        # la plus grande variable dans chaque position (surveillée, remplaçante, unitaire)
        for n in (3, 4, 50):
            self.verifie(n, [[n, -n + 1, 1], [-n], [-1, n - 1], [1 - n, n, 2]])
            self.verifie(n, [[-n, -1], [n, 1], [-n, 1], [n, -1]], False)

    def test_toutes_les_formules_a_deux_variables(self):
        clauses = [c for k in (1, 2) for c in itertools.combinations((1, -1, 2, -2), k)
                   if not (len(c) == 2 and c[0] == -c[1])]          # 8 clauses non triviales
        for r in range(len(clauses) + 1):
            for F in itertools.combinations(clauses, r):
                self.verifie(2, F)

    def test_doublons_et_tautologies(self):
        self.verifie(3, [[1, 1, 1], [-1, 2, 2], [-2, -2, 3, 3]], True)
        self.verifie(2, [[1, -1], [2, -2, 1], [1, -1]], True)        # que des tautologies
        self.verifie(2, [[1, -1, 2], [-2], [-2, 2]], True)
        self.verifie(1, [[1, -1], [1], [-1, -1]], False)

    def test_propagation_au_niveau_0(self):
        self.verifie(3, [[1], [-1, 2], [-2, 3], [-3]], False)        # conflit sans décision
        self.verifie(3, [[1], [-1, -2, 3], [-1, 2], [-3, -2]], False)  # via clause longue
        self.verifie(2, [[1], [1], [-1, 2]], True)                   # unitaire répété

    def test_longue_chaine_d_implications(self):
        n = 20000                                                    # pas de récursion
        chaine = [[-i, i + 1] for i in range(1, n)]
        m = resoudre(n, [[1]] + chaine)
        self.assertEqual(m, list(range(1, n + 1)))
        self.assertIsNone(resoudre(n, [[1]] + chaine + [[-n]]))
        longue = [[-i, -(i + 1), i + 2] for i in range(1, n - 1)]   # chaîne de clauses longues
        self.assertEqual(resoudre(n, [[1], [2]] + longue), list(range(1, n + 1)))

    def test_aleatoire_contre_force_brute(self):
        rng = random.Random(6)
        for k in range(1500):
            n = rng.randint(1, 9)
            cl = aleatoire(rng, n, rng.randint(1, 6 * n))
            self.verifie(n, cl)
            if k % 3 == 0:
                self.verifie(n, cl, **AGRESSIF)

    def test_3sat_au_seuil_contre_dpll(self):
        rng = random.Random(7)
        for _ in range(40):
            n = rng.randint(20, 45)
            cl = [[rng.choice((-1, 1)) * v for v in rng.sample(range(1, n + 1), 3)]
                  for _ in range(round(4.26 * n))]
            F = {frozenset(c) for c in cl}
            attendu = dpll.dpll(F, heuristics.creer("H4d", F))[0]
            self.verifie(n, cl, attendu)
            self.verifie(n, cl, attendu, **AGRESSIF)

    def test_tiroirs(self):
        for t in range(1, 7):
            self.verifie(*tiroirs(t, t), True)
            self.verifie(*tiroirs(t + 1, t), False)
        # beaucoup de conflits : redémarrages, réductions et renormalisation exercés
        self.verifie(*tiroirs(7, 6), False, **AGRESSIF)

    def test_variables_absentes_des_clauses(self):
        m = resoudre(10, [[3, -7], [-3]])
        self.assertTrue(modele_ok(10, [[3, -7], [-3]], m))

    def test_ne_modifie_pas_le_resultat_selon_l_ordre(self):
        rng = random.Random(8)
        for _ in range(200):
            n = rng.randint(2, 8)
            cl = aleatoire(rng, n, rng.randint(n, 5 * n), 2, 3)
            attendu = force_brute(n, cl)
            rng.shuffle(cl)
            self.verifie(n, [c[::-1] for c in cl], attendu)


def solutions_meowdoku(grille):
    """Force brute sur les règles du jeu : un chat par ligne, colonne = permutation."""
    n = len(grille)
    return [list(enumerate(p)) for p in itertools.permutations(range(n))
            if meowdoku.is_valid(grille, list(enumerate(p)))]


class Meowdoku(unittest.TestCase):
    def resout(self, grille):
        n = len(grille)
        m = resoudre(n * n, meowdoku.encode(grille))
        if m is None:
            return None
        return [((x - 1) // n, (x - 1) % n) for x in m if x > 0]

    def compare(self, lignes):
        grille = [l.split() for l in lignes]
        chats = self.resout(grille)
        attendu = solutions_meowdoku(grille)
        self.assertEqual(chats is not None, bool(attendu), lignes)
        if chats is not None:
            self.assertTrue(meowdoku.is_valid(grille, chats), (lignes, chats))
            self.assertIn(sorted(chats), attendu)

    def test_grille_du_sujet(self):
        g = meowdoku.parse_grid(os.path.join(RACINE, "data", "grids", "sujet.txt"))
        chats = self.resout(g)
        self.assertTrue(meowdoku.is_valid(g, chats))

    def test_tailles_1_2_3(self):
        self.compare(["A"])                               # un seul chat, case (0, 0)
        self.compare(["A A", "A B"])                      # n = 2 : toujours impossible
        self.compare(["A B", "A B"])
        self.compare(["A A B", "C B B", "C C B"])         # n = 3 : toujours impossible

    def test_coins_et_bords(self):
        self.compare(["A B B B", "B B B C", "D D C C", "D D D C"])   # (0,0) forcé, coin
        self.compare(["A C C C C", "C C C C C", "C C D D D", "E E E E D", "E E E E B"])  # (0,0) et (4,4)
        self.compare(["A C C C", "C B C C", "C C D D", "C C D D"])   # (0,0),(1,1) diagonale collée
        self.compare(["C C C A", "C C B C", "C C D D", "C C D D"])   # (0,3),(1,2) anti-diagonale au bord
        self.compare(["A C C B", "C C C C", "D D D D", "D D D D"])   # (0,0),(0,3) même ligne
        self.compare(["A C C C", "C C C C", "D D C C", "B D D D"])   # (0,0),(3,0) même colonne
        self.compare(["C C C C", "C C C C", "C C C C", "A C C B"])   # dernière ligne, coins opposés

    def test_regions_confinees(self):
        self.compare(["A A A A", "B B B B", "C C D D", "C C D D"])   # deux lignes pleines voisines
        self.compare(["A A B B", "C C C C", "C D D C", "C C C C"])   # A et B dans la même ligne
        self.compare(["A B C D E", "A B C D E", "A B C D E", "A B C D E", "A B C D E"])  # colonnes

    def test_grilles_aleatoires_contre_force_brute(self):
        rng = random.Random(9)
        for _ in range(150):
            n = rng.randint(4, 7)
            graines = rng.sample([(i, j) for i in range(n) for j in range(n)], n)
            reg = generator.faire_grossir(n, graines, rng)
            nom = generator.noms(n)
            self.compare([" ".join(nom[x] for x in l) for l in reg])

    def test_grandes_grilles_plantees(self):
        for n, graine in ((20, 1), (30, 2), (40, 3)):
            g, _ = generator.generate(n, graine)
            self.assertTrue(meowdoku.is_valid(g, self.resout(g)))


class Interface(unittest.TestCase):
    def sat(self, texte, *options):
        chemin = ecrire(texte) if texte is not None else "/inexistant.cnf"
        try:
            r = subprocess.run([sys.executable, os.path.join(RACINE, "sat.py"), chemin, *options],
                               capture_output=True, text=True, cwd=tempfile.gettempdir())
        finally:
            if texte is not None:
                os.remove(chemin)
        return r.returncode, r.stdout, r.stderr

    SAT = "p cnf 3 2\n1 -2 0\n2 3 0\n"
    UNSAT = "p cnf 1 2\n1 0\n-1 0\n"

    def test_sorties_exactes(self):
        for mode in ("dpll", "optimized"):
            self.assertEqual(self.sat(self.SAT, "--mode", mode), (0, "s SATISFIABLE\n", ""))
            self.assertEqual(self.sat(self.UNSAT, "--mode", mode), (0, "s UNSATISFIABLE\n", ""))
            self.assertEqual(self.sat(self.UNSAT, "--mode", mode, "--output-model"),
                             (0, "s UNSATISFIABLE\n", ""))                   # pas de ligne v
        self.assertEqual(self.sat(self.SAT), (0, "s SATISFIABLE\n", ""))    # sans mode

    def test_modele(self):
        for mode in ("dpll", "optimized"):
            code, out, err = self.sat(self.SAT, "--output-model", "--mode=" + mode)
            l = out.split("\n")
            self.assertEqual((code, err, len(l), l[0], l[2]), (0, "", 3, "s SATISFIABLE", ""))
            self.assertTrue(l[1].startswith("v ") and l[1].endswith(" 0"))
            m = [int(x) for x in l[1].split()[1:-1]]
            self.assertTrue(modele_ok(3, [[1, -2], [2, 3]], m), m)

    def test_modele_avec_variables_libres_et_formule_vide(self):
        code, out, _ = self.sat("p cnf 5 1\n-4 0\n", "--output-model")
        m = [int(x) for x in out.split("\n")[1].split()[1:-1]]
        self.assertEqual([abs(x) for x in m], [1, 2, 3, 4, 5])
        self.assertIn(-4, m)
        self.assertEqual(self.sat("p cnf 0 0\n", "--output-model"), (0, "s SATISFIABLE\nv 0\n", ""))
        self.assertEqual(self.sat("p cnf 0 0\n", "--output-model", "--mode", "dpll"),
                         (0, "s SATISFIABLE\nv 0\n", ""))
        self.assertEqual(self.sat("p cnf 1 1\n0\n", "--output-model"), (0, "s UNSATISFIABLE\n", ""))

    def test_deux_modes_meme_statut(self):
        rng = random.Random(10)
        for _ in range(4):
            n = 12
            cl = [[rng.choice((-1, 1)) * v for v in rng.sample(range(1, n + 1), 3)] for _ in range(51)]
            texte = f"p cnf {n} {len(cl)}\n" + "".join(" ".join(map(str, c)) + " 0\n" for c in cl)
            s = {self.sat(texte, "--mode", m)[1] for m in ("dpll", "optimized")}
            self.assertEqual(len(s), 1)

    def test_erreurs_d_usage(self):
        for options in ((), ("--mode",), ("--mode", "rapide"), ("--mode=",), ("--inconnu",),
                        ("autre.cnf",)):
            code, out, err = self.sat(self.SAT, *options) if options != () else self.sat(None, "--bidon")
            self.assertEqual((code, out), (2, ""), options)
            self.assertIn("usage", err)
        code, out, _ = self.sat(None)                      # fichier inexistant
        self.assertNotEqual(code, 0)
        self.assertEqual(out, "")


if __name__ == "__main__":
    unittest.main()
