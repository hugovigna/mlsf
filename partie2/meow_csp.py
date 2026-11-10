"""Question 6 : Meowdoku écrit dans le langage de contraintes.

    python meow_csp.py grille.txt [--modele 1|2|2alo|general]     # 6.1 : écrit le modèle .csp

Ce fichier contient :
  - le convertisseur grille (format de la partie I) -> déclarations N, M, K, Zone, region (6.1) ;
  - les règles du jeu des différents modèles (modèle 1, modèle 2, modèle 2 + « au moins un chat
    par région », modèle général pour N, M, K quelconques) ;
  - un vérificateur INDÉPENDANT du compilateur (il ne regarde que la grille et les positions
    des chats), une recherche exhaustive pour les petites grilles et un générateur de grilles
    rectangulaires aléatoires (6.2, 6.5) ;
  - une fonction `resoudre` qui lance toute la chaîne (compilation + solveur de la partie I).
"""
import argparse
import itertools
import random
import re
import sys

import csp
import encode


# ---------------------------------------------------------------------------
# 6.1  Grille (format de la partie I) -> données du modèle
# ---------------------------------------------------------------------------
def lire_grille(texte):
    """Lit une grille au format de la partie I :
         c commentaire
         GRID N M
         ZONES A B C ...
         N lignes de M noms de région
    Renvoie (zones, grille) où grille[i][j] est le nom de la région de la case (i, j)."""
    lignes = [l.split() for l in texte.splitlines() if l.strip() and not l.startswith("c")]
    assert lignes[0][0] == "GRID" and lignes[1][0] == "ZONES", "format de grille inconnu"
    n, m = int(lignes[0][1]), int(lignes[0][2])
    zones = lignes[1][1:]
    grille = lignes[2:]
    assert len(grille) == n and all(len(l) == m for l in grille), "grille mal formée"
    return zones, grille


# Ces noms sont déjà pris dans nos modèles (constantes, tableaux, mots-clés du langage) : une
# région qui s'appellerait ainsi (le générateur de la partie I produit K, M, N dès 11 régions)
# serait refusée par le compilateur. On la renomme en ajoutant un « Z » devant.
NOMS_RESERVES = {"N", "M", "K", "Zone", "region", "row", "col", "cat",
                 "const", "enum", "var", "array", "forall", "in", "constraint", "for", "where",
                 "and", "or", "not", "true", "false", "bool", "abs",
                 "atLeastOne", "atMostOne", "exactlyOne", "allDifferent"}


def nom_csp(zone):
    return "Z" + zone if zone in NOMS_RESERVES else zone


def donnees(zones, grille):
    """Les déclarations qui changent d'une grille à l'autre (voir l'énoncé)."""
    n, m, k = len(grille), len(grille[0]), len(zones)
    lignes = [f"const N = {n};     // lignes",
              f"const M = {m};     // colonnes",
              f"const K = {k};     // régions",
              "enum Zone = { " + ", ".join(nom_csp(z) for z in zones) + " };",
              "const region[N][M] = ["]
    rangees = ["    [" + ", ".join(nom_csp(z) for z in ligne) + "]" for ligne in grille]
    lignes.append(",\n".join(rangees))
    lignes.append("];")
    return "\n".join(lignes) + "\n"


# ---------------------------------------------------------------------------
# Les règles du jeu : un texte par modèle, identique pour toutes les grilles
# ---------------------------------------------------------------------------
# Modèle 1 : on décrit la position du chat de chaque région (énoncé, mot pour mot).
MODELE_1 = """
array row[Zone] : 1..N;
array col[Zone] : 1..M;

// au plus un chat par ligne et par colonne
constraint allDifferent(row[*]);
constraint allDifferent(col[*]);

// le chat de la région z est dans la région z
forall z in Zone, i in 1..N, j in 1..M {
    constraint region[i][j] != z -> not (row[z] = i and col[z] = j);
}

// pas deux chats voisins (en diagonale : lignes et colonnes sont distinctes)
forall z1 in Zone, z2 in Zone, i in 1..N, j in 1..M,
       k in (i - 1)..(i + 1), l in (j - 1)..(j + 1) {
    constraint z1 < z2 and k != i and l != j
               -> not (row[z1] = i and col[z1] = j and row[z2] = k and col[z2] = l);
}
"""

