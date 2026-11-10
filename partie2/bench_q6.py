"""Q6.3, 6.4, 6.6 : compare les modèles de Meowdoku sur des grilles de taille croissante.

    python bench_q6.py [timeout=60] [processus=4] [tailles=6,8,10,12,14] [graines=5]

Pour chaque grille (générateur de la partie I, graines 0, 1, ...), chaque modèle et chaque
solveur, on lance `python csp.py modele.csp --solve --stats` dans un processus à part (pour
pouvoir l'interrompre au temps limite) et on relève :
  - la taille de la FNC (variables, clauses) ;
  - le temps de compilation (analyse + encodage) et le temps de résolution, donnés par --stats ;
  - le statut (SAT, UNSAT, TIMEOUT). Une solution SAT est relue puis vérifiée par le
    vérificateur indépendant meow_csp.est_valide : la colonne `ok` le dit.
Résultat : results/q6.csv (une ligne par exécution) et un résumé (médianes) affiché à la fin.
"""
import csv
import os
import re
import statistics
import subprocess
import sys
import time
from multiprocessing import Pool

import meow_csp
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "partie1"))
import generator

MODELES = ("1", "2", "2alo")
SOLVEURS = ("optimized", "dpll")
DOSSIER = os.path.join("results", "q6_modeles")


def preparer(tailles, graines):
    """Écrit les modèles .csp (un par grille et par modèle) ; renvoie la liste des tâches."""
    os.makedirs(DOSSIER, exist_ok=True)
    taches = []
    for n in tailles:
        for graine in range(graines):
            grille, _ = generator.generate(n, graine)
            zones = list(dict.fromkeys(z for ligne in grille for z in ligne))
            texte = meow_csp.texte_grille(zones, grille)
            for modele in MODELES:
                chemin = os.path.join(DOSSIER, f"n{n}_g{graine}_m{modele}.csp")
                with open(chemin, "w") as f:
                    f.write(meow_csp.modele(texte, modele))
                for solveur in SOLVEURS:
                    taches.append((n, graine, modele, solveur, chemin, texte))
    return taches


def lancer(tache_timeout):
    (n, graine, modele, solveur, chemin, texte), timeout = tache_timeout
    cmd = [sys.executable, "csp.py", chemin, "--solve", "--stats", "--solver", solveur]
    t0 = time.perf_counter()
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return [n, graine, modele, solveur, "TIMEOUT", "", "", "", "", timeout, ""]
    total = time.perf_counter() - t0
    stats = re.search(r"vars=(\d+) clauses=(\d+) analyse=([\d.]+)s encode=([\d.]+)s", p.stderr)
    resolution = re.search(r"solve=([\d.]+)s", p.stderr)
    sortie = p.stdout.splitlines()
    if p.returncode != 0 or not sortie or not stats:
        return [n, graine, modele, solveur, "ERREUR", "", "", "", "", total, ""]
    ok = ""
    if sortie[0] == "s SATISFIABLE":
        zones, grille = meow_csp.lire_grille(texte)
        valeurs = [tuple(l.split(" = ")) for l in sortie[1:]]
        ok = meow_csp.est_valide(grille, meow_csp.chats_depuis_solution(valeurs, zones))
    statut = "SAT" if sortie[0] == "s SATISFIABLE" else "UNSAT"
    compil = float(stats.group(3)) + float(stats.group(4))
    return [n, graine, modele, solveur, statut, stats.group(1), stats.group(2),
            f"{compil:.3f}", resolution.group(1), f"{total:.3f}", ok]


def resume(lignes):
    """Médiane du temps de résolution (hors timeouts : comptés à part) par taille/modèle/solveur."""
    groupes = {}
    for n, graine, modele, solveur, statut, nv, nc, compil, res, total, ok in lignes:
        groupes.setdefault((n, modele, solveur), []).append((statut, nv, nc, compil, res))
    print(f"{'n':>3} {'modèle':>7} {'solveur':>10} {'vars':>6} {'clauses':>8} "
          f"{'compil(s)':>10} {'résolution(s)':>14} {'timeouts':>9}")
    for (n, modele, solveur), g in sorted(groupes.items()):
        fait = [x for x in g if x[0] in ("SAT", "UNSAT")]
        to = len(g) - len(fait)
        if fait:
            med = lambda k: statistics.median(float(x[k]) for x in fait)
            print(f"{n:>3} {modele:>7} {solveur:>10} {int(med(1)):>6} {int(med(2)):>8} "
                  f"{med(3):>10.3f} {med(4):>14.3f} {to:>9}")
        else:
            print(f"{n:>3} {modele:>7} {solveur:>10} {'-':>6} {'-':>8} {'-':>10} {'-':>14} {to:>9}")


if __name__ == "__main__":
    timeout = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    proc = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    tailles = [int(x) for x in sys.argv[3].split(",")] if len(sys.argv) > 3 else [6, 8, 10, 12, 14]
    graines = int(sys.argv[4]) if len(sys.argv) > 4 else 5
    taches = preparer(tailles, graines)
    with Pool(proc) as pool:
        lignes = pool.map(lancer, [(t, timeout) for t in taches], chunksize=1)
    with open(os.path.join("results", "q6.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["n", "graine", "modele", "solveur", "statut", "vars", "clauses",
                    "compilation_s", "resolution_s", "total_s", "ok"])
        w.writerows(lignes)
    resume(lignes)
    mauvais = [l for l in lignes if l[4] == "ERREUR" or l[10] is False]
    print("\nSolutions toutes valides." if not mauvais else f"\nPROBLEME : {mauvais}")
