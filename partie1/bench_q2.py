"""Génération des instances de test (utilisées par bench_q5.py).

python bench_q2.py                 # écrit des instances dans data/cnf/gen/
"""
import os
import random

import generator
import meowdoku

DOSSIER_GEN = "data/cnf/gen"


def gen():
    os.makedirs(DOSSIER_GEN, exist_ok=True)
    rng = random.Random(0)
    for n in (20, 30, 40, 50):                       # 3-SAT aléatoire, ratio 4.26 (seuil, mélange SAT/UNSAT)
        for k in range(10):
            cl = [[rng.choice([-1, 1]) * v for v in rng.sample(range(1, n + 1), 3)] for _ in range(round(4.26 * n))]
            meowdoku.write_dimacs(f"{DOSSIER_GEN}/3sat_n{n}_{k}.cnf", n, cl)
    for n in (5, 6, 8, 10, 12, 14):
        for k in range(10):
            g, _ = generator.generate(n, k)          # grille avec solution plantée : SAT
            meowdoku.write_dimacs(f"{DOSSIER_GEN}/meow-sat_n{n}_{k}.cnf", n * n, meowdoku.encode(g))
            # graines au hasard (sans garantie de solution) : SAT ou UNSAT
            cases = rng.sample([(i, j) for i in range(n) for j in range(n)], n)
            reg = generator.faire_grossir(n, cases, rng)
            nom = generator.noms(n)
            g = [[nom[x] for x in ligne] for ligne in reg]
            meowdoku.write_dimacs(f"{DOSSIER_GEN}/meow-alea_n{n}_{k}.cnf", n * n, meowdoku.encode(g))


if __name__ == "__main__":
    gen()
