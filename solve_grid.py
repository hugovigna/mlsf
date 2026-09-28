"""Q3 : résout une grille Meowdoku via CNF + DPLL.

python solve_grid.py grille.txt [sortie.txt]
Sortie : recopie de la grille, puis "région ligne colonne" (indices depuis 1), puis la grille avec *.
"""
import os
import sys
import tempfile

import dpll
import meowdoku
from dimacs import parse_dimacs


def resoudre(grille):
    """Renvoie la liste des chats (i, j) ou None si la grille n'a pas de solution."""
    n = len(grille)
    with tempfile.TemporaryDirectory() as d:
        chemin = os.path.join(d, "grille.cnf")
        meowdoku.write_dimacs(chemin, n * n, meowdoku.encode(grille))
        _, F = parse_dimacs(chemin)
    sat, v = dpll.dpll(F)
    if not sat:
        return None
    chats = [((x - 1) // n, (x - 1) % n) for x in v if x > 0]
    assert meowdoku.is_valid(grille, chats), "solution invalide"
    return chats


def main():
    if len(sys.argv) not in (2, 3):
        sys.exit(__doc__)
    with open(sys.argv[1]) as f:
        texte = f.read()
    grille = meowdoku.parse_grid(sys.argv[1])
    zones = next(l.split()[1:] for l in texte.splitlines() if l.startswith("ZONES"))
    chats = resoudre(grille)
    if chats is None:
        sys.exit("grille sans solution")
    n = len(grille)
    out = texte.rstrip("\n") + "\n"
    for z in zones:
        i, j = next((i, j) for i, j in chats if grille[i][j] == z)
        out += f"{z} {i + 1} {j + 1}\n"
    for i in range(n):
        out += " ".join("*" if (i, j) in chats else "." for j in range(n)) + "\n"
    if len(sys.argv) == 3:
        open(sys.argv[2], "w").write(out)
    else:
        print(out, end="")


if __name__ == "__main__":
    main()
