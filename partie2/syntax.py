"""Analyse syntaxique du langage de contraintes (Q2).

Ce fichier contient :
  - la grammaire Lark (analyseur LALR(1)) ;
  - une classe Python par construction du langage (l'arbre de syntaxe abstraite, AST) ;
  - ASTBuilder, qui transforme l'arbre d'analyse de Lark en AST ;
  - parse(texte) : du texte à l'AST ;
  - pretty(noeud) : de l'AST au texte (utile pour les tests : parse(pretty(a)) == a).

Choix : l'AST reflète fidèlement le texte (boucles, tranches, noms non résolus).
Tout le travail de sens (noms, types, déroulage) est fait plus tard, dans analyse.py.
"""
from dataclasses import dataclass, field
from lark import Lark, Transformer, v_args
from lark.exceptions import UnexpectedInput


class CompileError(Exception):
    """Erreur dans le modèle (syntaxe, nom, type...). pos = (ligne, colonne) ou None."""

    def __init__(self, message, pos=None):
        super().__init__(message)
        self.message = message
        self.pos = pos

    def format(self, filename="<modèle>"):
        if self.pos:
            return f"{filename}: line {self.pos[0]}, column {self.pos[1]}: {self.message}"
        return f"{filename}: {self.message}"


# ---------------------------------------------------------------------------
# Grammaire
# ---------------------------------------------------------------------------
# Les priorités sont encodées par des niveaux de règles, du moins prioritaire au plus
# prioritaire :   ->   <   or   <   and   <   not   <   comparaison   <   + -   <   *   <   - unaire
# - "and" et "or" sont associatifs à gauche : règle récursive à gauche (and_ : and_ "and" not_).
# - "->" est associatif à droite : règle récursive à droite (implies : or_ "->" implies).
# - une comparaison n'est pas chaînable : "sum (CMP sum)?" au lieu d'une récursion,
#   donc a = b = c est une erreur de syntaxe (le second "=" est inattendu).
# - "not x = 2" se lit not (x = 2) car la comparaison est plus prioritaire que not.
# Les règles qui commencent par "?" disparaissent de l'arbre quand elles n'ont qu'un enfant
# (pas de noeud inutile pour un simple passage d'un niveau à l'autre).
GRAMMAR = r"""
start: item*

?item: decl | stmt

// ----- déclarations -----
?decl: const_decl | enum_decl | var_decl | array_decl
const_decl: "const" NAME dims EQ init ";"
dims: ("[" sum "]")*
?init: sum | list
list: "[" init ("," init)* "]"
enum_decl: "enum" NAME EQ "{" NAME ("," NAME)* "}" ";"
var_decl: "var" NAME ":" domain ";"
array_decl: "array" NAME ("[" sum "]")+ ":" domain ";"

// un domaine : bool, un intervalle a..b ou un type énuméré. Le même "range" sert aux forall.
?domain: BOOL -> bool_domain
       | range
?range: sum ".." sum   -> range
      | NAME           -> enum_range

// ----- instructions -----
?stmt: constraint | forall
constraint: "constraint" implies ";"
forall: "forall" binding ("," binding)* "{" stmt* "}"
binding: NAME "in" range

// ----- expressions (un niveau par priorité) -----
?implies: or_ (ARROW implies)?
?or_: or_ "or" and_ | and_
?and_: and_ "and" not_ | not_
?not_: "not" not_ -> not_
     | comparison
?comparison: sum (cmp_op sum)?
?cmp_op: EQ | CMP
?sum: sum PLUS term | sum MINUS term | term
?term: term STAR unary | unary
?unary: MINUS unary -> neg
      | atom
?atom: NUMBER                          -> num
     | NAME                            -> name
     | NAME "(" args ")"               -> call
     | NAME "(" comprehension ")"      -> call_comp
     | NAME ("[" index "]")+           -> access
     | "(" implies ")"

args: implies ("," implies)*
// liste en compréhension : atLeastOne(cat[i][j] for i in 1..N, j in 1..M where region[i][j] = z)
// Elle doit être le seul argument : sinon la virgule serait ambiguë (argument suivant ou
// liaison suivante ?) et la grammaire ne serait plus LALR(1).
comprehension: implies "for" binding ("," binding)* ("where" implies)?
?index: sum | star
star: STAR

BOOL: "bool"
ARROW: "->"
// "=" est aussi le "=" des déclarations (const N = 9) : un seul terminal EQ pour les deux
// emplois, sinon le lexer de base verrait deux terminaux identiques et en choisirait un seul.
EQ: "="
CMP: "!=" | "<=" | ">=" | "<" | ">"
PLUS: "+"
MINUS: "-"
STAR: "*"
NUMBER: /[0-9]+/
NAME: /[A-Za-z_][A-Za-z0-9_]*/

COMMENT: /\/\/[^\n]*/
%import common.WS
%ignore WS
%ignore COMMENT
"""

