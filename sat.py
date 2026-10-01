"""Point d'entrée imposé (Q6).

    python sat.py instance.cnf [--mode dpll|optimized] [--output-model]

--mode dpll      : DPLL de la Q2 (dpll.py, algorithme 2, choix aléatoire H0).
--mode optimized : solveur CDCL (optimized.py). C'est le mode par défaut.
--output-model   : si SAT, affiche aussi le modèle « v l1 l2 ... ln 0 ».

Sortie standard réservée au résultat : « s SATISFIABLE » ou « s UNSATISFIABLE », puis la
ligne v éventuelle. Le modèle donne une valeur à chaque variable 1..n, n étant le maximum
entre l'en-tête et la plus grande variable rencontrée ; une variable libre est mise à vrai.
Les deux modes lisent le fichier avec le même lecteur (optimized.lire), plus tolérant que
dimacs.parse_dimacs (clause sur plusieurs lignes, dernier 0 manquant...).
Erreur d'usage : message sur stderr et code de retour 2, rien sur stdout.
"""
import sys

USAGE = "usage: python sat.py instance.cnf [--mode dpll|optimized] [--output-model]"


def analyser_arguments(args):
    """Renvoie (chemin, mode, sortie_modele) ; quitte avec le code 2 si invalide."""
    mode = "optimized"
    sortie_modele = False
    chemin = None
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--mode" and i + 1 < len(args):
            mode = args[i + 1]
            i += 1
        elif a.startswith("--mode="):
            mode = a[len("--mode="):]
        elif a == "--output-model":
            sortie_modele = True
        elif a.startswith("-") or chemin is not None:
            chemin = None                   # option inconnue ou deux fichiers
            break
        else:
            chemin = a
        i += 1
    if chemin is None or mode not in ("dpll", "optimized"):
        sys.stderr.write(USAGE + "\n")
        sys.exit(2)
    return chemin, mode, sortie_modele


def main():
    chemin, mode, sortie_modele = analyser_arguments(sys.argv[1:])
    # Import paresseux : on ne charge que le module du mode demandé (temps de démarrage).
    from optimized import lire
    n, clauses = lire(chemin)

    if mode == "dpll":
        from dpll import dpll
        F = {frozenset(c) for c in clauses}           # structure de la Q2
        sat, v = dpll(F)                               # v : littéraux rendus vrais
        modele = [x if -x not in v else -x for x in range(1, n + 1)] if sat else None
    else:
        from optimized import resoudre
        modele = resoudre(n, clauses)

    if modele is None:
        sys.stdout.write("s UNSATISFIABLE\n")
    elif sortie_modele:
        sys.stdout.write("s SATISFIABLE\nv " + " ".join(map(str, modele + [0])) + "\n")
    else:
        sys.stdout.write("s SATISFIABLE\n")


if __name__ == "__main__":
    main()
