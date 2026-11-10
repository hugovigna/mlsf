"""Meowdoku -> CNF.

Une grille est une liste de lignes ; grille[i][j] est le nom de la région de la case (i, j).
Les indices i, j commencent à 0. Une position de chat est un couple (i, j).
"""
import sys


def parse_grid(path):
    """Lit un fichier grille (format du sujet) et renvoie la grille."""
    with open(path) as f:
        lignes = [l.split() for l in f if l.strip() and not l.startswith("c")]
    # lignes[0] = GRID N M, lignes[1] = ZONES ..., ensuite les N lignes de la grille
    return lignes[2:]


def var(i, j, n):
    """Numéro DIMACS de la variable x_{i,j} : 1 si un chat est en (i, j)."""
    return i * n + j + 1


def en_conflit(grille, a, b):
    """Vrai si deux chats en a et b violent une règle."""
    (i1, j1), (i2, j2) = a, b
    return (i1 == i2                                  # même ligne
            or j1 == j2                               # même colonne
            or grille[i1][j1] == grille[i2][j2]       # même région
            or (abs(i1 - i2) <= 1 and abs(j1 - j2) <= 1))  # cases collées (8-voisinage)


def encode(grille):
    """Renvoie la liste des clauses (listes d'entiers DIMACS)."""
    n = len(grille)
    cases = [(i, j) for i in range(n) for j in range(n)]
    clauses = []

    # 1. Deux cases en conflit n'ont pas chacune un chat : (¬x_a ∨ ¬x_b)
    for k, a in enumerate(cases):
        for b in cases[k + 1:]: # pour éviter de mettre deux fois la même clause 
            if en_conflit(grille, a, b):
                clauses.append([-var(*a, n), -var(*b, n)]) # *a=i,j (déplie le couple)

    # 2. Chaque région a au moins un chat : (x_a ∨ x_b ∨ ...)
    for nom in dict.fromkeys(nom for ligne in grille for nom in ligne):   # ordre de 1re apparition
        clauses.append([var(i, j, n) for i, j in cases if grille[i][j] == nom])

    return clauses


def write_dimacs(path, nb_vars, clauses):
    with open(path, "w") as f:
        f.write(f"p cnf {nb_vars} {len(clauses)}\n")
        for c in clauses:
            f.write(" ".join(map(str, c)) + " 0\n")


def is_valid(grille, chats):
    """Vérifie directement les règles du jeu (indépendant de l'encodage CNF)."""
    n = len(grille)
    if len(set(chats)) != n:
        return False
    lignes = sorted(i for i, j in chats)
    colonnes = sorted(j for i, j in chats)
    regions = sorted(grille[i][j] for i, j in chats)
    if lignes != list(range(n)) or colonnes != list(range(n)):
        return False                                  # un chat par ligne et par colonne
    if regions != sorted({nom for ligne in grille for nom in ligne}):
        return False                                  # un chat par région
    chats = sorted(chats)                             # trié par ligne
    return all(abs(chats[k][1] - chats[k + 1][1]) >= 2 for k in range(n - 1))  # pas de diagonale collée


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("usage: python meowdoku.py grille.txt sortie.cnf")
    grille = parse_grid(sys.argv[1])
    n = len(grille)
    write_dimacs(sys.argv[2], n * n, encode(grille))
