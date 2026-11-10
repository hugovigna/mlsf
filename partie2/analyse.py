"""Analyse et transformation de l'arbre (Q3).

Entrée  : l'AST produit par syntax.parse.
Sortie  : un Model = la liste des cases de variables + une liste de contraintes sans boucle
          (formules de ground.py) qui ne portent plus que sur ces cases.

Choix de conception : UNE SEULE passe, qui parcourt l'arbre en gardant une table des
symboles et qui évalue partiellement chaque expression. « Évaluer partiellement » veut dire :
  - ce qui est connu à la compilation (constantes, indices de boucle, arithmétique, cases
    de tableaux constants, comparaisons entre valeurs connues) est calculé tout de suite ;
  - ce qui dépend d'une variable reste une formule.
Cette passe fait donc en même temps :
  1. l'analyse : noms déclarés, types, valeurs connues, indices dans les bornes ;
  2. le déroulage des forall (on exécute le corps pour chaque valeur de l'indice) ;
  3. le calcul des valeurs connues et la simplification des connecteurs ;
  4. le remplacement des tranches par la liste des cases.
Une passe par étape serait plus modulaire mais obligerait à refaire trois fois le même
parcours, et le court-circuit demandé par l'énoncé (« i < N -> grid[i+1][1] != ... » ne doit
pas évaluer grid[N+1][1]) est naturel dans une évaluation, pas dans une transformation d'arbre.

Conséquence assumée : une sous-expression qui n'est jamais évaluée (à cause d'un court-circuit)
n'est pas vérifiée non plus. Un modèle peut donc contenir une erreur de type cachée derrière
une condition toujours fausse ; c'est le comportement d'un langage évalué paresseusement.
"""
from dataclasses import dataclass
from itertools import product

import syntax as ast
import ground as g
from ground import Val, Cell, Enum, type_name
from syntax import CompileError


# ---------------------------------------------------------------------------
# Table des symboles
# ---------------------------------------------------------------------------
# Un seul dictionnaire nom -> symbole (« tous les noms partagent un même espace de noms »).
# Un symbole est l'un de :
#   Val    : constante entière, valeur d'un type énuméré, ou indice de boucle en cours ;
#   Cell   : variable (var x : ...) ;
#   Enum   : type énuméré ;
#   Array  : tableau de variables ou tableau constant.
@dataclass
class Dim:
    """Une dimension d'un tableau : soit une taille n (indices 1..n), soit un type énuméré
    (indices = les valeurs du type, numérotées 0..k-1)."""
    enum: Enum        # None pour une taille
    size: int

    def keys(self):
        return range(self.size) if self.enum else range(1, self.size + 1)

    def label(self, key):
        return self.enum.values[key] if self.enum else str(key)

    def describe(self):
        return f"enum {self.enum.name}" if self.enum else f"1..{self.size}"


@dataclass
class Array:
    name: str
    dims: list        # liste de Dim
    items: dict       # tuple d'indices -> Cell (tableau de variables) ou Val (tableau constant)


@dataclass
class Model:
    """Résultat de l'analyse."""
    cells: list       # toutes les cases de variables, dans l'ordre de déclaration
    constraints: list # formules sans boucle (ground.py) ; False = contrainte toujours fausse
    warnings: list    # messages d'avertissement
    enums: list


GLOBAL_BOOL = ("atLeastOne", "atMostOne", "exactlyOne")   # arguments booléens
GLOBALS = GLOBAL_BOOL + ("allDifferent",)


def type_of(r):
    """Type du résultat d'une évaluation : Val et Cell portent leur type, tout le reste
    (True, False, formules) est booléen."""
    if isinstance(r, (Val, Cell)):
        return r.typ
    return "bool"


