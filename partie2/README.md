# MLSF : compilateur de contraintes vers SAT (partie II)

Python 3.12. Seule dépendance : `lark` (`pip install -r requirements.txt`).
Le solveur est celui de la partie I, utilisé tel quel depuis `../partie1/`.
Rapport : `rapport.pdf` (source `rapport.tex`).

## Fichiers
| Fichier | Rôle | Question |
|---|---|---|
| `syntax.py` | grammaire Lark (LALR), AST, `parse`, `pretty`, erreurs de syntaxe avec ligne/colonne | Q2 |
| `analyse.py` | table des symboles, déroulage des `forall`, évaluation des valeurs connues, tranches, listes en compréhension, erreurs et avertissements | Q3 |
| `ground.py` | formules sans boucle (cases, comparaisons, globales) et constructeurs qui simplifient | Q3 / Q4 |
| `encode.py` | traduction en clauses : encodage direct des domaines, Tseitin, comparaisons, globales, Sinz, écriture DIMACS, lecture du modèle | Q1 / Q4 |
| `csp.py` | ligne de commande, appel du solveur de la partie I | Q5 |
| `meow_csp.py` | Meowdoku : convertisseur grille -> `.csp` (6.1), les modèles, vérificateur indépendant, recherche exhaustive, grilles aléatoires | Q6 |
| `bench_q6.py` | comparaison des modèles et des solveurs (`results/q6.csv`) | 6.3, 6.4, 6.6 |
| `exemples/` | pigeons (UNSAT), reines, coloriage de Petersen, sudoku | Q5 |
| `tests/` | 59 tests unitaires (voir plus bas) | toutes |
| `proplog/` | code fourni avec le sujet, non utilisé | |

## Utilisation
```
pip install -r requirements.txt
python csp.py exemples/queens.csp                    # FNC au format DIMACS sur la sortie standard
python csp.py exemples/queens.csp --dimacs q.cnf     # ... ou dans un fichier
python csp.py exemples/sudoku.csp --solve            # "s SATISFIABLE" puis "grid[1][1] = 5", ...
python csp.py exemples/queens.csp --ground           # contraintes après déroulage des boucles
python csp.py exemples/queens.csp --solve --amo sinz --solver dpll --stats
```
Options : `--amo pairwise|sinz` (encodage de « au plus un », défaut `pairwise`), `--solver optimized|dpll`
(solveur de la partie I, défaut `optimized`), `--stats` (taille de la FNC et temps, sur stderr).
Les erreurs de modèle sont écrites sur stderr sous la forme `fichier: line L, column C: message`
(code de sortie 1) ; les avertissements (contrainte toujours fausse) aussi.

### Question 6 (Meowdoku)
```
python meow_csp.py ../partie1/data/grids/g6.txt --modele 2alo > g6.csp   # 6.1 : grille -> modèle
python csp.py g6.csp --solve
python bench_q6.py 60 4                       # temps limite 60 s, 4 processus -> results/q6.csv
python bench_q6.py 60 4 6,8,10 3              # tailles et nombre de grilles par taille
```
Modèles : `1` (position du chat de chaque région), `2` (une booléenne par case, avec « au plus un
par région »), `2alo` (modèle 2 + « au moins un par région », 6.4), `general` (N, M, K quelconques, 6.5).

### Tests
```
python -m unittest discover -s tests -t .      # 59 tests, une dizaine de secondes
```
| Fichier | Contenu |
|---|---|
| `test_syntax.py` | priorités, associativité, erreurs de syntaxe, `parse(pretty(a)) == a` |
| `test_analyse.py` | déroulage, court-circuit, tranches, erreurs et positions |
| `test_encode.py` | chaque encodage contre l'énumération de toutes ses solutions |
| `test_random.py` | modèles aléatoires : la FNC a exactement les solutions de l'interprète de référence `oracle.py` (écrit indépendamment, par force brute), avec les deux encodages |
| `test_examples.py` | les 4 exemples en ligne de commande, vérifiés indépendamment ; format DIMACS ; code d'erreur |
| `test_meowdoku.py` | modèles de la Q6 contre le vérificateur et la recherche exhaustive |

## Choix de conception
- **Un seul passage pour l'analyse** : le compilateur parcourt l'AST en évaluant au fur et à mesure tout ce qui est connu (constantes, indices de boucle) ; il ne reste que des formules sur des cases de variables. `and`, `or`, `->` s'évaluent paresseusement (le `l >= 1 and l <= M and ... cat[i+1][l]` de l'énoncé ne sort pas des bornes).
- **Entiers et énumérés** : encodage direct (une variable booléenne par valeur, « exactement une valeur » par case). Les valeurs d'un énuméré sont 0, 1, ... dans l'ordre de déclaration, ce qui permet `z1 < z2`.
- **Tseitin** : une variable auxiliaire `a <-> f` par sous-formule non littérale, partagée par un cache ; une conjonction ou disjonction de littéraux posée directement reste de simples clauses.
- **Négation** : poussée vers les feuilles (De Morgan, comparaisons renversées) dès la construction des formules ; la négation ne porte plus que sur des littéraux.
- **Contrainte toujours fausse** : on l'ajoute comme clause vide (la FNC est UNSAT) et on émet un avertissement.
- **Compteur de Sinz** pour `atMostOne` à partir de 5 littéraux (`--amo sinz`), seulement pour une contrainte posée directement ; sous une négation, ou dans une formule composée, on garde le deux à deux (voir le rapport).
- **Extension du langage** : liste en compréhension en seul argument d'une globale, `atLeastOne(cat[i][j] for i in 1..N, j in 1..M where region[i][j] = z)` ; `for` et `where` deviennent des mots réservés.

## Limites connues
- Une branche qui n'est jamais évaluée (court-circuit) n'est pas vérifiée au niveau des types.
- Une liste en compréhension doit être le seul argument de la globale.
- L'équivalence `<->` n'est pas implémentée (question optionnelle non traitée).
- Les temps de `bench_q6.py` ont été mesurés avec 4 processus en parallèle : ils sont indicatifs.