# Les mots-clés (const, enum, var, array, bool, constraint, forall, in, not, and, or, plus
# for et where pour les compréhensions) sont des chaînes de la grammaire : Lark les traite
# avant le terminal NAME, donc ils sont réservés et ne peuvent pas servir de noms.
# lexer="basic" (et non le lexer contextuel par défaut) : le lexer contextuel n'essaie que les
# terminaux acceptés dans l'état courant, donc il laisserait "in" ou "const" servir de nom
# quand un NAME est attendu. Avec le lexer de base, un mot-clé est toujours un mot-clé.
_parser = Lark(GRAMMAR, parser="lalr", lexer="basic", propagate_positions=True)


# ---------------------------------------------------------------------------
# AST
# ---------------------------------------------------------------------------
# Chaque noeud garde sa position (ligne, colonne) pour les messages d'erreur.
# La position ne compte pas dans l'égalité (compare=False) : deux arbres sont égaux
# s'ils ont la même structure, même s'ils viennent de textes mis en page différemment.
@dataclass
class Node:
    pos: tuple = field(default=None, compare=False, repr=False, kw_only=True)


# --- programme et déclarations
@dataclass
class Program(Node):
    items: list


@dataclass
class ConstDecl(Node):
    name: str
    dims: list        # tailles (expressions) ; liste vide pour une constante entière
    init: object      # expression, ou ListLit pour un tableau


@dataclass
class ListLit(Node):
    items: list


@dataclass
class EnumDecl(Node):
    name: str
    values: list


@dataclass
class VarDecl(Node):
    name: str
    domain: object


@dataclass
class ArrayDecl(Node):
    name: str
    dims: list        # chaque dimension : expression (taille n, indices 1..n) ou Name d'un enum
    domain: object


# --- domaines et intervalles
@dataclass
class BoolDomain(Node):
    pass


@dataclass
class RangeDomain(Node):
    lo: object
    hi: object


@dataclass
class EnumDomain(Node):
    name: str


# --- instructions
@dataclass
class Constraint(Node):
    expr: object


@dataclass
class Binding(Node):
    name: str
    range: object     # RangeDomain ou EnumDomain


@dataclass
class Forall(Node):
    bindings: list
    body: list


# --- expressions
@dataclass
class Num(Node):
    value: int


@dataclass
class Name(Node):
    name: str


@dataclass
class Star(Node):     # le joker * d'une tranche
    pass


@dataclass
class Access(Node):   # grid[i][*]
    name: str
    indices: list


@dataclass
class Call(Node):     # abs(e), allDifferent(...)
    name: str
    args: list


@dataclass
class Comprehension(Node):   # expr for bindings where cond
    expr: object
    bindings: list
    cond: object          # None s'il n'y a pas de "where"


@dataclass
class Neg(Node):
    expr: object


@dataclass
class BinOp(Node):    # + - *
    op: str
    left: object
    right: object


@dataclass
class Cmp(Node):      # = != < <= > >=
    op: str
    left: object
    right: object


@dataclass
class Not(Node):
    expr: object


