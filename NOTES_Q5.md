# Notes Q4-Q5 : heuristiques et comparaison

Reproduire : `python bench_q2.py gen && python bench_q5.py data/cnf/gen 10` (résultats : `results/q5.csv`, `results/q5_tableaux.txt`).

## Protocole
- 160 instances (`data/cnf/gen`), 9 variantes (H0, H1, H2s/d, H3d, H4d, H7s/d, H8), timeout 10 s CPU, **une exécution par couple (instance, heuristique)**, H0 avec la graine 0.
- Familles : `3sat_n*` (3-SAT aléatoire, ratio 4,26), `meow-sat_n*` (grille à solution plantée, donc SAT), `meow-alea_n*` (graines de régions aléatoires : SAT ou UNSAT).
- Le statut d'une instance est celui trouvé par les heuristiques qui terminent (accord vérifié). Les modèles SAT sont vérifiés.
- Colonnes : décisions, retours arrière (2e branche explorée), propagations unitaires, littéraux purs, temps CPU (timeout compté 2 x 10 s), `%heur` = part du CPU passée dans l'heuristique.
- Attention : décisions/retours/unitaires sont des moyennes **sur les instances résolues seulement** (biais quand il y a des timeouts, à lire avec la colonne TO). Effectifs par cellule : 2 à 10 instances, donc tendances, pas de test statistique.

## Résultats principaux (extraits de `results/q5_tableaux.txt`)

Décisions moyennes, instances SAT (grilles à solution plantée) :

| | H0 | H1 | H2s | H2d | H3d | H4d | H7s | H7d | H8 |
|---|---|---|---|---|---|---|---|---|---|
| meow-sat_n10 | 17 | 14 | 74 | 88 | 88 | 82 | 74 | 88 | 8 |
| meow-sat_n12 | 1842 | 43 | 3124 | 242 | 242 | 185 | 3124 | 242 | 12 |
| meow-sat_n14 | 3204 | 2873 | 1215 (1 TO) | 812 | 812 | 668 | 1215 (1 TO) | 812 | 24 |

CPU moyen (s), instances UNSAT de `meow-alea_n12` (5 UNSAT sur 10 ; timeout compté 20 s) : H0 8,2 (2 TO), H1 4,5 (1 TO), H2d/H3d/H4d/H7d 8,3 (2 TO), **H8 0,11** (0 TO). Pour `meow-alea_n14` (7 UNSAT sur 10), nombre résolu : H8 7/7, H1 4/7, H0 2/7, H2s/d, H3d, H4d, H7s/d 1/7. L'unique instance résolue par ces dernières l'est sans aucune décision (contradiction par propagation).

3-SAT (n=50, SAT) : décisions H0 177, H1 190, H2d 26, H3d 36, **H4d 16**, H7d 26, H8 30.

## Analyse

**1. Les heuristiques génériques H2-H7 sont piégées par la structure de Meowdoku.**
Chaque variable est positive une seule fois (clause de région) et négative dans de nombreux conflits binaires. Vérification (5 grilles n=12) : H2d, H3d, H4d et H7d mettent **100 % de leurs décisions à 0**, sur la case la plus conflictuelle ; H2d, H3d et H7d produisent exactement la même séquence de décisions (résultats identiques dans le tableau). Mettre une case à 0 n'en retire qu'une candidate à sa région et ne déclenche aucune propagation forte ; c'est l'inverse du bon pari (case à 1 : élimine toutes les cases en conflit). Résultat : sur Meowdoku ces heuristiques font *plus* de décisions que H0 et H1 pour N ≤ 10 (n=10 SAT : 88 contre 17 et 14).
Prédiction initiale partiellement fausse : je pensais que la pondération de Jeroslow-Wang (H7) s'en sortirait mieux ; elle est ici identique à H2/H3 parce que les clauses binaires négatives dominent tous les poids. Seule H4d (compte limité aux clauses minimales) fait un peu mieux, de 7 à 25 % en décisions (88 → 82, 242 → 185, 812 → 668).