# Modèle 2 : une variable booléenne par case (énoncé) ...
MODELE_2 = """
array cat[N][M] : bool;

// exactement un chat par ligne et par colonne (N = M = K)
forall i in 1..N { constraint exactlyOne(cat[i][*]); }
forall j in 1..M { constraint exactlyOne(cat[*][j]); }

// pas deux chats voisins (en diagonale : lignes et colonnes sont exclusives)
forall i in 1..(N - 1), j in 1..M, l in (j - 1)..(j + 1) {
    constraint l >= 1 and l <= M and l != j -> not (cat[i][j] and cat[i + 1][l]);
}
"""

# ... complété par « au plus un chat par région » (6.2). Aucune tranche ne désigne les cases
# d'une région, on interdit donc les paires de cases de la même région, une fois chacune : la
# case (i, j) doit venir avant la case (k, l) dans l'ordre de lecture.
AU_PLUS_UN_PAR_REGION = """
// au plus un chat par région : pas deux chats dans deux cases distinctes d'une même région
forall i in 1..N, j in 1..M, k in i..N, l in 1..M {
    constraint (k > i or l > j) and region[i][j] = region[k][l]
               -> not (cat[i][j] and cat[k][l]);
}
"""

# 6.4 : « au moins un chat par région » (redondant quand N = M = K). Une liste en compréhension
# désigne les cases de la région z. C'est une extension du langage (question optionnelle de
# l'énoncé) : sans elle, il faudrait introduire des variables auxiliaires pour écrire une grande
# disjonction.
AU_MOINS_UN_PAR_REGION = """
// (redondant) au moins un chat par région
forall z in Zone {
    constraint atLeastOne(cat[i][j] for i in 1..N, j in 1..M where region[i][j] = z);
}
"""

# 6.5 : grilles quelconques. Il n'y a plus autant de lignes ou de colonnes que de régions :
# « au plus un » par ligne et par colonne, et « exactement un » par région (c'est la règle
# fondamentale ; les autres en découlent quand N = M = K).
MODELE_GENERAL = """
array cat[N][M] : bool;

// au plus un chat par ligne et par colonne
forall i in 1..N { constraint atMostOne(cat[i][*]); }
forall j in 1..M { constraint atMostOne(cat[*][j]); }

// pas deux chats voisins (en diagonale : lignes et colonnes sont exclusives)
forall i in 1..(N - 1), j in 1..M, l in (j - 1)..(j + 1) {
    constraint l >= 1 and l <= M and l != j -> not (cat[i][j] and cat[i + 1][l]);
}

// exactement un chat par région
forall z in Zone {
    constraint exactlyOne(cat[i][j] for i in 1..N, j in 1..M where region[i][j] = z);
}
"""

MODELES = {
    "1": MODELE_1,
    "2": MODELE_2 + AU_PLUS_UN_PAR_REGION,
    "2alo": MODELE_2 + AU_PLUS_UN_PAR_REGION + AU_MOINS_UN_PAR_REGION,
    "general": MODELE_GENERAL,
}


def modele(texte_grille, nom):
    """Modèle complet (données + règles) pour une grille donnée."""
    zones, grille = lire_grille(texte_grille)
    return donnees(zones, grille) + MODELES[nom]


# ---------------------------------------------------------------------------
# Résolution et lecture de la solution
# ---------------------------------------------------------------------------
def resoudre(texte_modele, amo="pairwise", solver="optimized"):
    """Compile le modèle et le résout. Renvoie la liste des valeurs (nom, valeur) ou None."""
    model, enc = csp.compile_text(texte_modele, amo)
    sat_model = csp.solve(enc.clauses, enc.nvars, solver)
    if sat_model is None:
        return None
    return encode.decode(enc, model, sat_model)


