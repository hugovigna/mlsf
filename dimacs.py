"""Lecture d'un fichier DIMACS CNF.

Formule : set de clauses ; clause : frozenset d'entiers non nuls (k = x_k, -k = ¬x_k).
Le 0 de fin de clause n'est pas stocké ; la clause vide est frozenset().
"""


def parse_dimacs(path):
    """Renvoie (nb_vars, formule)."""
    nb_vars = 0
    formule = set()
    courant = []
    with open(path) as f:
        for ligne in f:
            mots = ligne.split()
            if not mots or mots[0] == "c": # skip les lignes de commentaires
                continue
            if mots[0] == "%":                      # fin de fichier style SATLIB
                break
            if mots[0] == "p":                      # ligne avec les infos du type "p cnf <nb_vars> <nb_clauses>""
                nb_vars = int(mots[2])
                continue
            courant.extend(int(m) for m in mots)  # une clause peut s'étendre sur plusieurs lignes
            while 0 in courant:                     # chaque 0 ferme une clause
                i = courant.index(0)
                formule.add(frozenset(courant[:i])) # on ne stocke pas le 0 de fin
                courant = courant[i + 1:]
    assert not courant, f"clause non terminée par 0 : {courant!r}"
    return nb_vars, formule