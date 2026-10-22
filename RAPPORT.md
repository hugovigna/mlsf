# Projet MLSF – Partie I : un solveur SAT pour Meowdoku

Binôme : *(noms)*. Python 3.12, aucune bibliothèque externe. Tout se lance depuis la racine du dépôt (voir `README.md`). Les tests se lancent avec `python -m unittest discover -s tests -t .` (49 tests).

On a limité le travail au cas N = M = K (une grille carrée, un chat par ligne et par colonne).

## Question 1 : modéliser Meowdoku en CNF

**Variables.** Pour une grille n×n, la variable x_{i,j} vaut vrai s'il y a un chat en (i, j). Elle est numérotée i·n + j + 1 (avec i, j à partir de 0), donc de 1 à n².

**Clauses.** Il y en a deux sortes :
- **Conflits.** Pour chaque paire de cases qui ne peuvent pas avoir un chat toutes les deux, on met (¬x_a ∨ ¬x_b). Deux cases sont en conflit si elles sont sur la même ligne, la même colonne, la même région, ou collées (8-voisinage, donc diagonales comprises).
- **Au moins un chat par région.** Pour chaque région, une clause (x_a ∨ x_b ∨ …) avec toutes ses cases.

**Pourquoi c'est correct.** Au plus un chat par région, par ligne et par colonne est assuré par les clauses de conflit. Avec n régions et au moins un chat dans chacune, il y a donc exactement un chat par région. Les n chats sont sur n lignes différentes, donc exactement un par ligne, et de même par colonne. Le nombre de clauses est de l'ordre de n⁴, parce qu'on regarde toutes les paires de cases (`meowdoku.py`, fonction `encode`).

**Vérification.** `is_valid` contrôle une configuration directement avec les règles du jeu, sans passer par la CNF. Toutes les solutions trouvées plus loin sont passées dedans.

**Générateur** (`generator.py`). La méthode garantit une solution :
1. On place n chats, un par ligne et par colonne, jamais collés (choix aléatoire avec retour arrière).
2. Chaque chat est la graine d'une région. On fait grossir les régions case par case, en ajoutant au hasard une case libre voisine d'une région, jusqu'à remplir la grille.

Les chats initiaux forment donc une solution. Les grilles obtenues n'ont pas forcément une solution unique.

## Question 2 : lecture DIMACS et DPLL

- `dimacs.py` lit un fichier DIMACS. Une formule est un `set` de `frozenset` d'entiers signés. Conséquence : les clauses en double disparaissent.
- `dpll.py` contient l'algorithme 1 (`dpll_sat`) et l'algorithme 2 (`dpll`, qui renvoie aussi la valuation). Chaque appel recrée une nouvelle formule avec `simplifier`.

**Validation.** On a utilisé les 41 instances publiques DIMACS (`public-instances/`) : 11 cas limites ou d'interface et 30 instances SATLIB de 42 à 1363 variables. Le statut obtenu avec `dpll` est identique à `expected.json` pour les 41 fichiers, et chaque modèle trouvé satisfait toutes les clauses (temps dans `results/q2_public_times.csv`). Ces tests ont fait apparaître que certains fichiers écrivent une clause sur plusieurs lignes ; `parse_dimacs` accumule maintenant les littéraux jusqu'au `0`. On a aussi comparé `dpll` à une force brute sur 300 formules aléatoires de moins de 8 variables (statut et modèle).

**Performances** (choix aléatoire, une exécution par instance, sans timeout). 28 des 30 instances `public-*` sont résolues en moins de 3 s, dont 25 en moins d'une seconde. Les deux autres sont plus dures : `public-12` (SAT, 65 s) et `public-03` (UNSAT, 117,5 s). Les temps varient beaucoup d'une exécution à l'autre à cause du hasard : `public-06` a dépassé 120 s lors d'un premier lancement puis a été résolue en 0,16 s au suivant. Les instances UNSAT coûtent en général plus cher que les SAT, car il faut explorer tout l'arbre.

## Question 3 : résoudre une grille

