# MLSF : solveur DPLL et Meowdoku (partie I)

Sujet : `sujet_projet.pdf`. Python 3.12, aucune dépendance. Consignes de travail : `AGENT.MD`. État d'avancement : `memories.md`. Correspondance sujet -> fichiers : `QUESTIONS.md`.

## Fichiers
| Fichier | Rôle |
|---|---|
| `meowdoku.py` | lecture de grille, encodage CNF (DIMACS), vérification `is_valid` (Q1) |
| `generator.py` | génération de grilles N×N à solution plantée (Q1) |
| `dimacs.py` | lecture DIMACS -> set de frozenset (Q2.1) |
| `dpll.py` | DPLL algorithmes 1 et 2/3, avec compteurs facultatifs (Q2, Q5) |
| `solve_grid.py` | grille -> CNF -> DPLL -> solution au format du sujet (Q3) |
| `heuristics.py` | heuristiques H0, H1, H2s/d, H3d, H4d, H7s/d, H8 (Q4) |
| `bench_q2.py`, `bench_q5.py` | génération d'instances, validation, comparaison des heuristiques |
| `demo_q1.py` | visualisation de la Q1 |
| `NOTES_Q2.md`, `NOTES_Q5.md` | analyses (matière du rapport) |
| `tests/` | tests unitaires |

## Utilisation
```
python generator.py 8 data/grids/g8.txt 1          # grille 8x8 (graine 1)
python meowdoku.py data/grids/g8.txt g8.cnf         # grille -> DIMACS
python solve_grid.py data/grids/sujet.txt           # résout une grille
python demo_q1.py 6 1                               # visualise grille, CNF, solutions
python bench_q2.py gen && python bench_q5.py        # instances puis comparaison (results/q5.csv)
python -m unittest discover -s tests -t .           # tests
```
`sat.py` (interface imposée de la Q6) n'est pas encore écrit.
