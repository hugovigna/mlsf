"""Formules « sans boucle » : le résultat de l'analyse (Q3), l'entrée de la traduction (Q4).

Après analyse, une contrainte ne parle plus que de cases de variables (grid[1][2]) et de
valeurs connues. On la représente par une petite formule logique dont les feuilles sont :
  - True / False                : formule connue ;
  - Cell                        : une case de variable booléenne ;
  - Cmp(op, l, r)               : une comparaison entre deux « termes » (case ou entier connu) ;
  - Global(nom, args)           : une contrainte globale (allDifferent, atMostOne...) ;
  - Lit(n)                      : un littéral DIMACS (utilisé seulement par encode.py).
et dont les noeuds sont Not, And, Or (And et Or ont un nombre quelconque d'arguments).

Les formules sont des dataclasses « frozen » : on peut les comparer et s'en servir comme
clés de dictionnaire (utile pour partager les variables auxiliaires de Tseitin).

Les fonctions mk_not, mk_and, mk_or, mk_cmp sont des constructeurs « intelligents » : ils
simplifient au passage (constantes, doublons, négation poussée vers les feuilles). Ainsi
la négation n'est jamais appliquée qu'à une feuille : not (a and b) devient (not a) or (not b).
"""
from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Types, valeurs et cases
# ---------------------------------------------------------------------------
# Un type est "bool", "int" ou un objet Enum. Les valeurs d'un type énuméré sont les
# entiers 0, 1, ... dans l'ordre de déclaration (on peut donc les comparer avec < et <=).
@dataclass(frozen=True)
class Enum:
    name: str
    values: tuple     # noms des valeurs : values[k] est le nom de la valeur k


def type_name(t):
    return t if isinstance(t, str) else t.name


@dataclass(frozen=True)
class Val:
    """Valeur connue à la compilation : un entier ou une valeur énumérée (typ = son type)."""
    value: int
    typ: object


@dataclass(frozen=True)
class Cell:
    """Une case de variable, par exemple grid[1][2].
    typ : "bool", "int" ou Enum ; values : les valeurs possibles (vide pour un booléen)."""
    name: str
    typ: object
    values: tuple


@dataclass(frozen=True)
class Lit:
    n: int            # numéro DIMACS signé


# ---------------------------------------------------------------------------
# Noeuds des formules
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Not:
    f: object         # toujours une feuille : Cell booléenne ou Global


@dataclass(frozen=True)
class And:
    args: tuple


@dataclass(frozen=True)
class Or:
    args: tuple


@dataclass(frozen=True)
class Cmp:
    op: str           # "=", "!=", "<", "<=" seulement (> et >= sont renversés par mk_cmp)
    left: object      # Cell ou entier connu
    right: object


@dataclass(frozen=True)
class Global:
    name: str         # "atLeastOne", "atMostOne", "exactlyOne" ou "allDifferent"
    args: tuple       # allDifferent : Cell ou entier ; les autres : formules


# ---------------------------------------------------------------------------
# Constructeurs intelligents
# ---------------------------------------------------------------------------
def mk_not(f):
    if f is True:
        return False
    if f is False:
        return True
    if isinstance(f, Not):
        return f.f
    if isinstance(f, Lit):
        return Lit(-f.n)
    if isinstance(f, And):             # lois de De Morgan
        return mk_or([mk_not(a) for a in f.args])
    if isinstance(f, Or):
        return mk_and([mk_not(a) for a in f.args])
    if isinstance(f, Cmp):
        return negate_cmp(f)
    return Not(f)                      # Cell booléenne ou Global


def mk_and(args):
    flat = []
    for a in args:
        if a is False:
            return False               # un faux rend tout faux
        if a is True:
            continue                   # un vrai ne change rien
        for b in (a.args if isinstance(a, And) else (a,)):    # And(And(a,b),c) -> And(a,b,c)
            if b not in flat:
                flat.append(b)
    if not flat:
        return True
    return flat[0] if len(flat) == 1 else And(tuple(flat))


def mk_or(args):
    flat = []
    for a in args:
        if a is True:
            return True
        if a is False:
            continue
        for b in (a.args if isinstance(a, Or) else (a,)):
            if b not in flat:
                flat.append(b)
    if not flat:
        return False
    return flat[0] if len(flat) == 1 else Or(tuple(flat))


def mk_iff(a, b):
    """a <-> b, pour deux formules."""
    if a is True or a is False:
        return b if a else mk_not(b)
    if b is True or b is False:
        return a if b else mk_not(a)
    return mk_and([mk_or([mk_not(a), b]), mk_or([a, mk_not(b)])])


def holds(op, a, b):
    """Valeur de a op b pour deux entiers."""
    return {"=": a == b, "!=": a != b, "<": a < b, "<=": a <= b, ">": a > b, ">=": a >= b}[op]


def mk_cmp(op, left, right):
    """Comparaison de deux termes (Cell ou entier connu), normalisée :
    - > et >= sont réécrits avec < et <= (x > y devient y < x) ;
    - deux entiers connus donnent directement True ou False ;
    - pour = et !=, l'entier connu est à droite (2 = x devient x = 2)."""
    if op == ">":
        op, left, right = "<", right, left
    elif op == ">=":
        op, left, right = "<=", right, left
    if isinstance(left, int) and isinstance(right, int):
        return holds(op, left, right)
    if op in ("=", "!=") and isinstance(left, int):
        left, right = right, left
    return Cmp(op, left, right)


def negate_cmp(c):
    """La négation d'une comparaison est une comparaison : not (x < y) est y <= x."""
    if c.op == "=":
        return Cmp("!=", c.left, c.right)
    if c.op == "!=":
        return Cmp("=", c.left, c.right)
    if c.op == "<":
        return Cmp("<=", c.right, c.left)
    return Cmp("<", c.right, c.left)       # not (x <= y) est y < x


# ---------------------------------------------------------------------------
# Affichage (pour les tests et l'option --ground de csp.py)
# ---------------------------------------------------------------------------
def show(f):
    if f is True:
        return "true"
    if f is False:
        return "false"
    if isinstance(f, Cell):
        return f.name
    if isinstance(f, Lit):
        return str(f.n)
    if isinstance(f, Not):
        return "not " + show(f.f)
    if isinstance(f, And):
        return "(" + " and ".join(show(a) for a in f.args) + ")"
    if isinstance(f, Or):
        return "(" + " or ".join(show(a) for a in f.args) + ")"
    if isinstance(f, Cmp):
        return f"{_show_term(f.left, f.right)} {f.op} {_show_term(f.right, f.left)}"
    if isinstance(f, Global):
        args = [str(a) if isinstance(a, int) and not isinstance(a, bool) else show(a) for a in f.args]
        return f"{f.name}({', '.join(args)})"
    return str(f)


def _show_term(t, other):
    """Un entier comparé à une case énumérée s'affiche avec le nom de la valeur."""
    if isinstance(t, int) and isinstance(other, Cell) and isinstance(other.typ, Enum):
        return other.typ.values[t] if 0 <= t < len(other.typ.values) else str(t)
    return show(t) if not isinstance(t, int) else str(t)
