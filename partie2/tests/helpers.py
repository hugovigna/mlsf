"""Outils communs aux tests : énumération des solutions d'une FNC, comparaison avec l'oracle."""
import os
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)
import csp                      # ajoute aussi partie1/ au chemin de recherche
from csp import solve


def cell_value(enc, cell, true_vars):
    """Valeur (entier ou booléen Python) d'une case dans un modèle de la FNC."""
    if cell.typ == "bool":
        return enc.lit_of[(cell.name, None)] in true_vars
    return next(v for v in cell.values if enc.lit_of[(cell.name, v)] in true_vars)


def sat_solutions(text, amo="pairwise", limit=100000):
    """Toutes les valuations des cases qui satisfont le modèle, d'après la FNC : on résout,
    on note la valuation, on ajoute une clause qui l'interdit, et on recommence jusqu'à UNSAT."""
    model, enc = csp.compile_text(text, amo)
    clauses = [list(c) for c in enc.clauses]
    found = []
    while len(found) < limit:
        m = solve(clauses, enc.nvars)
        if m is None:
            return found
        true_vars = {l for l in m if l > 0}
        found.append({c.name: cell_value(enc, c, true_vars) for c in model.cells})
        # clause de blocage sur les variables des cases uniquement (pas les auxiliaires)
        named = [n for (name, v), n in enc.lit_of.items()]
        clauses.append([-n if n in true_vars else n for n in named])
    raise AssertionError("trop de solutions")


def as_set(solutions):
    return {frozenset(s.items()) for s in solutions}
