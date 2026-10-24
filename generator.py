"""Génération d'une grille Meowdoku n x n avec solution plantée.

1. On place n chats (un par ligne et par colonne, jamais collés).
2. Chaque chat est la graine d'une région, qu'on fait grossir case par case.
"""
import random
import sys


def noms(n):
    """A, B, ..., Z, A1, B1, ..."""
    return [chr(65 + k % 26) + (str(k // 26) if k >= 26 else "") for k in range(n)]


def place_chats(n, rng):
    """Choisit une colonne par ligne (colonnes toutes différentes, écart >= 2 entre lignes
    consécutives) par backtracking aléatoire. Renvoie la liste des colonnes, ou None."""
    colonnes = []

    def essayer(i):
        if i == n:
            return True
        choix = list(range(n))
        rng.shuffle(choix)
        for c in choix:
        # si colonne jamais utilisée et (soit c'est le premier chat soit on est bien pas collé en diag)
            if c not in colonnes and (i == 0 or abs(c - colonnes[-1]) >= 2): # comme on choisit une colonne par ligne dans l'ordre, pour vérifier si la clause diag est ok il suffit de regarder la colonne choisie pour la ligne juste avant 
                colonnes.append(c)
                if essayer(i + 1): # backtraking
                    return True
                colonnes.pop() # sinon on abandonne cette branche 
        return False

    return colonnes if essayer(0) else None


def faire_grossir(n, chats, rng):
    """Chaque chat (i, j) est la graine de la région i. Tant qu'il reste des cases libres,
    on tire au hasard une case libre voisine d'une région et on l'y ajoute."""
    region = [[None] * n for _ in range(n)]
    for k, (i, j) in enumerate(chats):
        region[i][j] = k
    while True:
        candidats = []  # (case libre, région voisine)
        for i in range(n):
            for j in range(n):
                if region[i][j] is None:
                    for a, b in ((i - 1, j), (i + 1, j), (i, j - 1), (i, j + 1)): # pas le 8-voisinage pour garder la connexité spéciale là sans diag
                        if 0 <= a < n and 0 <= b < n and region[a][b] is not None: # si une case 4-voisine est dans une région, on peut attribuer cette case libre à cette région
                            candidats.append(((i, j), region[a][b])) 
        if not candidats:
            return region
        (i, j), k = rng.choice(candidats)
        region[i][j] = k


def generate(n, seed=None):
    """Renvoie (grille, chats). Impossible pour n = 2 et 3 (ValueError)."""
    rng = random.Random(seed)
    colonnes = place_chats(n, rng)
    if colonnes is None:
        raise ValueError(f"aucune grille pour n={n}")
    chats = list(enumerate(colonnes))
    nom = noms(n)
    grille = [[nom[k] for k in ligne] for ligne in faire_grossir(n, chats, rng)]
    return grille, chats


def write_grid(path, grille):
    n = len(grille)
    with open(path, "w") as f:
        f.write(f"GRID {n} {n}\nZONES {' '.join(noms(n))}\n")
        for ligne in grille:
            f.write(" ".join(ligne) + "\n")


if __name__ == "__main__":
    if len(sys.argv) not in (3, 4):
        sys.exit("usage: python generator.py N sortie.txt [graine]")
    graine = int(sys.argv[3]) if len(sys.argv) == 4 else None
    grille, _ = generate(int(sys.argv[1]), graine)
    write_grid(sys.argv[2], grille)
