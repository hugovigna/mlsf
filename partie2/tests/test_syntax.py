"""Tests de l'analyseur syntaxique (Q2) : priorités, associativité, erreurs, exemples, pretty-print."""
import glob
import os
import unittest

import syntax as S
from syntax import parse, pretty, CompileError

EXEMPLES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "exemples")
a, b, c = S.Name("a"), S.Name("b"), S.Name("c")


def expr(text):
    """L'AST d'une expression : expr("a or b") est Or(a, b)."""
    return parse(f"constraint {text};").items[0].expr


class TestPriorites(unittest.TestCase):
    def test_connecteurs(self):
        cas = [
            ("a or b and c", S.Or(a, S.And(b, c))),
            ("a and b or c", S.Or(S.And(a, b), c)),
            ("not a and b", S.And(S.Not(a), b)),
            ("not (a and b)", S.Not(S.And(a, b))),
            ("a or b -> c", S.Implies(S.Or(a, b), c)),
            ("not not a", S.Not(S.Not(a))),
        ]
        for texte, attendu in cas:
            self.assertEqual(expr(texte), attendu, texte)

    def test_associativite(self):
        self.assertEqual(expr("a and b and c"), S.And(S.And(a, b), c))        # gauche
        self.assertEqual(expr("a or b or c"), S.Or(S.Or(a, b), c))            # gauche
        self.assertEqual(expr("a -> b -> c"), S.Implies(a, S.Implies(b, c)))  # droite
        self.assertEqual(expr("(a -> b) -> c"), S.Implies(S.Implies(a, b), c))

    def test_comparaison_plus_prioritaire_que_not(self):
        # « not x = 2 » se lit not (x = 2)
        self.assertEqual(expr("not a = 2"), S.Not(S.Cmp("=", a, S.Num(2))))

    def test_arithmetique(self):
        n = S.Num
        self.assertEqual(expr("a + b * 2 = c"),
                         S.Cmp("=", S.BinOp("+", a, S.BinOp("*", b, n(2))), c))
        self.assertEqual(expr("a - b - c = 0"),
                         S.Cmp("=", S.BinOp("-", S.BinOp("-", a, b), c), n(0)))          # gauche
        self.assertEqual(expr("-a * b = 0"), S.Cmp("=", S.BinOp("*", S.Neg(a), b), n(0)))  # - unaire d'abord
        self.assertEqual(expr("a - -b = 0"), S.Cmp("=", S.BinOp("-", a, S.Neg(b)), n(0)))

    def test_implication_et_comparaison(self):
        # « -> » ne se confond ni avec « - » ni avec « > »
        self.assertEqual(expr("a->b"), S.Implies(a, b))
        self.assertEqual(expr("a>=b"), S.Cmp(">=", a, b))
        self.assertEqual(expr("a-b>c"), S.Cmp(">", S.BinOp("-", a, b), c))

    def test_acces_et_tranches(self):
        self.assertEqual(expr("allDifferent(g[1][*], g[*][2])"),
                         S.Call("allDifferent", [S.Access("g", [S.Num(1), S.Star()]),
                                                 S.Access("g", [S.Star(), S.Num(2)])]))

    def test_comprehension(self):
        e = expr("atLeastOne(x[i] for i in 1..3 where i != 2)")
        self.assertIsInstance(e.args[0], S.Comprehension)
        self.assertEqual(len(e.args[0].bindings), 1)
        self.assertIsNotNone(e.args[0].cond)


class TestErreurs(unittest.TestCase):
    def test_erreurs_de_syntaxe(self):
        mauvais = [
            "constraint a = b = c;",       # comparaison non chaînable
            "constraint a +;",
            "constraint a",                # point-virgule manquant
            "var in : bool;",              # mot-clé comme nom
            "var const : 1..3;",
            "forall i in 1..3 { constraint a; ",
            "constraint f(a for i in 1..2, b);",   # compréhension : seul argument
            "var x : ;",
            "constraint a $ b;",           # caractère inconnu
        ]
        for texte in mauvais:
            with self.assertRaises(CompileError, msg=texte):
                parse(texte)

    def test_position_de_l_erreur(self):
        with self.assertRaises(CompileError) as ctx:
            parse("var x : bool;\nconstraint x or;")
        self.assertEqual(ctx.exception.pos[0], 2)

    def test_les_mots_commencant_comme_un_mot_cle_sont_des_noms(self):
        parse("var index : bool; var format : bool; var android : bool; var order : bool;")

    def test_commentaires(self):
        self.assertEqual(parse("// rien\nvar x : bool; // fin\n"), parse("var x : bool;"))


class TestExemples(unittest.TestCase):
    def test_exemples_acceptes_et_pretty_relisible(self):
        fichiers = sorted(glob.glob(os.path.join(EXEMPLES, "*.csp")))
        self.assertEqual(len(fichiers), 4)
        for f in fichiers:
            with open(f) as fichier:
                arbre = parse(fichier.read())
            self.assertEqual(parse(pretty(arbre)), arbre, f)    # texte affiché -> même arbre

    def test_pretty_programme_complet(self):
        texte = """
        const N = 3; enum C = { R, G };
        const t[2][2] = [[1, 2], [3, 4]];
        var b : bool; var x : 1..N; var c : C;
        array a[N][C] : 1..N;
        forall i in 1..N, j in i..N { constraint i < j -> a[i][R] != a[j][G] or not (b and x = 1); }
        constraint allDifferent(a[*][R]) and atMostOne(b for k in 1..2 where k > 1);
        """
        arbre = parse(texte)
        self.assertEqual(parse(pretty(arbre)), arbre)


if __name__ == "__main__":
    unittest.main()
