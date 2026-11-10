"""Interprète de référence pour les tests : donne le sens d'un modèle SANS le compiler.

Le compilateur évalue partiellement les expressions puis les traduit en clauses. Pour le
tester, on a besoin d'une deuxième lecture du langage qui n'utilise rien de tout cela :
ici, on fixe une valeur à chaque variable et on évalue directement chaque contrainte avec
des booléens et des entiers Python. Un modèle est satisfiable si et seulement si au moins
une valuation fait passer toutes les contraintes (on les essaie toutes, pour de petits modèles).

Seul l'analyseur syntaxique (syntax.parse) est partagé avec le compilateur.
"""
import itertools

import syntax as ast


class Oracle:
    def __init__(self, program):
        self.program = program

    # ---------- une exécution complète pour une valuation donnée ----------
    def run(self, assignment):
        """Exécute le programme. assignment : nom d'une case -> valeur (entier, booléen).
        Renvoie True si toutes les contraintes sont vraies. Remplit self.domains."""
        self.env = {}          # nom -> entier, tableau (dict clé -> entier), ou ("enum", noms)
        self.domains = {}      # nom d'une case -> liste de valeurs possibles
        self.values = assignment
        self.ok = True
        for item in self.program.items:
            self.exec(item)
        return self.ok

    def exec(self, item):
        if isinstance(item, ast.ConstDecl):
            if not item.dims:
                self.env[item.name] = self.ev(item.init)
            else:
                sizes = [self.ev(d) for d in item.dims]
                self.env[item.name] = self.const_array(item.init, sizes, ())
        elif isinstance(item, ast.EnumDecl):
            self.env[item.name] = ("enum", item.values)
            for k, v in enumerate(item.values):
                self.env[v] = k
        elif isinstance(item, ast.VarDecl):
            self.declare_cell(item.name, item.domain)
        elif isinstance(item, ast.ArrayDecl):
            keysets = []
            for d in item.dims:
                keysets.append(self.keys_of(d))
            cells = {}
            for key in itertools.product(*keysets):
                name = item.name + "".join(f"[{k}]" for k in key)
                cells[key] = self.declare_cell(name, item.domain)
            self.env[item.name] = cells
        elif isinstance(item, ast.Constraint):
            if not self.ev(item.expr):
                self.ok = False
        elif isinstance(item, ast.Forall):
            self.loop(item.bindings, lambda: [self.exec(s) for s in item.body])

    def keys_of(self, dim):
        """Indices d'une dimension : 1..n, ou 0..k-1 pour un type énuméré."""
        if isinstance(dim, ast.Name) and isinstance(self.env.get(dim.name), tuple):
            return range(len(self.env[dim.name][1]))
        return range(1, self.ev(dim) + 1)

    def domain_values(self, dom):
        if isinstance(dom, ast.BoolDomain):
            return [False, True]
        if isinstance(dom, ast.RangeDomain):
            return list(range(self.ev(dom.lo), self.ev(dom.hi) + 1))
        return list(range(len(self.env[dom.name][1])))

    def declare_cell(self, name, dom):
        values = self.domain_values(dom)
        self.domains[name] = values
        value = self.values.get(name, values[0])
        if "[" not in name:
            self.env[name] = value      # variable simple ; les cases de tableau sont rangées dans le dict du tableau
        return value

    def const_array(self, lit, sizes, prefix):
        out = {}
        for k, sub in enumerate(lit.items, start=1):
            if len(sizes) > 1:
                out.update(self.const_array(sub, sizes[1:], prefix + (k,)))
            else:
                out[prefix + (k,)] = self.ev(sub)
        return out

    def loop(self, bindings, action):
        if not bindings:
            action()
            return
        b, rest = bindings[0], bindings[1:]
        if isinstance(b.range, ast.RangeDomain):
            values = range(self.ev(b.range.lo), self.ev(b.range.hi) + 1)
        else:
            values = range(len(self.env[b.range.name][1]))
        for v in values:
            self.env[b.name] = v
            self.loop(rest, action)
        del self.env[b.name]

    # ---------- expressions : valeurs Python ordinaires ----------
    def ev(self, e):
        if isinstance(e, ast.Num):
            return e.value
        if isinstance(e, ast.Name):
            return self.env[e.name]
        if isinstance(e, ast.Access):
            return self.access(e)
        if isinstance(e, ast.Neg):
            return -self.ev(e.expr)
        if isinstance(e, ast.BinOp):
            a, b = self.ev(e.left), self.ev(e.right)
            return a + b if e.op == "+" else a - b if e.op == "-" else a * b
        if isinstance(e, ast.Cmp):
            a, b = self.ev(e.left), self.ev(e.right)
            return {"=": a == b, "!=": a != b, "<": a < b, "<=": a <= b, ">": a > b, ">=": a >= b}[e.op]
        if isinstance(e, ast.Not):
            return not self.ev(e.expr)
        if isinstance(e, ast.And):
            return self.ev(e.left) and self.ev(e.right)       # paresseux, comme le langage
        if isinstance(e, ast.Or):
            return self.ev(e.left) or self.ev(e.right)
        if isinstance(e, ast.Implies):
            return (not self.ev(e.left)) or self.ev(e.right)
        if isinstance(e, ast.Call):
            return self.call(e)
        raise AssertionError(e)

    def access(self, e):
        # tableau constant ou tableau de cases : dans les deux cas un dict (indices -> valeur)
        return self.env[e.name][tuple(self.ev(i) for i in e.indices)]

    def flat(self, a):
        """Valeurs d'un argument de contrainte globale (tranche, compréhension ou expression)."""
        if isinstance(a, ast.Access) and any(isinstance(i, ast.Star) for i in a.indices):
            ranges = []
            for i, d in enumerate(a.indices):
                if isinstance(d, ast.Star):
                    ranges.append(self.star_keys(a.name, i))
                else:
                    ranges.append([self.ev(d)])
            return [self.access(ast.Access(a.name, [ast.Num(k) for k in key]))
                    for key in itertools.product(*ranges)]
        if isinstance(a, ast.Comprehension):
            out = []

            def inst():
                if a.cond is None or self.ev(a.cond):
                    out.extend(self.flat(a.expr))

            self.loop(a.bindings, inst)
            return out
        return [self.ev(a)]

    def star_keys(self, name, position):
        """Indices possibles de la dimension `position` du tableau `name`."""
        return sorted({key[position] for key in self.env[name]})

    def call(self, e):
        if e.name == "abs":
            return abs(self.ev(e.args[0]))
        values = [v for a in e.args for v in self.flat(a)]
        if e.name == "allDifferent":
            return len(set(values)) == len(values)
        count = sum(1 for v in values if v)
        return {"atLeastOne": count >= 1, "atMostOne": count <= 1, "exactlyOne": count == 1}[e.name]


def all_solutions(text):
    """Toutes les valuations qui satisfont le modèle (dict nom -> valeur). Pour de petits modèles."""
    oracle = Oracle(ast.parse(text))
    oracle.run({})
    names = list(oracle.domains)
    out = []
    for combo in itertools.product(*[oracle.domains[n] for n in names]):
        assignment = dict(zip(names, combo))
        if oracle.run(assignment):
            out.append(assignment)
    return out


def check(text, assignment):
    """Vrai si la valuation (nom -> valeur) satisfait toutes les contraintes du modèle."""
    return Oracle(ast.parse(text)).run(assignment)
