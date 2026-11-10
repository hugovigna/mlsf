"""Compilateur de modèles de contraintes vers SAT (ligne de commande).

    python csp.py modele.csp                    # FNC au format Dimacs sur la sortie standard
    python csp.py modele.csp --dimacs f.cnf     # FNC écrite dans f.cnf
    python csp.py modele.csp --solve            # résolution par le solveur de la partie I
    python csp.py modele.csp --ground           # affiche les contraintes après déroulage

Options : --amo pairwise|sinz   encodage de « au plus un » (défaut : pairwise)
          --solver optimized|dpll   solveur de la partie I (défaut : optimized)
          --stats               taille de la FNC et temps de chaque étape, sur la sortie d'erreur

Chaîne : texte -> AST (syntax.py) -> contraintes sans boucle (analyse.py)
         -> clauses (encode.py) -> solveur (partie1/) -> valeurs des variables du modèle.
Les erreurs de modèle et les avertissements sont écrits sur la sortie d'erreur.
"""
import argparse
import os
import sys
import time

import syntax
import analyse
import encode
import ground

# Le solveur DPLL de la partie I est utilisé tel quel, depuis le dossier voisin partie1/.
# append (et non insert 0) : en cas de nom de fichier commun, les fichiers de la partie II gagnent.
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "partie1"))


def solve(clauses, nvars, solver="optimized"):
    """Appelle le solveur de la partie I. Renvoie un modèle (liste de littéraux ±1..±nvars) ou None."""
    if solver == "dpll":
        from dpll import dpll                       # algorithme 2 de la partie I (lent mais fidèle)
        sat, valuation = dpll({frozenset(c) for c in clauses})
        if not sat:
            return None
        return [x if -x not in valuation else -x for x in range(1, nvars + 1)]
    from optimized import resoudre                  # DPLL accéléré de la partie I
    return resoudre(nvars, clauses)


def compile_text(text, amo="pairwise"):
    """Texte du modèle -> (modèle analysé, encodeur contenant la FNC). Lève CompileError."""
    model = analyse.compile_text(text)
    return model, encode.encode(model, amo)


def main(argv=None):
    p = argparse.ArgumentParser(description="Compilateur de contraintes vers SAT")
    p.add_argument("model")
    p.add_argument("--dimacs", metavar="FICHIER", help="écrit la FNC dans ce fichier")
    p.add_argument("--solve", action="store_true", help="résout avec le solveur de la partie I")
    p.add_argument("--ground", action="store_true", help="affiche les contraintes sans boucle")
    p.add_argument("--amo", choices=["pairwise", "sinz"], default="pairwise")
    p.add_argument("--solver", choices=["optimized", "dpll"], default="optimized")
    p.add_argument("--stats", action="store_true")
    args = p.parse_args(argv)

    try:
        with open(args.model) as f:
            text = f.read()
    except OSError as e:
        print(f"{args.model}: cannot read file ({e.strerror})", file=sys.stderr)
        return 2

    try:
        t0 = time.time()
        model = analyse.compile_text(text)
        t1 = time.time()
        enc = encode.encode(model, args.amo)
        t2 = time.time()
    except syntax.CompileError as e:
        print(e.format(args.model), file=sys.stderr)
        return 1

    for w in model.warnings:
        print(f"{args.model}: warning: {w}", file=sys.stderr)

    if args.ground:
        for c in model.constraints:
            print(ground.show(c))
        return 0

    if args.stats:
        print(f"cells={len(model.cells)} constraints={len(model.constraints)} "
              f"vars={enc.nvars} clauses={len(enc.clauses)} "
              f"analyse={t1 - t0:.2f}s encode={t2 - t1:.2f}s", file=sys.stderr)

    if args.solve:
        t3 = time.time()
        sat_model = solve(enc.clauses, enc.nvars, args.solver)
        if args.stats:
            print(f"solve={time.time() - t3:.2f}s", file=sys.stderr)
        if sat_model is None:
            print("s UNSATISFIABLE")
        else:
            print("s SATISFIABLE")
            for name, value in encode.decode(enc, model, sat_model):
                print(f"{name} = {value}")
        return 0

    dimacs = encode.to_dimacs(enc, model)
    if args.dimacs:
        with open(args.dimacs, "w") as f:
            f.write(dimacs)
    else:
        sys.stdout.write(dimacs)
    return 0


if __name__ == "__main__":
    sys.exit(main())
