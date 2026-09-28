"""Heuristiques de branchement. Une heuristique est une fonction choix(F) -> littéral à rendre vrai
(p si p <- 1, -p si p <- 0). `creer(nom, F0, seed)` la construit ; F0 = formule initiale (versions statiques).

H0  aléatoire                          H1  première variable libre, valeur 1
H2d variable la plus fréquente, polarité majoritaire (H2s : statique, calculée sur F0)
H3d littéral le plus fréquent
H4d MOMS : variable la plus fréquente dans les clauses de taille minimale, polarité majoritaire
H7d Jeroslow-Wang par littéral (H7s : statique)
H8  (perso) plus courte clause purement positive, variable la plus fréquente, valeur 1
Égalités : plus petite variable, puis polarité positive.
"""
import random
from collections import Counter, defaultdict

from dpll import variables


def _occ(F):
    return Counter(l for c in F for l in c)


def score_h2(F):
    occ = _occ(F)
    return {l: (occ[l] + occ[-l], occ[l]) for l in occ}


def score_h3(F):
    return {l: (n,) for l, n in _occ(F).items()}


def score_h4(F):
    k = min(len(c) for c in F)
    occ = _occ([c for c in F if len(c) == k])
    return {l: (occ[l] + occ[-l], occ[l]) for l in occ}


def score_h7(F):
    poids = defaultdict(float)
    for c in F:
        for l in c:
            poids[l] += 2.0 ** -len(c)
    return {l: (w,) for l, w in poids.items()}


def _cle(sc):
    return lambda l: (sc[l], -abs(l), l > 0)


def dynamique(score):
    def choix(F):
        sc = score(F)
        return max(sc, key=_cle(sc))
    return choix


def statique(score, F0):
    sc = score(F0)
    ordre = sorted(sc, key=_cle(sc), reverse=True)

    def choix(F):
        vs = variables(F)
        return next(l for l in ordre if abs(l) in vs)
    return choix


def h1(F):
    return min(variables(F))


def h8(F):
    positives = [c for c in F if all(l > 0 for l in c)]
    if not positives:
        return dynamique(score_h7)(F)
    k = min(len(c) for c in positives)
    occ = _occ(F)
    candidats = {p for c in positives if len(c) == k for p in c}
    return max(candidats, key=lambda p: (occ[p] + occ[-p], -p))


def creer(nom, F0, seed=0):
    if nom == "H0":
        rng = random.Random(seed)
        return lambda F: rng.choice(list(variables(F))) * rng.choice((1, -1))
    dyn = {"H2d": score_h2, "H3d": score_h3, "H4d": score_h4, "H7d": score_h7}
    sta = {"H2s": score_h2, "H7s": score_h7}
    if nom == "H1":
        return h1
    if nom == "H8":
        return h8
    if nom in dyn:
        return dynamique(dyn[nom])
    if nom in sta:
        return statique(sta[nom], F0)
    raise ValueError(nom)


NOMS = ["H0", "H1", "H2s", "H2d", "H3d", "H4d", "H7s", "H7d", "H8"]
