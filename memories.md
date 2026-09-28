# Mémoire de projet (pour reprise par une autre session)

Projet MLSF : solveur SAT (DPLL) + jeu Meowdoku, partie I, en binôme, **rendu le 25/10/2026** (Edunao : rapport + tous les fichiers). Sujet : `sujet_projet.pdf` (texte extrait avec `pypdf`, pas de poppler). Consignes de travail (`AGENT.MD`) : frugalité (écrire clair, succinct, précis) et rigueur. L'utilisateur parle français et veut du code simple et intuitif, qu'il puisse expliquer en soutenance (le sujet évalue la maîtrise, pas la quantité). Rapport à rédiger **à la fin** (le matériau est dans `NOTES_*.md`). On se limite à N=M=K.

## État (par question)
- Q1 fait : `meowdoku.py` (encode/is_valid/parse_grid/write_dimacs), `generator.py`, `demo_q1.py`. Grille = liste de lignes de noms de région ; variable x_{i,j} = i*n+j+1.
- Q2 fait : `dimacs.py` (formule = set de frozenset d'entiers signés, sans le 0), `dpll.py` (`dpll_sat` = algo 1, `dpll(F, choix, stats)` = algos 2/3), `bench_q2.py`, `NOTES_Q2.md`. **2.3 incomplet : les fichiers DIMACS des enseignants n'ont pas été fournis** (à mettre dans `data/cnf/` puis `python bench_q2.py run`).
- Q3 fait : `solve_grid.py` (sortie identique à la figure 2 du sujet sur `data/grids/sujet.txt`).
- Q4 fait : `heuristics.py`, `creer(nom, F0, seed)` ; noms dans `NOMS` (H0, H1, H2s, H2d, H3d, H4d, H7s, H7d, H8). H8 = heuristique perso (plus courte clause positive).
- Q5 fait : `bench_q5.py` (compteurs via `stats`), résultats `results/q5.csv`, `results/q5_tableaux.txt`, analyse `NOTES_Q5.md`.
- **Q6 à faire** : `sat.py` imposé (`python sat.py inst.cnf [--mode dpll|optimized] [--output-model]`, sortie `s SATISFIABLE`/`s UNSATISFIABLE` + `v ... 0`, rien d'autre sur stdout ; Python 3.12, 4 CPU, 8 Gio, 60 s par instance, classement au nb d'instances résolues puis temps).
- Rapport (à faire en dernier) : décisions de conception, résultats, analyses, usage de l'IA à mentionner.

## Résultats clés à connaître (détails : `NOTES_Q5.md`)
- Sur Meowdoku, H2d/H3d/H4d/H7d mettent 100 % des décisions à 0 (variables presque uniquement négatives), H2d=H3d=H7d exactement ; H8 (région la plus contrainte, valeur 1) domine, statique très inférieur au dynamique. Sur 3-SAT aléatoire les dynamiques sont 5 à 10 fois meilleurs que H0/H1 et H4d (MOMS) est la meilleure.
- Pistes pour Q6 : H8 comme choix de branchement + structures incrémentales (comptage de littéraux surveillés, pas de recopie de la formule à chaque nœud : `simplifier` est O(|F|) par nœud), propagation itérative (limite de récursion), éventuellement apprentissage de clauses.

## Conventions et pièges
- Tests : `python -m unittest discover -s tests -t .` (19 tests). Scratchpad de session hors dépôt.
- Ne pas mettre de messages de debug sur stdout dans `sat.py` (stderr uniquement).
- Les moyennes de `bench_q5.py` (décisions...) sont calculées sur les instances résolues seulement ; une seule exécution par cas.
- Historique git : un commit par grande étape, le dépôt distant est `origin` (GitHub, branche `main`).
