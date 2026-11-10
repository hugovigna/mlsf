"""Tests de l'analyse (Q3) : déroulage, valeurs connues, court-circuit, normalisation, erreurs."""
import unittest

from tests import helpers   # noqa : met le dossier du projet et partie1/ dans sys.path
import analyse
import ground
import syntax
from syntax import CompileError


def ground_text(text):
    """Les contraintes sans boucle d'un modèle, sous forme de textes."""
    return [ground.show(c) for c in analyse.compile_text(text).constraints]


def error_of(text):
    with unittest.TestCase().assertRaises(CompileError) as ctx:
        analyse.compile_text(text)
    return ctx.exception


class TestDeroulage(unittest.TestCase):
    def test_forall_et_arithmetique(self):
        texte = """const N = 3; array a[N] : 1..3;
                   forall i in 1..N-1 { constraint a[i] != a[i + 1]; }"""
        self.assertEqual(ground_text(texte), ["a[1] != a[2]", "a[2] != a[3]"])

    def test_bornes_dependant_d_un_indice(self):
        texte = """array a[3] : 1..3;
                   forall i in 1..3, j in i+1..3 { constraint a[i] < a[j]; }"""
        self.assertEqual(ground_text(texte), ["a[1] < a[2]", "a[1] < a[3]", "a[2] < a[3]"])

    def test_forall_sur_enum_et_tableau_indice_par_enum(self):
        texte = """enum C = { R, G }; array used[C] : bool;
                   forall c in C { constraint used[c]; }"""
        self.assertEqual(ground_text(texte), ["used[R]", "used[G]"])

    def test_tranches(self):
        texte = "array g[2][3] : 1..3; constraint allDifferent(g[2][*]); constraint allDifferent(g[*][1]);"
        self.assertEqual(ground_text(texte),
                         ["allDifferent(g[2][1], g[2][2], g[2][3])", "allDifferent(g[1][1], g[2][1])"])

    def test_tableau_constant(self):
        texte = """const e[2][2] = [[1, 2], [2, 3]]; array a[3] : 1..3;
                   forall k in 1..2 { constraint a[e[k][1]] != a[e[k][2]]; }"""
        self.assertEqual(ground_text(texte), ["a[1] != a[2]", "a[2] != a[3]"])

    def test_comprehension(self):
        texte = """const r[2][2] = [[1, 2], [2, 2]]; array c[2][2] : bool;
                   constraint atLeastOne(c[i][j] for i in 1..2, j in 1..2 where r[i][j] = 2);"""
        self.assertEqual(ground_text(texte), ["atLeastOne(c[1][2], c[2][1], c[2][2])"])


class TestSimplification(unittest.TestCase):
    def test_valeurs_connues(self):
        self.assertEqual(ground_text("constraint 2 * 3 - 1 = 5;"), [])         # vrai : disparaît
        self.assertEqual(ground_text("constraint abs(2 - 5) = 3 and 1 < 2;"), [])

    def test_contrainte_fausse_avertissement(self):
        m = analyse.compile_text("constraint 1 = 2;")
        self.assertEqual(len(m.warnings), 1)
        self.assertEqual(m.constraints, [False])

    def test_avertissement_une_seule_fois_par_contrainte(self):
        m = analyse.compile_text("forall i in 1..5 { constraint i < 0; }")
        self.assertEqual(len(m.warnings), 1)

    def test_connecteurs_avec_operande_connu(self):
        base = "var x : 1..3; var b : bool; "
        self.assertEqual(ground_text(base + "constraint 1 < 2 and b;"), ["b"])
        self.assertEqual(ground_text(base + "constraint 1 > 2 or b;"), ["b"])
        self.assertEqual(ground_text(base + "constraint 1 > 2 -> b;"), [])
        self.assertEqual(ground_text(base + "constraint 1 < 2 -> x = 2;"), ["x = 2"])

    def test_normalisation(self):
        base = "var x : 1..3; var y : 1..3; "
        self.assertEqual(ground_text(base + "constraint x > y;"), ["y < x"])
        self.assertEqual(ground_text(base + "constraint x >= y;"), ["y <= x"])
        self.assertEqual(ground_text(base + "constraint not (x = 2);"), ["x != 2"])
        self.assertEqual(ground_text(base + "constraint not (x < y);"), ["y <= x"])
        self.assertEqual(ground_text(base + "constraint 2 = x;"), ["x = 2"])
        self.assertEqual(ground_text(base + "constraint not (x = 1 and y = 2);"), ["(x != 1 or y != 2)"])


