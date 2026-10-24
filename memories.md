# Mémoire de projet (pour reprise par une autre session)

Projet MLSF : solveur SAT (DPLL) + jeu Meowdoku, partie I, en binôme, **rendu le 25/10/2026** (Edunao : rapport + tous les fichiers). Sujet : `sujet_projet.pdf` (texte extrait avec `pypdf`, pas de poppler). Consignes de travail (`AGENT.MD`) : frugalité (écrire clair, succinct, précis) et rigueur. L'utilisateur parle français et veut du code simple et intuitif, qu'il puisse expliquer en soutenance (le sujet évalue la maîtrise, pas la quantité). Rapport à rédiger **à la fin** (le matériau est dans `NOTES_*.md`). On se limite à N=M=K.

## État (par question)
- Q1 fait : `meowdoku.py` (encode/is_valid/parse_grid/write_dimacs), `generator.py`, `demo_q1.py`. Grille = liste de lignes de noms de région ; variable x_{i,j} = i*n+j+1.
- Q2 fait : `dimacs.py` (formule = set de frozenset d'entiers signés, sans le 0), `dpll.py` (`dpll_sat` = algo 1, `dpll(F, choix, stats)` = algos 2/3), `bench_q2.py` (ne fait plus que générer data/cnf/gen pour la Q5), `NOTES_Q2.md`. 2.3 validé sur `public-instances/` (41/41 conformes, temps dans results/q2_public_times.csv ; parseur corrigé pour clauses multi-lignes).
- Q3 fait : `solve_grid.py` (sortie identique à la figure 2 du sujet sur `data/grids/sujet.txt`).
- Q4 fait : `heuristics.py`, `creer(nom, F0, seed)` ; noms dans `NOMS` (H0, H1, H2s, H2d, H3d, H4d, H7s, H7d, H8). H8 = heuristique perso (plus courte clause positive).
- Q5 fait : `bench_q5.py` (compteurs via `stats`), résultats `results/q5.csv`, `results/q5_tableaux.txt`, analyse `NOTES_Q5.md`.
- Q6 fait : `sat.py` (interface imposée, modes dpll/optimized, `--output-model` ; stdout réservé au résultat, erreur d'usage = code 2), `optimized.py` (DPLL simple, même logique que dpll+H8, 3 corrections : affectation + trail avec annulation au lieu de `simplifier`, 2 littéraux surveillés au lieu de `trouver_unitaire`, clauses positives mises de côté pour H8 ; pas de littéral pur ; la version CDCL est dans le commit 0ffdbb2), `tests/test_q6.py` (30 tests). Mesures : 160 instances de data/cnf/gen en 5,4 s au total ; grilles plantées n=30 en 20 ms, mais certaines (n=35 graine 1, n=40 graine 3) dépassent 30 s faute d'apprentissage ; UNSAT à régions aléatoires n>=25 durs (aussi pour MiniSat). Pistes non faites : portefeuille sur 4 cœurs, raisonnement de comptage propre à Meowdoku (risqué : encodage des enseignants inconnu).
- Rapport (à faire en dernier) : décisions de conception, résultats, analyses, usage de l'IA à mentionner.

## Résultats clés à connaître (détails : `NOTES_Q5.md`)
- Sur Meowdoku, H2d/H3d/H4d/H7d mettent 100 % des décisions à 0 (variables presque uniquement négatives), H2d=H3d=H7d exactement ; H8 (région la plus contrainte, valeur 1) domine, statique très inférieur au dynamique. Sur 3-SAT aléatoire les dynamiques sont 5 à 10 fois meilleurs que H0/H1 et H4d (MOMS) est la meilleure.
- Pistes pour Q6 : H8 comme choix de branchement + structures incrémentales (comptage de littéraux surveillés, pas de recopie de la formule à chaque nœud : `simplifier` est O(|F|) par nœud), propagation itérative (limite de récursion), éventuellement apprentissage de clauses.

## Conventions et pièges
- Tests : `python -m unittest discover -s tests -t .` (19 tests). Scratchpad de session hors dépôt.
- Ne pas mettre de messages de debug sur stdout dans `sat.py` (stderr uniquement).
- Les moyennes de `bench_q5.py` (décisions...) sont calculées sur les instances résolues seulement ; une seule exécution par cas.
- Historique git : un commit par grande étape, le dépôt distant est `origin` (GitHub, branche `main`).