class Compiler:
    def __init__(self):
        self.symbols = {}
        self.cells = []
        self.enums = []
        self.constraints = []
        self.warnings = []
        self.false_positions = set()   # pour n'avertir qu'une fois par contrainte du texte

    # ---------- outils ----------
    def error(self, message, node):
        raise CompileError(message, node.pos)

    def declare(self, name, symbol, node):
        if name in self.symbols:
            self.error(f"name '{name}' is already declared", node)
        self.symbols[name] = symbol

    def lookup(self, name, node):
        if name not in self.symbols:
            self.error(f"undeclared name '{name}'", node)
        return self.symbols[name]

    def known_int(self, e, what):
        """Évalue e, qui doit être un entier connu à la compilation ; renvoie un int Python."""
        r = self.eval(e)
        if not isinstance(r, Val):
            self.error(f"{what} must be a known value (constants and loop indices only), "
                       f"not a variable", e)
        if r.typ != "int":
            self.error(f"{what} must be an integer, not a {type_name(r.typ)}", e)
        return r.value

    def eval_bool(self, e, what):
        """Évalue e, qui doit être booléenne."""
        r = self.eval(e)
        if type_of(r) != "bool":
            self.error(f"{what} expects a boolean, got {type_name(type_of(r))}", e)
        return r

    # ---------- programme ----------
    def compile(self, program):
        for item in program.items:
            self.execute(item)
        return Model(self.cells, self.constraints, self.warnings, self.enums)

    def execute(self, item):
        if isinstance(item, ast.ConstDecl):
            self.do_const(item)
        elif isinstance(item, ast.EnumDecl):
            self.do_enum(item)
        elif isinstance(item, ast.VarDecl):
            self.do_var(item)
        elif isinstance(item, ast.ArrayDecl):
            self.do_array(item)
        elif isinstance(item, ast.Constraint):
            self.do_constraint(item)
        elif isinstance(item, ast.Forall):
            # Déroulage : le corps est exécuté une fois par valeur des indices.
            self.iterate(item.bindings, lambda: [self.execute(s) for s in item.body])

    # ---------- déclarations ----------
    def do_const(self, d):
        sizes = [self.known_int(e, f"size of '{d.name}'") for e in d.dims]
        if not sizes:
            if isinstance(d.init, ast.ListLit):
                self.error(f"'{d.name}' has no dimension, it cannot be given a list", d)
            value = self.eval(d.init)
            if not isinstance(value, Val):
                self.error(f"constant '{d.name}' must be a known integer or enum value", d.init)
            self.declare(d.name, value, d)
            return
        if not isinstance(d.init, ast.ListLit):
            self.error(f"'{d.name}' is an array, its value must be a list [...]", d.init)
        items = {}
        self.fill_const(d.name, d.init, sizes, (), items)
        if len({v.typ for v in items.values()}) > 1:
            self.error(f"all the values of '{d.name}' must have the same type", d)
        self.declare(d.name, Array(d.name, [Dim(None, s) for s in sizes], items), d)

    def fill_const(self, name, lit, sizes, prefix, items):
        """Range dans items les valeurs de la liste lit (de forme sizes), indices à partir de 1."""
        if not isinstance(lit, ast.ListLit):
            self.error(f"'{name}': a list is expected here", lit)
        if len(lit.items) != sizes[0]:
            self.error(f"'{name}': {len(lit.items)} values given, {sizes[0]} expected", lit)
        for k, sub in enumerate(lit.items, start=1):
            if len(sizes) > 1:
                self.fill_const(name, sub, sizes[1:], prefix + (k,), items)
            else:
                v = self.eval(sub)
                if not isinstance(v, Val):
                    self.error(f"'{name}': values must be known integers or enum values", sub)
                items[prefix + (k,)] = v

    def do_enum(self, d):
        enum = Enum(d.name, tuple(d.values))
        self.declare(d.name, enum, d)
        self.enums.append(enum)
        for k, v in enumerate(d.values):
            self.declare(v, Val(k, enum), d)

    def domain_of(self, dom):
        """Renvoie (type, valeurs possibles) d'un domaine déclaré."""
        if isinstance(dom, ast.BoolDomain):
            return "bool", ()
        if isinstance(dom, ast.RangeDomain):
            lo = self.known_int(dom.lo, "lower bound")
            hi = self.known_int(dom.hi, "upper bound")
            if lo > hi:
                self.error(f"empty domain {lo}..{hi}", dom)
            return "int", tuple(range(lo, hi + 1))
        enum = self.lookup(dom.name, dom)
        if not isinstance(enum, Enum):
            self.error(f"'{dom.name}' is not a type", dom)
        return enum, tuple(range(len(enum.values)))

    def do_var(self, d):
        typ, values = self.domain_of(d.domain)
        cell = Cell(d.name, typ, values)
        self.declare(d.name, cell, d)
        self.cells.append(cell)

    def do_array(self, d):
        dims = []
        for e in d.dims:
            if isinstance(e, ast.Name) and isinstance(self.symbols.get(e.name), Enum):
                dims.append(Dim(self.symbols[e.name], len(self.symbols[e.name].values)))
            else:
                size = self.known_int(e, f"size of '{d.name}'")
                if size < 1:
                    self.error(f"size of '{d.name}' must be at least 1, not {size}", e)
                dims.append(Dim(None, size))
        typ, values = self.domain_of(d.domain)
        items = {}
        for key in product(*[dim.keys() for dim in dims]):
            label = "".join(f"[{dim.label(k)}]" for dim, k in zip(dims, key))
            cell = Cell(d.name + label, typ, values)
            items[key] = cell
            self.cells.append(cell)
        self.declare(d.name, Array(d.name, dims, items), d)

    # ---------- instructions ----------
    def do_constraint(self, c):
        f = self.eval_bool(c.expr, "a constraint")
        if f is True:
            return                       # contrainte toujours vraie : elle disparaît
        if f is False and c.pos not in self.false_positions:
            self.false_positions.add(c.pos)
            self.warnings.append(f"line {c.pos[0]}, column {c.pos[1]}: this constraint is "
                                 f"always false, the model is unsatisfiable")
        self.constraints.append(f)       # False est gardée : elle rendra la FNC insatisfiable

    def range_values(self, rng):
        """Valeurs parcourues par un intervalle a..b ou un type énuméré (dans un forall)."""
        if isinstance(rng, ast.RangeDomain):
            lo = self.known_int(rng.lo, "lower bound of a loop")
            hi = self.known_int(rng.hi, "upper bound of a loop")
            return [Val(i, "int") for i in range(lo, hi + 1)]
        enum = self.lookup(rng.name, rng)
        if not isinstance(enum, Enum):
            self.error(f"'{rng.name}' is not a type", rng)
        return [Val(k, enum) for k in range(len(enum.values))]

    def iterate(self, bindings, action, k=0):
        """Exécute action() pour chaque combinaison de valeurs des indices de bindings.
        Les liaisons sont imbriquées de gauche à droite : une borne peut utiliser un indice
        précédent (forall i in 1..N, j in i..N). L'indice est un symbole le temps de la boucle."""
        if k == len(bindings):
            action()
            return
        b = bindings[k]
        for v in self.range_values(b.range):
            self.declare(b.name, v, b)
            self.iterate(bindings, action, k + 1)
            del self.symbols[b.name]

    # ---------- expressions ----------
    def eval(self, e):
        """Évalue partiellement e. Le résultat est l'un de :
        Val (entier ou valeur énumérée connu), True/False (booléen connu),
        Cell (case de variable), ou une formule de ground.py."""
        if isinstance(e, ast.Num):
            return Val(e.value, "int")
        if isinstance(e, ast.Name):
            return self.eval_name(e)
        if isinstance(e, ast.Access):
            return self.eval_access(e)
        if isinstance(e, ast.Neg):
            return Val(-self.known_int(e.expr, "operand of unary '-'"), "int")
        if isinstance(e, ast.BinOp):
            return self.eval_arith(e)
        if isinstance(e, ast.Cmp):
            return self.eval_cmp(e)
        if isinstance(e, ast.Call):
            return self.eval_call(e)
        if isinstance(e, ast.Not):
            return g.mk_not(self.eval_bool(e.expr, "'not'"))
        # Les trois connecteurs binaires sont paresseux : la partie droite n'est évaluée que
        # si la partie gauche ne décide pas déjà du résultat (faux and e = faux, etc.).
        # C'est ce qui permet d'écrire « i < N -> grid[i + 1][1] != ... ».
        if isinstance(e, ast.And):
            left = self.eval_bool(e.left, "'and'")
            if left is False:
                return False
            return g.mk_and([left, self.eval_bool(e.right, "'and'")])
        if isinstance(e, ast.Or):
            left = self.eval_bool(e.left, "'or'")
            if left is True:
                return True
            return g.mk_or([left, self.eval_bool(e.right, "'or'")])
        if isinstance(e, ast.Implies):
            left = self.eval_bool(e.left, "'->'")
            if left is False:
                return True
            return g.mk_or([g.mk_not(left), self.eval_bool(e.right, "'->'")])   # a -> b = non a ou b
        if isinstance(e, ast.Star):
            self.error("a slice [*] is only allowed as an argument of a global constraint", e)
        if isinstance(e, ast.Comprehension):
            self.error("a list comprehension is only allowed as the argument of a global constraint", e)
        raise AssertionError(f"noeud inattendu {e!r}")

    def eval_name(self, e):
        sym = self.lookup(e.name, e)
        if isinstance(sym, (Val, Cell)):
            return sym
        if isinstance(sym, Array):
            self.error(f"array '{e.name}' must be used with {len(sym.dims)} index(es)", e)
        self.error(f"'{e.name}' is a type, not a value", e)

    def eval_arith(self, e):
        a = self.known_int(e.left, f"left operand of '{e.op}'")
        b = self.known_int(e.right, f"right operand of '{e.op}'")
        return Val({"+": a + b, "-": a - b, "*": a * b}[e.op], "int")

    def eval_cmp(self, e):
        left, right = self.eval(e.left), self.eval(e.right)
        tl, tr = type_of(left), type_of(right)
        if tl != tr:
            self.error(f"cannot compare a {type_name(tl)} with a {type_name(tr)}", e)
        if tl == "bool":
            if e.op not in ("=", "!="):
                self.error(f"booleans can only be compared with = and !=, not {e.op}", e)
            iff = g.mk_iff(left, right)
            return iff if e.op == "=" else g.mk_not(iff)
        # entiers ou valeurs énumérées : un terme est une Cell ou un entier connu
        term = lambda r: r.value if isinstance(r, Val) else r
        return g.mk_cmp(e.op, term(left), term(right))

    # ---------- tableaux et tranches ----------
    def access_keys(self, e):
        """Pour un accès a[i][*]..., renvoie (tableau, liste des clés visées, présence d'une tranche).
        Chaque indice est un entier connu dans les bornes, ou * (toutes les valeurs)."""
        array = self.lookup(e.name, e)
        if not isinstance(array, Array):
            self.error(f"'{e.name}' is not an array", e)
        if len(e.indices) != len(array.dims):
            self.error(f"'{e.name}' has {len(array.dims)} dimension(s), "
                       f"but {len(e.indices)} index(es) given", e)
        options = []      # pour chaque dimension, la liste des indices possibles
        has_star = False
        for number, (idx, dim) in enumerate(zip(e.indices, array.dims), start=1):
            if isinstance(idx, ast.Star):
                options.append(list(dim.keys()))
                has_star = True
                continue
            r = self.eval(idx)
            if not isinstance(r, Val):
                self.error(f"index {number} of '{e.name}' must be a known value, not a variable", idx)
            expected = dim.enum if dim.enum else "int"
            if r.typ != expected:
                self.error(f"index {number} of '{e.name}' must be a {type_name(expected)}, "
                           f"not a {type_name(r.typ)}", idx)
            if r.value not in dim.keys():
                shown = dim.label(r.value) if dim.enum else r.value
                self.error(f"index {number} of '{e.name}' is {shown}, out of range "
                           f"{dim.describe()}", idx)
            options.append([r.value])
        return array, list(product(*options)), has_star

    def eval_access(self, e):
        array, keys, has_star = self.access_keys(e)
        if has_star:
            self.error("a slice [*] is only allowed as an argument of a global constraint", e)
        return array.items[keys[0]]

    def eval_args(self, e):
        """Évalue un argument de contrainte globale ; renvoie une LISTE de résultats :
        une tranche donne toutes ses cases (ligne par ligne), une compréhension donne un
        résultat par instance, une expression ordinaire donne un seul résultat."""
        if isinstance(e, ast.Access):
            array, keys, _ = self.access_keys(e)
            return [array.items[k] for k in keys]
        if isinstance(e, ast.Comprehension):
            results = []

            def instance():
                if e.cond is not None:
                    c = self.eval_bool(e.cond, "'where'")
                    if c is not True and c is not False:
                        self.error("the 'where' condition must be known at compile time", e.cond)
                    if c is False:
                        return
                results.extend(self.eval_args(e.expr))

            self.iterate(e.bindings, instance)
            return results
        return [self.eval(e)]

    # ---------- appels de fonction ----------
    def eval_call(self, e):
        if e.name == "abs":
            if len(e.args) != 1:
                self.error(f"abs expects 1 argument, got {len(e.args)}", e)
            return Val(abs(self.known_int(e.args[0], "argument of abs")), "int")
        if e.name not in GLOBALS:
            self.error(f"unknown function '{e.name}'", e)
        args = []
        for a in e.args:
            args.extend(self.eval_args(a))
        if not args:
            self.error(f"{e.name} needs at least one argument", e)
        types = {type_of(a) for a in args}
        if len(types) > 1:
            self.error(f"the arguments of {e.name} must all have the same type "
                       f"(found {', '.join(sorted(type_name(t) for t in types))})", e)
        typ = types.pop()
        if e.name == "allDifferent":
            if typ == "bool":
                self.error("allDifferent applies to integers or enum values, not booleans", e)
            return g.Global(e.name, tuple(a.value if isinstance(a, Val) else a for a in args))
        if typ != "bool":
            self.error(f"{e.name} applies to booleans, not to {type_name(typ)}", e)
        return g.Global(e.name, tuple(args))


def compile_program(program):
    return Compiler().compile(program)


def compile_text(text):
    return compile_program(ast.parse(text))
