"""Q2.3/2.4 : génération d'instances et validation/mesure de DPLL (versions 1 et 2).

python bench_q2.py gen             # écrit des instances dans data/cnf/gen/
python bench_q2.py run [dossier]   # défaut : data/cnf (récursif)
"""
import glob
import os
import random
import signal
import sys
import time
from collections import defaultdict

import dpll
import generator
import meowdoku
from dimacs import parse_dimacs

DOSSIER_GEN = "data/cnf/gen"
TIMEOUT = 20


def gen():
    os.makedirs(DOSSIER_GEN, exist_ok=True)
    rng = random.Random(0)
    for n in (20, 30, 40, 50):                       # 3-SAT aléatoire, ratio 4.26 (seuil, mélange SAT/UNSAT)
        for k in range(10):
            cl = [[rng.choice([-1, 1]) * v for v in rng.sample(range(1, n + 1), 3)] for _ in range(round(4.26 * n))]
            meowdoku.write_dimacs(f"{DOSSIER_GEN}/3sat_n{n}_{k}.cnf", n, cl)
    for n in (5, 6, 8, 10, 12):
        for k in range(10):
            g, _ = generator.generate(n, k)          # grille avec solution plantée : SAT
            meowdoku.write_dimacs(f"{DOSSIER_GEN}/meow-sat_n{n}_{k}.cnf", n * n, meowdoku.encode(g))
            # graines au hasard (sans garantie de solution) : SAT ou UNSAT
            cases = rng.sample([(i, j) for i in range(n) for j in range(n)], n)
            reg = generator.faire_grossir(n, cases, rng)
            nom = generator.noms(n)
            g = [[nom[x] for x in ligne] for ligne in reg]
            meowdoku.write_dimacs(f"{DOSSIER_GEN}/meow-alea_n{n}_{k}.cnf", n * n, meowdoku.encode(g))


class Timeout(Exception):
    pass


def chrono(f, *args):
    def h(*_):
        raise Timeout
    signal.signal(signal.SIGALRM, h)
    signal.alarm(TIMEOUT)
    t = time.perf_counter()
    try:
        r = f(*args)
    except Timeout:
        return None, TIMEOUT
    finally:
        signal.alarm(0)
    return r, time.perf_counter() - t


def run(dossier):
    fichiers = sorted(glob.glob(f"{dossier}/**/*.cnf", recursive=True))
    if not fichiers:
        sys.exit(f"aucun .cnf dans {dossier}")
    stats = defaultdict(lambda: defaultdict(list))
    erreurs = 0
    for fic in fichiers:
        fam = os.path.basename(fic).split("_n")[0] + "_n" + os.path.basename(fic).split("_n")[-1].split("_")[0] \
            if "_n" in os.path.basename(fic) else "divers"
        _, F = parse_dimacs(fic)
        rng = random.Random(1)
        choix = lambda F: dpll.choix_aleatoire(F, rng)
        s1, t1 = chrono(dpll.dpll_sat, F, choix)
        r2, t2 = chrono(dpll.dpll, F, choix)
        st = stats[fam]
        st["t1"].append(t1)
        st["t2"].append(t2)
        if s1 is None or r2 is None:
            st["timeout"].append(fic)
            continue
        s2, v = r2
        ok = s1 == s2 and (not s2 or (all(-l not in v for l in v) and all(c & v for c in F)))
        st["sat" if s2 else "unsat"].append(fic)
        if not ok:
            erreurs += 1
            print("ERREUR", fic, s1, s2)
    print(f"{'famille':<16}{'n':>4}{'SAT':>5}{'UNSAT':>6}{'timeout':>8}{'t1 moy':>9}{'t2 moy':>9}{'t2 max':>9}")
    for fam, st in stats.items():
        n = len(st["t1"])
        print(f"{fam:<16}{n:>4}{len(st['sat']):>5}{len(st['unsat']):>6}{len(st['timeout']):>8}"
              f"{sum(st['t1'])/n:>9.3f}{sum(st['t2'])/n:>9.3f}{max(st['t2']):>9.3f}")
    print(f"{len(fichiers)} instances, {erreurs} erreur(s)")


if __name__ == "__main__":
    if sys.argv[1:2] == ["gen"]:
        gen()
    elif sys.argv[1:2] == ["run"]:
        run(sys.argv[2] if len(sys.argv) > 2 else "data/cnf")
    else:
        sys.exit(__doc__)