**2. Sur une instance non structurée (3-SAT), l'intuition classique est confirmée.** Les heuristiques dynamiques divisent les décisions par 5 à 10 par rapport à H0/H1, et H4d (MOMS) est la meilleure en décisions, cohérent avec l'idée que les petites clauses (ici les clauses ternaires devenues binaires) sont les plus contraignantes. Même heuristique, deux problèmes : le gain dépend de la structure, pas seulement de l'heuristique.

**3. H1 (première variable libre, valeur 1) est meilleure que prévu sur Meowdoku mais irrégulière.** L'ordre des variables est ligne par ligne, donc H1 place un chat par ligne en avançant, ce qui ressemble à la résolution classique des n-reines. Elle est bonne à n=12 (43 décisions) mais mauvaise à n=14 (2873) : elle dépend fortement de la disposition des régions.

**4. H8 (plus courte clause positive) domine sur Meowdoku.** Elle mène le calcul région par région en choisissant la région qui a le moins de candidats (« premier échec ») et met la case à 1 (forte propagation). Décisions : 8 (n=10), 12 (n=12), 24 (n=14) sur les grilles SAT ; sur les UNSAT de `meow-alea_n10` : 3 contre 430 à 6 600 pour les autres. C'est la seule qui résout tous les UNSAT de n=14 dans le temps imparti. Sur le 3-SAT elle reste au niveau des autres dynamiques (elle se rabat sur H7d faute de clause positive). Limite : elle exploite la structure de l'encodage (les clauses « au moins un chat » sont les seules clauses positives) ; ce n'est pas une heuristique générique.

**5. Statique contre dynamique.** Sur Meowdoku, le statique est bien pire : n=12 SAT, H2s 3124 décisions et 0,77 s contre H2d 242 décisions et 0,11 s (idem H7s/H7d). Le classement initial ne tient pas compte des variables déjà fixées, donc il dirige vers des cases déjà éliminées. Le coût du recalcul est réel (part de CPU dans l'heuristique : 45-55 % en dynamique contre 24-28 % en statique et 10-17 % pour H0), mais il est largement compensé. Sur le 3-SAT (n=40-50), le dynamique gagne un peu en décisions (H2d 8 contre H2s 12, sur SAT) mais le CPU est quasi identique (0,001 s) : gain et coût s'équilibrent.

**6. Coût des heuristiques.** Le calcul est en O(|F|) par décision, comme la simplification. Il représente jusqu'à 55 % du CPU sur les grilles SAT, mais seulement 5-15 % sur les UNSAT, où la propagation unitaire domine (il y a beaucoup plus d'unitaires que de décisions). Il n'y a aucun littéral pur sur Meowdoku : chaque variable apparaît dans les deux polarités.

**7. SAT contre UNSAT.** Sur les UNSAT, décisions = retours arrière : toute décision explore ses deux branches, donc l'arbre est le même quelle que soit la valeur choisie en premier ; seul l'ordre des variables compte. Sur `meow-alea_n10` UNSAT (décisions moyennes) : H0 431, H4d 838, H2d/H3d/H7d 1119, H1 1807, statiques 6632, **H8 3**. Le hasard (H0) fait donc mieux que les heuristiques H2-H7 génériques ; H8, qui choisit la bonne *variable* (la région la plus contrainte), gagne un facteur 100 à 1000.

## Limites
- Une seule exécution par cas et H0 avec une seule graine : les écarts de moins d'un facteur 2 ne sont pas significatifs.
- Les grilles `meow-alea` sont des partitions tirées au hasard (pas des grilles « réelles » de jeu), majoritairement UNSAT à partir de n=12.
- Les grilles `meow-sat` ne sont pas à solution unique.
- Instances du 3-SAT petites (n ≤ 50) : le temps est dominé par le bruit de mesure.
- Fichiers des enseignants non testés (non disponibles).
