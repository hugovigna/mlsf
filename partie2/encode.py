"""Traduction en FNC (Q4, et mise en forme Dimacs de la Q1/Q5).

Entrée : le Model de analyse.py (cases + contraintes sans boucle).
Sortie : des clauses, listes d'entiers DIMACS non nuls (k = variable k vraie, -k = fausse).

Trois étapes :
  1. Encodage direct des domaines : une case x de domaine {v1..vk} devient k variables
     booléennes x_v1..x_vk (x_v vraie <=> x vaut v) avec les clauses « exactement une ».
  2. Traduction des comparaisons et des contraintes globales en formules sur ces variables
     (translate*). Le résultat est une formule propositionnelle de ground.py dont les feuilles
     sont des Lit (littéraux DIMACS).
  3. Mise en FNC par la transformation de Tseitin (add_formula / literal).
"""
import ground as g
from ground import Lit, Cell, Cmp, Global, And, Or, Not


class Encoder:
    def __init__(self, amo="pairwise"):
        """amo : encodage de « au plus un » : "pairwise" (deux à deux) ou "sinz" (compteur séquentiel)."""
        self.amo = amo
        self.nvars = 0
        self.clauses = []
        self.seen = set()       # clauses déjà produites (pour ne pas les écrire deux fois)
        self.lit_of = {}        # (nom de la case, valeur) -> numéro de variable ; valeur None pour un booléen
        self.aux = {}           # sous-formule -> variable auxiliaire de Tseitin (partagée)

    # ---------- variables et clauses ----------
    def new_var(self):
        self.nvars += 1
        return self.nvars

    def add_clause(self, lits):
        lits = list(dict.fromkeys(lits))          # pas de littéral en double
        if any(-l in lits for l in lits):
            return                                # tautologie (x ou non x) : inutile
        key = tuple(sorted(lits))
        if key in self.seen:
            return
        self.seen.add(key)
        self.clauses.append(lits)

    # ---------- 1. encodage direct des domaines ----------
    def declare_cell(self, cell):
        if cell.typ == "bool":
            self.lit_of[(cell.name, None)] = self.new_var()
            return
        lits = []
        for v in cell.values:
            n = self.new_var()
            self.lit_of[(cell.name, v)] = n
            lits.append(n)
        self.add_clause(lits)                     # au moins une valeur
        self.at_most_one(lits)                    # au plus une valeur

    def is_value(self, term, v):
        """Formule « term vaut v », pour un terme (Cell ou entier connu)."""
        if isinstance(term, Cell):
            n = self.lit_of.get((term.name, v))
            return Lit(n) if n is not None else False     # v hors du domaine : jamais vrai
        return term == v                                  # entier connu : True ou False

    # ---------- 2. comparaisons ----------
    def translate(self, f):
        """Formule de ground.py -> formule sur des Lit."""
        if f is True or f is False:
            return f
        if isinstance(f, Cell):                   # case booléenne
            return Lit(self.lit_of[(f.name, None)])
        if isinstance(f, Not):                    # Cell booléenne ou Global
            return g.mk_not(self.translate(f.f))
        if isinstance(f, And):
            return g.mk_and([self.translate(a) for a in f.args])
        if isinstance(f, Or):
            return g.mk_or([self.translate(a) for a in f.args])
        if isinstance(f, Cmp):
            return self.translate_cmp(f)
        if isinstance(f, Global):
            return self.translate_global(f)
        raise AssertionError(f"formule inattendue {f!r}")

    def translate_cmp(self, c):
        """Comparaison de deux termes (Cell ou entier connu, pas deux entiers) -> formule.

        Cas case / entier connu : on garde les valeurs v de la case qui vérifient la
        comparaison (« bonnes ») et les autres (« mauvaises »). Comme x prend exactement une
        valeur, « x est bonne » s'écrit aussi bien (x_v1 ou x_v2 ...) sur les bonnes valeurs
        que (non x_w1 et non x_w2 ...) sur les mauvaises. On prend la forme la plus courte.
        Exemple pour x dans 1..3 : x <= 2 donne ¬x_3 et non x_1 ou x_2.

        Cas deux cases : pour chaque valeur v de x, on écrit x_v -> (une des valeurs de y
        en relation avec v), soit une clause (¬x_v ou y_w1 ou y_w2 ...) par valeur v.
        Pour x = y, la clause est (¬x_v ou y_v) ; pour x < y, c'est (¬x_v ou y_w, w > v).
        Il faut, pour que ce soit exact, que y ait exactement une valeur : c'est le cas."""
        l, r = c.left, c.right
        if isinstance(l, Cell) and isinstance(r, Cell):
            if c.op == "!=":
                # x != y : jamais la même valeur en même temps (clause binaire par valeur commune)
                return g.mk_and([g.mk_or([g.mk_not(self.is_value(l, v)), g.mk_not(self.is_value(r, v))])
                                 for v in l.values if v in r.values])
            return g.mk_and([
                g.mk_or([g.mk_not(self.is_value(l, v))] +
                        [self.is_value(r, w) for w in r.values if g.holds(c.op, v, w)])
                for v in l.values])
        # une case et un entier connu (de l'un ou l'autre côté)
        cell, known = (l, r) if isinstance(l, Cell) else (r, l)
        if isinstance(l, Cell):
            ok = lambda v: g.holds(c.op, v, known)
        else:
            ok = lambda v: g.holds(c.op, known, v)
        good = [v for v in cell.values if ok(v)]
        bad = [v for v in cell.values if not ok(v)]
        if len(good) <= len(bad):
            return g.mk_or([self.is_value(cell, v) for v in good])
        return g.mk_and([g.mk_not(self.is_value(cell, v)) for v in bad])

    # ---------- contraintes globales ----------
    def translate_global(self, gl):
        """Contrainte globale -> formule (pas de variable auxiliaire, donc utilisable sous
        une négation, une implication, etc.). Au plus un : encodage deux à deux."""
        if gl.name == "allDifferent":
            return g.mk_and([self.pairwise_amo([self.is_value(a, v) for a in gl.args])
                             for v in self.all_values(gl.args)])
        args = [self.translate(a) for a in gl.args]
        if gl.name == "atLeastOne":
            return g.mk_or(args)
        if gl.name == "atMostOne":
            return self.pairwise_amo(args)
        return g.mk_and([g.mk_or(args), self.pairwise_amo(args)])     # exactlyOne

    @staticmethod
    def all_values(terms):
        """Union des valeurs possibles des termes d'un allDifferent."""
        values = set()
        for t in terms:
            values.update(t.values if isinstance(t, Cell) else (t,))
        return sorted(values)

    @staticmethod
    def pairwise_amo(fs):
        """Au plus une des formules fs : pour chaque couple, au moins l'une est fausse."""
        return g.mk_and([g.mk_or([g.mk_not(a), g.mk_not(b)])
                         for i, a in enumerate(fs) for b in fs[i + 1:]])

    # ---------- 3. mise en FNC ----------
    def add_constraint(self, f):
        """Ajoute une contrainte de niveau supérieur. Une contrainte globale à ce niveau est
        encodée directement en clauses, ce qui permet d'utiliser le compteur séquentiel."""
        if f is True:
            return
        if isinstance(f, And):
            for a in f.args:
                self.add_constraint(a)
        elif isinstance(f, Global):
            self.add_global(f)
        else:
            self.add_formula(self.translate(f))

    def add_global(self, gl):
        """Contrainte globale vraie « de plein droit » (jamais sous une négation)."""
        if gl.name == "allDifferent":
            # pour chaque valeur, au plus une des expressions la prend
            for v in self.all_values(gl.args):
                self.add_amo([self.is_value(a, v) for a in gl.args])
            return
        args = [self.translate(a) for a in gl.args]
        if gl.name in ("atLeastOne", "exactlyOne"):
            self.add_formula(g.mk_or(args))
        if gl.name in ("atMostOne", "exactlyOne"):
            self.add_amo(args)

    def add_amo(self, fs):
        """Clauses « au plus une des formules fs est vraie » (fs : formules déjà traduites)."""
        lits, trues = [], 0
        for f in fs:
            if f is True:
                trues += 1
            elif f is not False:
                lits.append(self.literal(f))
        if trues > 1:
            self.add_clause([])                   # deux vraies : impossible
        elif trues == 1:
            for l in lits:
                self.add_clause([-l])             # une vraie : toutes les autres sont fausses
        else:
            self.at_most_one(lits)

    def at_most_one(self, lits):
        """Au plus un des littéraux lits, selon l'encodage choisi."""
        n = len(lits)
        # En dessous de 5 littéraux, le deux à deux est plus court que le compteur (n(n-1)/2 < 3n-4).
        if self.amo == "pairwise" or n < 5:
            for i in range(n):
                for j in range(i + 1, n):
                    self.add_clause([-lits[i], -lits[j]])
            return
        # Compteur séquentiel de Sinz : s_i = « l'un des x_1..x_i est vrai ».
        s = [self.new_var() for _ in range(n - 1)]
        self.add_clause([-lits[0], s[0]])
        for i in range(1, n - 1):
            self.add_clause([-lits[i], s[i]])             # x_i vrai => s_i
            self.add_clause([-s[i - 1], s[i]])            # s_{i-1} => s_i
            self.add_clause([-lits[i], -s[i - 1]])        # x_i et s_{i-1} : interdit
        self.add_clause([-lits[n - 1], -s[n - 2]])

    def add_formula(self, f):
        """Ajoute la formule f (sur des Lit) comme contrainte. Si c'est une conjonction, on
        ajoute chaque morceau ; si c'est une disjonction de littéraux, c'est une seule clause,
        sans variable auxiliaire : Tseitin n'est utilisé que pour les sous-formules qui ne
        sont pas des littéraux."""
        if f is True:
            return
        if f is False:
            self.add_clause([])
        elif isinstance(f, And):
            for a in f.args:
                self.add_formula(a)
        elif isinstance(f, Or):
            self.add_clause([self.literal(a) for a in f.args])
        else:
            self.add_clause([self.literal(f)])

    def literal(self, f):
        """Littéral DIMACS équivalent à la formule f (sur des Lit, sans constante).
        Transformation de Tseitin : une sous-formule And/Or reçoit une variable auxiliaire a
        avec a <-> f, définie par des clauses. On réutilise a si on retrouve la même sous-formule."""
        if isinstance(f, Lit):
            return f.n
        if f in self.aux:
            return self.aux[f]
        parts = [self.literal(a) for a in f.args]
        a = self.new_var()
        self.aux[f] = a
        if isinstance(f, And):
            for p in parts:
                self.add_clause([-a, p])                      # a => chaque part
            self.add_clause([a] + [-p for p in parts])        # toutes les parts => a
        else:
            self.add_clause([-a] + parts)                     # a => une des parts
            for p in parts:
                self.add_clause([a, -p])                      # chaque part => a
        return a


