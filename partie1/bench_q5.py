"""Q5 : compare les heuristiques sur un dossier d'instances CNF.

python bench_q5.py [dossier=data/cnf/gen] [timeout=10]   -> results/q5.csv + tableaux
Par instance et heuristique : statut, decisions, retours, unitaires, purs, temps CPU,
part du temps CPU passee dans l'heuristique.
"""
import csv
import glob
import os
import signal
import sys
import time
from collections import Counter, defaultdict
from multiprocessing import Pool

import dpll
import heuristics
from dimacs import parse_dimacs


class Timeout(Exception):
    pass


def une_execution(args):
    fic, nom, timeout = args
    _, F = parse_dimacs(fic)
    choix = heuristics.creer(nom, F)
    t_heur = [0.0]

    def choix_mesure(F):
        t = time.process_time()
        r = choix(F)
        t_heur[0] += time.process_time() - t
        return r

    def h(*_):
        raise Timeout
    signal.signal(signal.SIGALRM, h)
    st = Counter()
    signal.alarm(timeout)
    t0 = time.process_time()
    try:
        sat, v = dpll.dpll(F, choix_mesure, st)
        statut = "SAT" if sat else "UNSAT"
        if sat:
            assert all(-l not in v for l in v) and all(c & v for c in F), f"modele invalide {fic} {nom}"
    except Timeout:
        statut = "TIMEOUT"
    finally:
        signal.alarm(0)
    cpu = time.process_time() - t0
    return dict(instance=os.path.basename(fic), nom=nom, statut=statut, decisions=st["decisions"],
                retours=st["retours"], unitaires=st["unitaires"], purs=st["purs"], cpu=cpu,
                ratio_heur=t_heur[0] / cpu if cpu else 0)


def famille(instance):
    return instance.rsplit("_", 1)[0]


def tableaux(lignes, timeout):
    # statut de reference d'une instance = celui trouve par une heuristique qui termine
    ref = {}
    for r in lignes:
        if r["statut"] != "TIMEOUT":
            assert ref.setdefault(r["instance"], r["statut"]) == r["statut"], f"desaccord {r['instance']}"
    g = defaultdict(list)
    for r in lignes:
        g[(famille(r["instance"]), ref.get(r["instance"], "?"), r["nom"])].append(r)
    print(f"{'famille':<15}{'st':<6}{'heur':<5}{'res':>5}{'TO':>4}{'decis':>10}{'retours':>10}{'unit':>10}{'pur':>8}"
          f"{'cpu(s)':>9}{'%heur':>7}")
    for (fam, st, nom), rs in sorted(g.items()):
        ok = [r for r in rs if r["statut"] != "TIMEOUT"]
        to = len(rs) - len(ok)
        m = lambda k: sum(r[k] for r in ok) / len(ok) if ok else float("nan")
        cpu = (sum(r["cpu"] for r in ok) + to * 2 * timeout) / len(rs)   # timeout compte 2x
        print(f"{fam:<15}{st:<6}{nom:<5}{len(ok):>5}{to:>4}{m('decisions'):>10.1f}{m('retours'):>10.1f}"
              f"{m('unitaires'):>10.1f}{m('purs'):>8.1f}{cpu:>9.3f}{100 * m('ratio_heur'):>7.1f}")


if __name__ == "__main__":
    dossier = sys.argv[1] if len(sys.argv) > 1 else "data/cnf/gen"
    timeout = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    fichiers = sorted(glob.glob(f"{dossier}/**/*.cnf", recursive=True))
    taches = [(f, nom, timeout) for f in fichiers for nom in heuristics.NOMS]
    with Pool() as p:
        lignes = p.map(une_execution, taches, chunksize=1)
    os.makedirs("results", exist_ok=True)
    with open("results/q5.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(lignes[0]))
        w.writeheader()
        w.writerows(lignes)
    tableaux(lignes, timeout)
