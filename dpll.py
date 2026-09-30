"""DPLL, algorithmes 1 et 2 du sujet.

Formule : set de frozenset d'entiers signés (voir dimacs.py). Valuation : set de littéraux
rendus vrais (p <- 1 donne p, p <- 0 donne -p) ; les variables absentes sont libres.
`choix(F)` renvoie le littéral à rendre vrai lors d'une décision (ligne 9 / 17).
"""
import random
import sys

sys.setrecursionlimit(100000)


def simplifier(F, l):
    """F[l <- 1] : retire les clauses contenant l, retire -l des autres."""
    return {c - {-l} if -l in c else c for c in F if l not in c}


def choix_aleatoire(F, rng=random):
    """H0 : variable de F et valeur de vérité tirées au hasard."""
    p = rng.choice(list(variables(F)))
    return p if rng.random() < 0.5 else -p


def variables(F):
    return {abs(l) for c in F for l in c}


def trouver_unitaire(F):
    for c in F:
        if len(c) == 1:
            return list(c)[0] # on prend l'élément de la clause
    return None


def trouver_pur(F):
    lits = {l for c in F for l in c}
    for l in lits:
        if -l not in lits: # apparaît que sous une polarité
            return l
    return None


def dpll_sat(F, choix=choix_aleatoire):
    """Algorithme 1 : True si F est satisfiable."""
    if frozenset() in F:
        return False # clause vide donc pas sat
    if not F:
        return True # formule vide donc tout est satisfiable
    l = trouver_unitaire(F)
    if l is None:
        l = trouver_pur(F)
    if l is not None:
        return dpll_sat(simplifier(F, l), choix)
    l = choix(F)
    return dpll_sat(simplifier(F, l), choix) or dpll_sat(simplifier(F, -l), choix)


def dpll(F, choix=choix_aleatoire, stats=None):
    """Algorithme 2/3 : (True, valuation) si F est satisfiable, (False, None) sinon.
    `stats` (Counter facultatif) compte : unitaires, purs, decisions, retours (autres branches explorees)."""
    if frozenset() in F:
        return False, None
    if not F:
        return True, set()
    l = trouver_unitaire(F)
    if l is not None:
        if stats is not None:
            stats["unitaires"] += 1
    else:
        l = trouver_pur(F)
        if l is not None and stats is not None:
            stats["purs"] += 1
    if l is not None:
        s, v = dpll(simplifier(F, l), choix, stats)
        return (True, v | {l}) if s else (False, None) # v | {l} c'est l'union de la valuation avec l'affectation de l
    l = choix(F)
    if stats is not None:
        stats["decisions"] += 1
    s, v = dpll(simplifier(F, l), choix, stats)
    if s:
        return True, v | {l}
    if stats is not None:
        stats["retours"] += 1
    s, v = dpll(simplifier(F, -l), choix, stats)
    return (True, v | {-l}) if s else (False, None)