# ---------------------------------------------------------------------------
# Du modèle analysé à la FNC
# ---------------------------------------------------------------------------
def encode(model, amo="pairwise"):
    enc = Encoder(amo)
    for cell in model.cells:
        enc.declare_cell(cell)
    for f in model.constraints:
        enc.add_constraint(f)
    return enc


def to_dimacs(enc, model):
    """Texte Dimacs. Les lignes « c var k nom = valeur » gardent la correspondance entre
    numéros et variables du modèle (les variables auxiliaires n'y figurent pas)."""
    lines = []
    for cell in model.cells:
        if cell.typ == "bool":
            lines.append(f"c var {enc.lit_of[(cell.name, None)]} {cell.name}")
        else:
            for v in cell.values:
                lines.append(f"c var {enc.lit_of[(cell.name, v)]} {cell.name} = {show_value(cell, v)}")
    lines.append(f"p cnf {enc.nvars} {len(enc.clauses)}")
    for c in enc.clauses:
        lines.append(" ".join(map(str, c)) + " 0")
    return "\n".join(lines) + "\n"


def show_value(cell, v):
    return cell.typ.values[v] if isinstance(cell.typ, g.Enum) else str(v)


def decode(enc, model, sat_model):
    """Valeurs des cases d'après un modèle du solveur (liste de littéraux ±k).
    Renvoie une liste de (nom, valeur affichable)."""
    true_vars = {l for l in sat_model if l > 0}
    result = []
    for cell in model.cells:
        if cell.typ == "bool":
            result.append((cell.name, "true" if enc.lit_of[(cell.name, None)] in true_vars else "false"))
        else:
            # la case vaut la valeur v dont la variable x_v est vraie (il y en a exactement une)
            v = next(v for v in cell.values if enc.lit_of[(cell.name, v)] in true_vars)
            result.append((cell.name, show_value(cell, v)))
    return result