`solve_grid.py` lit la grille, la convertit en CNF, appelle DPLL, puis écrit le fichier au format de la figure 2 (dictionnaire région → position, puis grille avec `*`). La solution est toujours vérifiée avec `is_valid`. Sur l'exemple du sujet (`data/grids/sujet.txt`), la sortie est identique à la figure 2.

## Question 4 : heuristiques de branchement

Dans `heuristics.py`, on a implémenté H0, H1, H2 (statique et dynamique), H3d, H4d (MOMS), H7 (statique et dynamique) et une heuristique à nous, **H8**. Cela couvre les contraintes du sujet : H3d et H7 sont fondées sur un littéral, H4d et H7 utilisent la taille des clauses, et plusieurs sont dynamiques. On n'a pas fait H5 ni H6.

**H8** exploite la structure de l'encodage : les seules clauses entièrement positives sont les clauses « au moins un chat dans la région ». H8 prend la région qui a le moins de cases encore possibles (principe « échouer d'abord »), choisit dans cette région la variable la plus fréquente et la met à 1. Une case à 1 élimine tout de suite toutes les cases en conflit avec elle. S'il n'y a plus de clause positive, elle se rabat sur H7d.

**Vérification.** Chaque heuristique donne le même statut que l'algorithme 2 sur toutes les instances de la Q2, et les modèles sont valides.

## Question 5 : comparaison

On a instrumenté DPLL avec des compteurs (décisions, retours arrière, propagations unitaires, littéraux purs) et mesuré le temps CPU et la part passée dans l'heuristique (`bench_q5.py`). Protocole : 160 instances (3-SAT aléatoire, grilles Meowdoku à solution plantée, grilles à régions aléatoires SAT ou UNSAT), 9 variantes, timeout de 10 s, une exécution par cas. Détails dans `NOTES_Q5.md` et `results/`.

Ce qu'on a observé :
1. **Les heuristiques classiques (H2 à H7) sont mauvaises sur Meowdoku.** Chaque variable est positive dans une seule clause et négative dans des dizaines. H2d, H3d, H4d et H7d choisissent donc la valeur 0 pour 100 % de leurs décisions, ce qui ne propage presque rien. Elles font plus de décisions que le choix aléatoire pour n ≤ 10 (88 contre 17 pour n = 10).
2. **Sur du 3-SAT aléatoire, c'est l'inverse.** Les heuristiques dynamiques font 5 à 10 fois moins de décisions que H0 et H1, et H4d est la meilleure. L'intuition classique est donc juste, mais elle dépend de la structure du problème.
3. **H8 domine sur Meowdoku.** Pour n = 14 sur grilles SAT, elle prend 24 décisions contre 670 à 3 200 pour les autres. Elle est la seule à résoudre les 7 grilles UNSAT de n = 14. Sur UNSAT n = 10, elle fait 3 décisions contre 430 à 6 600. Sa limite : elle dépend de l'encodage et n'est pas générique.
4. **Statique contre dynamique.** Le dynamique recalcule tout à chaque décision : il peut prendre jusqu'à 55 % du temps CPU. Mais sur Meowdoku il vaut largement le coup (n = 12, H2s : 3 124 décisions, H2d : 242). Sur le 3-SAT de petite taille, le gain et le coût s'annulent.
5. **Sur UNSAT,** le nombre de décisions est égal au nombre de retours arrière et la valeur choisie en premier n'a pas d'importance : seul l'ordre des variables compte.

**Limites.** Une seule exécution par cas, des échantillons de 2 à 10 instances, pas de test statistique : ce sont des tendances. Les grilles à régions aléatoires sont surtout UNSAT à partir de n = 12, et les grilles à solution plantée ne ressemblent peut-être pas à celles des enseignants.

## Question 6 : solveur optimisé

**Interface.** `sat.py instance.cnf [--mode dpll|optimized] [--output-model]`. Le mode `dpll` appelle l'algorithme 2 de la Q2. Sans mode, on utilise `optimized`. Seul le résultat est écrit sur stdout (`s SATISFIABLE` ou `s UNSATISFIABLE`, puis `v … 0` avec `--output-model`). Une erreur d'usage donne un message sur stderr et le code 2. Les deux modes lisent le fichier avec le même lecteur, plus tolérant que celui de la Q2 (clause sur plusieurs lignes, dernier 0 manquant, ligne `%`…).