@dataclass
class And(Node):
    left: object
    right: object


@dataclass
class Or(Node):
    left: object
    right: object


@dataclass
class Implies(Node):
    left: object
    right: object


# ---------------------------------------------------------------------------
# Construction de l'AST à partir de l'arbre de Lark
# ---------------------------------------------------------------------------
def _pos(meta):
    return (meta.line, meta.column)


@v_args(meta=True)   # chaque méthode reçoit (meta, children) ; meta donne la position
class ASTBuilder(Transformer):
    def start(self, meta, c):
        return Program(list(c), pos=(1, 1))

    # déclarations
    def const_decl(self, meta, c):
        return ConstDecl(str(c[0]), c[1], c[3], pos=_pos(meta))   # c[2] est le signe =

    def dims(self, meta, c):
        return list(c)

    def list(self, meta, c):
        return ListLit(list(c), pos=_pos(meta))

    def enum_decl(self, meta, c):
        return EnumDecl(str(c[0]), [str(v) for v in c[2:]], pos=_pos(meta))   # c[1] est le signe =

    def var_decl(self, meta, c):
        return VarDecl(str(c[0]), c[1], pos=_pos(meta))

    def array_decl(self, meta, c):
        return ArrayDecl(str(c[0]), list(c[1:-1]), c[-1], pos=_pos(meta))

    # domaines
    def bool_domain(self, meta, c):
        return BoolDomain(pos=_pos(meta))

    def range(self, meta, c):
        return RangeDomain(c[0], c[1], pos=_pos(meta))

    def enum_range(self, meta, c):
        return EnumDomain(str(c[0]), pos=_pos(meta))

    # instructions
    def constraint(self, meta, c):
        return Constraint(c[0], pos=_pos(meta))

    def binding(self, meta, c):
        return Binding(str(c[0]), c[1], pos=_pos(meta))

    def forall(self, meta, c):
        bindings = [x for x in c if isinstance(x, Binding)]
        body = [x for x in c if not isinstance(x, Binding)]
        return Forall(bindings, body, pos=_pos(meta))

    # expressions
    def implies(self, meta, c):     # c = [gauche, ARROW, droite]
        return Implies(c[0], c[2], pos=_pos(meta))

    def or_(self, meta, c):
        return Or(c[0], c[1], pos=_pos(meta))

    def and_(self, meta, c):
        return And(c[0], c[1], pos=_pos(meta))

    def not_(self, meta, c):
        return Not(c[0], pos=_pos(meta))

    def comparison(self, meta, c):  # c = [gauche, CMP, droite]
        return Cmp(str(c[1]), c[0], c[2], pos=_pos(meta))

    def sum(self, meta, c):         # c = [gauche, PLUS ou MINUS, droite]
        return BinOp(str(c[1]), c[0], c[2], pos=_pos(meta))

    def term(self, meta, c):        # c = [gauche, STAR, droite]
        return BinOp("*", c[0], c[2], pos=_pos(meta))

    def neg(self, meta, c):         # c = [MINUS, e]
        return Neg(c[1], pos=_pos(meta))

    def num(self, meta, c):
        return Num(int(c[0]), pos=_pos(meta))

    def name(self, meta, c):
        return Name(str(c[0]), pos=_pos(meta))

    def call(self, meta, c):
        return Call(str(c[0]), c[1], pos=_pos(meta))

    def call_comp(self, meta, c):
        return Call(str(c[0]), [c[1]], pos=_pos(meta))

    def args(self, meta, c):
        return list(c)

    def comprehension(self, meta, c):
        # c = [expr, binding, ..., binding, (cond)] : la condition est le seul enfant
        # qui n'est pas une liaison, après l'expression
        bindings = [x for x in c[1:] if isinstance(x, Binding)]
        rest = [x for x in c[1:] if not isinstance(x, Binding)]
        return Comprehension(c[0], bindings, rest[0] if rest else None, pos=_pos(meta))

    def access(self, meta, c):
        return Access(str(c[0]), list(c[1:]), pos=_pos(meta))

    def star(self, meta, c):
        return Star(pos=_pos(meta))


