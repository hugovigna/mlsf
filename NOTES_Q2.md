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
Instances publiques (`public-instances/`, 41 fichiers) : statut identique à `expected.json` pour les 41, et modèle vérifié clause par clause pour les SAT. Temps dans `results/q2_public_times.csv`.
- Les fichiers ont révélé des clauses écrites sur plusieurs lignes : `parse_dimacs` accumule maintenant les littéraux jusqu'au `0`.
- `tests/test_q2_2.py` : 300 formules aléatoires (≤ 8 variables) comparées à la force brute (statut et modèle) ; grilles Meowdoku décodées et validées par `is_valid`.

## 2.4 Performances (choix aléatoire, une exécution, sans timeout)
- 28 instances `public-*` sur 30 en moins de 3 s (25 en moins d'1 s).
- Plus dures : `public-12` (SAT) 65 s, `public-03` (UNSAT) 117,5 s.
- Forte variance due au choix aléatoire : `public-06` > 120 s à un lancement, 0,16 s au suivant.
- UNSAT en général plus coûteux que SAT : tout l'arbre doit être exploré.
- `dpll` recrée la formule à chaque nœud (`simplifier`, O(|F|)) : motive les heuristiques (Q4) et les structures incrémentales (Q6).
