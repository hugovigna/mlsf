# Correspondance sujet -> fichiers

Ordre de lecture conseillé : Q1 -> Q6. Les fichiers de test sont dans `tests/`.

## Q1 : modéliser Meowdoku en CNF et générer des grilles
| Demande | Fichier | Fonction / commande |
|---|---|---|
| Lire une grille (format figure 1b) | `meowdoku.py` | `parse_grid` |
| Variables x_{i,j} et clauses (lignes, colonnes, diagonales, régions) | `meowdoku.py` | `var`, `en_conflit`, `encode` |
| Écrire le fichier DIMACS | `meowdoku.py` | `write_dimacs` ; `python meowdoku.py grille.txt out.cnf` |
| Vérifier une configuration selon les règles du jeu | `meowdoku.py` | `is_valid` |
| Générateur de grilles à solution plantée | `generator.py` | `place_chats`, `faire_grossir`, `generate` ; `python generator.py N out.txt [graine]` |
| Visualiser et contrôler (à la main) | `demo_q1.py` | `python demo_q1.py N [graine]` |
| Tests | `tests/test_q1.py` | |

## Q2 : lecture DIMACS et DPLL (algorithmes 1 et 2)
| Demande | Fichier | Fonction / commande |
|---|---|---|
| 2.1 Lire un DIMACS en structure Python | `dimacs.py` | `parse_dimacs` |
| 2.2 Algorithme 1 (SAT/UNSAT) | `dpll.py` | `dpll_sat` |
| 2.2 Algorithme 2 (statut + valuation) | `dpll.py` | `dpll` |
| 2.3 Valider sur des fichiers DIMACS | `bench_q2.py` | `python bench_q2.py gen` puis `run [dossier]` ; **fichiers des enseignants : manquants** |
| 2.4 Commenter les performances | `NOTES_Q2.md` | |
| Tests | `tests/test_q2.py`, `tests/test_q2_2.py` | |

## Q3 : résoudre une grille de bout en bout
| Demande | Fichier | Commande |
|---|---|---|
| Grille -> CNF -> DPLL -> solution au format figure 2 | `solve_grid.py` | `python solve_grid.py grille.txt [sortie.txt]` |
| Exemple du sujet | `data/grids/sujet.txt` | |
| Tests | `tests/test_q3.py` | |

## Q4 : heuristiques de branchement (algorithme 3)
| Demande | Fichier | Détail |
|---|---|---|
| Heuristiques H0 à H7 (statiques/dynamiques) et H8 perso | `heuristics.py` | `creer(nom, F0)`, liste `NOMS` |
| Branchement dans DPLL | `dpll.py` | paramètre `choix` de `dpll` |
| Tests (exemple du sujet, correction vs force brute) | `tests/test_q4.py` | |

## Q5 : instrumenter et comparer
| Demande | Fichier | Détail |
|---|---|---|
| Compteurs (décisions, retours, unitaires, purs) | `dpll.py` | paramètre `stats` |
| Temps CPU et part de l'heuristique, banc de comparaison | `bench_q5.py` | `python bench_q5.py [dossier] [timeout]` |
| Instances (3-SAT, Meowdoku SAT/UNSAT) | `data/cnf/gen/` | générées par `bench_q2.py gen` |
| Résultats bruts | `results/q5.csv`, `results/q5_tableaux.txt` | |
| Analyse | `NOTES_Q5.md` | |

## Q6 : solveur optimisé et interface imposée
| Demande | Fichier | État |
|---|---|---|
| `python sat.py inst.cnf [--mode dpll\|optimized] [--output-model]` | `sat.py` | **à faire** |
| Implémentation optimisée | `optimized.py` | **à faire** |

## Transversal
| Fichier | Rôle |
|---|---|
| `README.md` | vue d'ensemble et commandes |
| `memories.md` | état du projet pour reprise par une autre session |
| `AGENT.MD` | consignes de travail |
| `NOTES_Q2.md`, `NOTES_Q5.md` | matière du rapport (à rédiger en dernier) |
