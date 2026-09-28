# Notes Q2

## 2.1 Lecture DIMACS (`dimacs.py`)
- Formule = `set` de `frozenset` d'entiers signés, un par ligne de clause, sans le 0 final ; clause vide = `frozenset()`.
- Conséquence : les clauses en double et l'ordre des littéraux disparaissent (formule équivalente ; `len(F)` peut être < nombre annoncé dans `p cnf`).
- Les lignes `c` sont ignorées, la lecture s'arrête à une ligne `%` (fin SATLIB).

## 2.2 DPLL (`dpll.py`)
- `dpll_sat` = algorithme 1, `dpll` = algorithme 2 (valuation = ensemble de littéraux vrais ; `p<-0` codé `-p`).
- Ordre : clause vide, formule vide, unitaire, pur, décision. Décision par `choix(F)` (défaut : H0 aléatoire), interchangeable pour la Q4.
- `F[l<-1]` recrée un nouvel ensemble à chaque appel : coût O(|F|) par nœud, pas de structure incrémentale (à améliorer en Q6).

## 2.3 Validation
Fichiers des enseignants : **pas encore disponibles** dans le dépôt. `python bench_q2.py run <dossier>` les traitera dès qu'ils seront placés dans `data/cnf/`.

En attendant :
- `tests/test_q2_2.py` : 300 formules aléatoires (≤ 8 variables) comparées à la force brute (statut SAT/UNSAT, et modèle : cohérent et satisfait toutes les clauses) ; grilles Meowdoku décodées et validées par `is_valid`.
- `bench_q2.py` sur 140 instances générées (`bench_q2.py gen`) : 3-SAT aléatoire au seuil (ratio 4,26), Meowdoku avec solution plantée (SAT), Meowdoku à graines aléatoires (SAT ou UNSAT). Vérifié à chaque instance : algorithmes 1 et 2 donnent le même statut, et le modèle de l'algorithme 2 satisfait la formule. Résultat : 0 erreur.
- Limite : sur ces instances plus grandes, un UNSAT n'est pas vérifié indépendamment (la force brute n'est faite que sur les petits cas du test unitaire).

## 2.4 Performances (temps en s, choix aléatoire, timeout 20 s, 1 exécution par instance)

| famille | n | SAT | UNSAT | t1 moy | t2 moy | t2 max |
|---|---|---|---|---|---|---|
| 3sat_n20 | 10 | 7 | 3 | 0,001 | 0,001 | 0,002 |
| 3sat_n50 | 10 | 8 | 2 | 0,041 | 0,040 | 0,165 |
| meow-sat_n8 | 10 | 10 | 0 | 0,004 | 0,005 | 0,016 |
| meow-sat_n12 | 10 | 10 | 0 | 0,630 | 0,023 | 0,058 |
| meow-alea_n8 | 10 | 3 | 7 | 0,007 | 0,004 | 0,010 |
| meow-alea_n10 | 10 | 4 | 6 | 0,187 | 0,152 | 0,550 |
| meow-alea_n12 | 10 | 5 | 5 | 2,753 | 3,543 | 16,654 |

Aucun timeout. (Tableau complet : `python bench_q2.py run data/cnf/gen`.)

Observations :
- Algorithmes 1 et 2 : même exploration, donc mêmes ordres de grandeur ; les écarts (ex. `meow-sat_n12`, 0,63 vs 0,023) viennent du tirage aléatoire différent entre les deux exécutions, pas de l'algorithme. Une seule exécution par instance : l'écart entre t1 et t2 n'est pas interprétable.
- Forte variance due au choix aléatoire (`meow-alea_n12` : moyenne 3,5 s, max 16,7 s).
- Les grilles UNSAT (graines aléatoires) coûtent nettement plus que les SAT à taille égale : pour prouver l'insatisfiabilité, tout l'arbre doit être exploré, alors qu'une grille SAT trouve une solution avant.
- Le coût croît vite avec N sur Meowdoku (clauses en O(N^4) et arbre de recherche), ce qui motive les heuristiques (Q4) et des structures incrémentales (Q6).