**Démarche.** Suivant la conclusion de la Q5 (H8 est la bonne heuristique), on est parti du DPLL de `dpll.py` et on a profilé. En chronométrant `dpll` avec H8 sur 10 grilles de chaque famille Meowdoku (n = 10, 12, 14), `simplifier` prend 58 à 63 % du temps, `trouver_unitaire` 11 à 13 %, `trouver_pur` environ 5 % et H8 14 à 18 %, soit 92 à 94 % au total pour ces trois causes (90 % sur du 3-SAT à 50 variables). Toutes parcourent toute la formule à chaque étape. On a corrigé uniquement ces trois causes, pour garder un code simple à expliquer :

| Cause de lenteur dans `dpll.py` | Correction dans `optimized.py` |
|---|---|
| `simplifier` reconstruit toute la formule à chaque affectation (O(\|F\|)) | La formule ne change jamais. Un tableau `val` et une pile `trail` des littéraux affectés ; revenir en arrière = défaire la fin de la pile. |
| `trouver_unitaire` et `trouver_pur` parcourent toute la formule | Deux littéraux surveillés par clause : quand un littéral devient faux, on ne regarde que les clauses qui le surveillent. Le littéral pur est abandonné : il ne sert à rien sur Meowdoku et coûte O(\|F\|). |
| H8 relit toute la formule à chaque décision | Les clauses entièrement positives sont mises de côté une fois ; une décision ne parcourt qu'elles. |

La recherche reste celle de DPLL : branche « vrai » puis « faux », retour arrière chronologique. Le programme est récursif, avec la limite de récursion relevée.

**Tests** (`tests/test_q6.py`, 30 tests). Lecteur DIMACS (commentaires, `%`, clauses éclatées, 0 manquant…), cas limites (formule vide, clause vide, clauses unitaires contradictoires, doublons, tautologies, variables au-delà de l'en-tête), comparaison avec la force brute, principe des tiroirs, grilles Meowdoku dans les coins, interface en ligne de commande.

**Résultats.** Sur les 160 instances du banc (timeout de 10 s, temps total d'un processus Python par instance, donc démarrage compris), les deux modes donnent toujours le même statut :

| Famille | `dpll` (résolues, temps cumulé) | `optimized` |
|---|---|---|
| 3-SAT n = 20 à 50 | 40/40, 1,8 s | 40/40, 1,3 s |
| Meowdoku aléatoire n = 5 à 10 | 40/40, 2,4 s | 40/40, 1,2 s |
| Meowdoku aléatoire n = 12 | 9/10, 20,9 s | 10/10, 0,4 s |
| Meowdoku aléatoire n = 14 | 5/10, 63,5 s | 10/10, 0,4 s |
| Meowdoku à solution plantée n = 12, 14 | 20/20, 3,1 s | 20/20, 0,8 s |

À titre d'ordre de grandeur, le temps minimal d'un processus Python est d'environ 0,03 s. Sur de grandes grilles plantées, `optimized` résout n = 30 en 0,02 s et n = 40 (graine 2) en 0,07 s.

**Limites, à dire honnêtement.** Sans apprentissage de clauses, certaines grilles restent trop dures : une grille plantée de n = 35 (graine 1) et une de n = 40 (graine 3) dépassent 30 s. Les grilles UNSAT à régions aléatoires de n ≥ 25 sont aussi hors de portée (et sont difficiles même pour MiniSat). On n'a pas non plus testé les fichiers de la compétition. Une première version en CDCL (apprentissage, VSIDS, redémarrages) existe dans l'historique git (commit `0ffdbb2`) ; on l'a abandonnée parce qu'elle était trop compliquée pour qu'on puisse l'expliquer complètement en soutenance.

## Usage des assistants IA

On a utilisé Claude (Claude Code) pour écrire une partie du code, les tests et les brouillons des notes d'analyse. Pour chaque morceau, on a relu, fait expliquer et simplifié le code jusqu'à pouvoir le défendre. Les résultats chiffrés viennent de nos propres exécutions (`results/`, `NOTES_Q2.md`, `NOTES_Q5.md`), qu'on peut relancer.