def chats_depuis_solution(valeurs, zones):
    """Positions (i, j), en comptant depuis 1, des chats d'après les valeurs du modèle.
    Reconnaît les deux formes : cat[i][j] = true (modèles 2) ou row[z], col[z] (modèle 1)."""
    chats, lig, col = [], {}, {}
    for nom, v in valeurs:
        m = re.fullmatch(r"cat\[(\d+)\]\[(\d+)\]", nom)
        if m and str(v) == "true":
            chats.append((int(m.group(1)), int(m.group(2))))
        m = re.fullmatch(r"(row|col)\[(\w+)\]", nom)
        if m:
            (lig if m.group(1) == "row" else col)[m.group(2)] = int(v)
    for z in lig:
        chats.append((lig[z], col[z]))
    return sorted(chats)


# ---------------------------------------------------------------------------
# Vérificateur indépendant : il ne connaît ni le langage ni le compilateur
# ---------------------------------------------------------------------------
def est_valide(grille, chats):
    """Règles du jeu, écrites directement. `chats` : positions (i, j) comptées depuis 1."""
    regions = {z for ligne in grille for z in ligne}
    if len(set(chats)) != len(chats):
        return False
    # un chat par région, exactement
    comptes = {z: 0 for z in regions}
    for i, j in chats:
        comptes[grille[i - 1][j - 1]] += 1
    if any(c != 1 for c in comptes.values()):
        return False
    # au plus un chat par ligne et par colonne
    if len({i for i, j in chats}) != len(chats) or len({j for i, j in chats}) != len(chats):
        return False
    # pas deux chats sur des cases voisines (8 voisins)
    for (i1, j1), (i2, j2) in itertools.combinations(chats, 2):
        if abs(i1 - i2) <= 1 and abs(j1 - j2) <= 1:
            return False
    return True


def recherche_exhaustive(grille):
    """Toutes les solutions de la grille : un chat par région, on essaie toutes les
    combinaisons de cases. Réservé aux petites grilles."""
    regions = sorted({z for ligne in grille for z in ligne})
    cases = {z: [(i + 1, j + 1) for i, ligne in enumerate(grille)
                 for j, x in enumerate(ligne) if x == z] for z in regions}
    return [sorted(c) for c in itertools.product(*(cases[z] for z in regions))
            if est_valide(grille, list(c))]


# ---------------------------------------------------------------------------
# Générateur de grilles rectangulaires (le générateur de la partie I ne fait que des carrés)
# ---------------------------------------------------------------------------
def grille_aleatoire(n, m, k, rng):
    """Grille n x m découpée en k régions connexes : k graines au hasard, puis chaque case
    libre voisine d'une région est donnée à cette région, tirage au hasard à chaque pas."""
    assert 1 <= k <= n * m
    zones = [chr(65 + z % 26) + (str(z // 26) if z >= 26 else "") for z in range(k)]
    grille = [[None] * m for _ in range(n)]
    cases = [(i, j) for i in range(n) for j in range(m)]
    for z, (i, j) in zip(zones, rng.sample(cases, k)):
        grille[i][j] = z
    while True:
        # cases libres qui touchent (4 voisins) une case déjà colorée
        bord = [(i, j, grille[a][b])
                for i, j in cases if grille[i][j] is None
                for a, b in ((i - 1, j), (i + 1, j), (i, j - 1), (i, j + 1))
                if 0 <= a < n and 0 <= b < m and grille[a][b] is not None]
        if not bord:
            return zones, grille
        i, j, z = rng.choice(bord)
        grille[i][j] = z


def texte_grille(zones, grille):
    """Écrit une grille au format de la partie I."""
    return (f"GRID {len(grille)} {len(grille[0])}\nZONES {' '.join(zones)}\n"
            + "\n".join(" ".join(ligne) for ligne in grille) + "\n")


# ---------------------------------------------------------------------------
def main(argv=None):
    p = argparse.ArgumentParser(description="Convertit une grille Meowdoku en modèle .csp")
    p.add_argument("grille")
    p.add_argument("--modele", choices=sorted(MODELES), default="2alo")
    args = p.parse_args(argv)
    with open(args.grille) as f:
        sys.stdout.write(modele(f.read(), args.modele))


if __name__ == "__main__":
    main()
