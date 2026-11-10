"""Q2/Q6 : lance `python sat.py <instance> --mode <mode> --output-model` sur les instances
publiques et sur les grilles Meowdoku générées (data/cnf/gen/meow-*), avec le temps limite du sujet.

python bench_q6.py [timeout=60] [processus=4]   -> results/public.csv, results/meowdoku.csv
Le temps est le temps réel du processus (démarrage de Python compris). Le modèle d'une instance SAT
est vérifié clause par clause ; une réponse fausse est signalée dans la colonne `ok`.
"""
import csv
import glob
import json
import os
import subprocess
import sys
import time
from multiprocessing import Pool

from optimized import lire

MODES = ("dpll", "optimized")


def lancer(args):
    fic, mode, timeout = args
    t0 = time.perf_counter()
    try:
        p = subprocess.run([sys.executable, "sat.py", fic, "--mode", mode, "--output-model"],
                           capture_output=True, text=True, timeout=timeout)
        out = p.stdout
    except subprocess.TimeoutExpired:
        return fic, mode, "TIMEOUT", timeout, None
    t = time.perf_counter() - t0
    lignes = out.split("\n")
    if lignes[0] == "s UNSATISFIABLE":
        return fic, mode, "UNSAT", t, None
    if lignes[0] != "s SATISFIABLE" or len(lignes) < 2:
        return fic, mode, "ERREUR", t, None
    modele = {int(x) for x in lignes[1].split()[1:-1]}
    _, clauses = lire(fic)
    ok = all(any(x in modele for x in c) for c in clauses)
    return fic, mode, "SAT", t, ok


def ecrire(chemin, resultats, attendu):
    par = {}
    for fic, mode, st, t, ok in resultats:
        par.setdefault(fic, {})[mode] = (st, t, ok)
    with open(chemin, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["instance", "attendu", "dpll_statut", "dpll_s", "optimized_statut", "optimized_s", "ok"])
        for fic in sorted(par):
            a = par[fic]
            ref = attendu(fic, a)
            ok = all(a[m][0] == "TIMEOUT" or (a[m][0] == ref and a[m][2] in (None, True)) for m in MODES)
            w.writerow([os.path.basename(fic), ref] + [x for m in MODES for x in (a[m][0], f"{a[m][1]:.3f}")] + [ok])


if __name__ == "__main__":
    timeout = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    proc = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    os.makedirs("results", exist_ok=True)
    attendu = json.load(open("public-instances/expected.json"))
    pub = sorted(glob.glob("public-instances/instances/*.cnf"))
    meow = sorted(glob.glob("data/cnf/gen/meow-*.cnf"))
    with Pool(proc) as p:
        res_pub = p.map(lancer, [(f, m, timeout) for f in pub for m in MODES], chunksize=1)
        res_meow = p.map(lancer, [(f, m, timeout) for f in meow for m in MODES], chunksize=1)

    def ref_pub(fic, a):
        return attendu[os.path.basename(fic)]

    def ref_meow(fic, a):                    # statut commun des deux modes quand ils terminent
        s = {a[m][0] for m in MODES} - {"TIMEOUT"}
        return s.pop() if len(s) == 1 else "?"

    ecrire("results/public.csv", res_pub, ref_pub)
    ecrire("results/meowdoku.csv", res_meow, ref_meow)