class TestCourtCircuit(unittest.TestCase):
    PROTEGE = """const N = 3; array a[N] : 1..3;
                 forall i in 1..N { constraint i < N -> a[i + 1] != a[i]; }"""

    def test_acces_hors_bornes_protege(self):
        self.assertEqual(ground_text(self.PROTEGE), ["a[2] != a[1]", "a[3] != a[2]"])

    def test_acces_hors_bornes_non_protege(self):
        e = error_of("const N = 3; array a[N] : 1..3; forall i in 1..N { constraint a[i + 1] != a[i]; }")
        self.assertIn("out of range", e.message)
        self.assertEqual(e.pos[0], 1)

    def test_garde_avec_and_et_or(self):
        base = "array a[2] : 1..3; const k = 3; "
        self.assertEqual(ground_text(base + "constraint k <= 2 and a[k] = 1;"), ["false"])
        self.assertEqual(ground_text(base + "constraint k > 2 or a[k] = 1;"), [])
        error_of(base + "constraint k > 2 and a[k] = 1;")      # non protégé : erreur


class TestErreurs(unittest.TestCase):
    def test_modeles_errones(self):
        cas = [
            ("constraint w;", "undeclared"),
            ("var x : bool; var x : bool;", "already declared"),
            ("const x = 1; var x : bool;", "already declared"),
            ("var x : 1..3; var y : 1..3; constraint x + 1 = y;", "known"),
            ("var x : bool; var y : bool; constraint x + y = 1;", "known"),
            ("enum C = { R, G }; var x : C; constraint x = 1;", "cannot compare"),
            ("var x : 1..3; var b : bool; constraint x = b;", "cannot compare"),
            ("var b : bool; var c : bool; constraint b < c;", "= and !="),
            ("array a[3] : 1..3; constraint a[4] = 1;", "out of range"),
            ("array a[3] : 1..3; constraint a[0] = 1;", "out of range"),
            ("array a[3] : 1..3; constraint a[1][1] = 1;", "dimension"),
            ("array a[3] : 1..3; constraint a = 1;", "index"),
            ("var x : 1..3; var y : 1..3; array a[3] : 1..3; constraint a[x] = 1;", "known"),
            ("var x : 1..3; constraint x[1] = 1;", "not an array"),
            ("array a[3] : 1..3; constraint a[*] = 1;", "slice"),
            ("var x : 1..3; constraint x;", "boolean"),
            ("var x : 1..3; constraint x and x = 1;", "boolean"),
            ("var x : 3..1;", "empty"),
            ("array a[0] : 1..3;", "at least 1"),
            ("var b : bool; constraint allDifferent(b, b);", "not booleans"),
            ("var x : 1..3; constraint atMostOne(x);", "booleans"),
            ("var x : 1..3; var b : bool; constraint allDifferent(x, b);", "same type"),
            ("constraint foo(1);", "unknown function"),
            ("constraint abs(1, 2) = 1;", "1 argument"),
            ("const a[2] = [1, 2, 3];", "values given"),
            ("const a[2] = 5;", "list"),
            ("const a = [1, 2];", "no dimension"),
            ("const N = 3; forall N in 1..2 { constraint N = 1; }", "already declared"),
            ("var x : 1..3; forall i in x..3 { }", "known"),
            ("enum C = { R, G }; var x : C; array a[C] : 1..2; constraint a[1] = 1;", "must be a C"),
            ("array a[2] : Missing;", "undeclared"),
            ("const N = 3; var x : N;", "not a type"),
        ]
        for texte, mot in cas:
            with self.assertRaises(CompileError, msg=texte) as ctx:
                analyse.compile_text(texte)
            self.assertIn(mot, ctx.exception.message, texte)

    def test_format_du_message(self):
        e = error_of("array a[3] : 1..3;\nconstraint a[4] = 1;")
        self.assertEqual(e.format("model.csp"), "model.csp: line 2, column 14: "
                         "index 1 of 'a' is 4, out of range 1..3")


if __name__ == "__main__":
    unittest.main()
