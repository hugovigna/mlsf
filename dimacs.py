"""Lecture d'un fichier DIMACS CNF.

Formule : set de clauses ; clause : frozenset d'entiers non nuls (k = x_k, -k = ¬x_k).
Le 0 de fin de clause n'est pas stocké ; la clause vide est frozenset().
"""


def parse_dimacs(path):
    """Renvoie (nb_vars, formule)."""
    nb_vars = 0
    formule = set()
    with open(path) as f:
        for ligne in f:
            mots = ligne.split()
            if not mots or mots[0] == "c":
                continue
            if mots[0] == "%":                      # fin de fichier style SATLIB
                break
            if mots[0] == "p":                      # p cnf <nb_vars> <nb_clauses>
                nb_vars = int(mots[2])
                continue
            lits = [int(m) for m in mots]
            assert lits[-1] == 0, f"clause non terminée par 0 : {ligne!r}"
            formule.add(frozenset(lits[:-1]))
    return nb_vars, formule