def parse(text):
    """Du texte à l'AST. Lève CompileError en cas d'erreur de syntaxe."""
    try:
        tree = _parser.parse(text)
    except UnexpectedInput as e:
        # e.line / e.column : position de l'erreur. get_context donne la ligne fautive.
        raise CompileError(f"syntax error, unexpected {_unexpected(e)}", (e.line, e.column))
    return ASTBuilder().transform(tree)


def _unexpected(e):
    """Texte court décrivant l'élément inattendu."""
    token = getattr(e, "token", None)
    if token is not None:
        return "end of input" if token.type == "$END" else repr(str(token))
    return repr(e.char) if hasattr(e, "char") else "input"


# ---------------------------------------------------------------------------
# Affichage (pretty print)
# ---------------------------------------------------------------------------
def pretty(n, indent=0):
    """Texte d'un noeud. Chaque connecteur binaire est parenthésé, donc le texte
    affiché se relit toujours en donnant le même arbre."""
    pad = "    " * indent
    if isinstance(n, Program):
        return "\n".join(pretty(x) for x in n.items)
    if isinstance(n, ConstDecl):
        dims = "".join(f"[{pretty(d)}]" for d in n.dims)
        return f"{pad}const {n.name}{dims} = {pretty(n.init)};"
    if isinstance(n, ListLit):
        return "[" + ", ".join(pretty(x) for x in n.items) + "]"
    if isinstance(n, EnumDecl):
        return f"{pad}enum {n.name} = {{ {', '.join(n.values)} }};"
    if isinstance(n, VarDecl):
        return f"{pad}var {n.name} : {pretty(n.domain)};"
    if isinstance(n, ArrayDecl):
        dims = "".join(f"[{pretty(d)}]" for d in n.dims)
        return f"{pad}array {n.name}{dims} : {pretty(n.domain)};"
    if isinstance(n, BoolDomain):
        return "bool"
    if isinstance(n, RangeDomain):
        return f"({pretty(n.lo)})..({pretty(n.hi)})"
    if isinstance(n, EnumDomain):
        return n.name
    if isinstance(n, Constraint):
        return f"{pad}constraint {pretty(n.expr)};"
    if isinstance(n, Binding):
        return f"{n.name} in {pretty(n.range)}"
    if isinstance(n, Forall):
        head = ", ".join(pretty(b) for b in n.bindings)
        body = "\n".join(pretty(s, indent + 1) for s in n.body)
        return f"{pad}forall {head} {{\n{body}\n{pad}}}"
    if isinstance(n, Num):
        return str(n.value)
    if isinstance(n, Name):
        return n.name
    if isinstance(n, Star):
        return "*"
    if isinstance(n, Access):
        return n.name + "".join(f"[{pretty(i)}]" for i in n.indices)
    if isinstance(n, Call):
        return f"{n.name}({', '.join(pretty(a) for a in n.args)})"
    if isinstance(n, Comprehension):
        text = f"{pretty(n.expr)} for " + ", ".join(pretty(b) for b in n.bindings)
        if n.cond is not None:
            text += f" where {pretty(n.cond)}"
        return text
    if isinstance(n, Neg):
        return f"(-{pretty(n.expr)})"
    if isinstance(n, BinOp):
        return f"({pretty(n.left)} {n.op} {pretty(n.right)})"
    if isinstance(n, Cmp):
        return f"({pretty(n.left)} {n.op} {pretty(n.right)})"
    if isinstance(n, Not):
        return f"(not {pretty(n.expr)})"
    if isinstance(n, And):
        return f"({pretty(n.left)} and {pretty(n.right)})"
    if isinstance(n, Or):
        return f"({pretty(n.left)} or {pretty(n.right)})"
    if isinstance(n, Implies):
        return f"({pretty(n.left)} -> {pretty(n.right)})"
    raise TypeError(f"noeud inconnu : {n!r}")
