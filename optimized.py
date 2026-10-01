"""Solveur optimisé (Q6) : CDCL (Conflict-Driven Clause Learning), en Python pur.

Différences avec le DPLL de la Q2 (dpll.py), qui recopie la formule à chaque nœud :
  1. Pas de recopie : une seule affectation partielle `val`, modifiée puis défaite.
     On garde la *trace* (`trail`), la liste des littéraux rendus vrais dans l'ordre ;
     revenir en arrière = dépiler la trace.
  2. Propagation unitaire paresseuse :
     - clauses binaires (a ∨ b) : listes d'implications (¬a => b, ¬b => a). Sur Meowdoku
       presque toutes les clauses sont binaires (conflits entre deux cases) ;
     - clauses de taille >= 3 : deux littéraux surveillés. Une clause n'est examinée que
       quand l'un de ses deux littéraux surveillés devient faux ; tant que les deux ne
       sont pas faux, elle ne peut être ni unitaire ni fausse.
  3. Apprentissage : à chaque conflit, on déduit par résolution une nouvelle clause
     (schéma 1-UIP), conséquence logique de la formule, qui interdit de refaire la même
     erreur ; puis on remonte directement au niveau où cette clause devient unitaire
     (retour arrière non chronologique), au lieu d'essayer l'autre branche.
  4. Choix de variable VSIDS : chaque variable a une activité, augmentée quand elle
     participe à un conflit, avec une décroissance exponentielle des anciennes valeurs
     (on divise par 0,95 l'incrément au lieu de multiplier toutes les activités).
     On décide sur la variable libre la plus active (tas binaire).
  5. Sauvegarde de phase : une variable reprend la dernière valeur qu'elle avait.
  6. Redémarrages (suite de Luby) : on repart du niveau 0 en gardant clauses apprises,
     activités et phases ; évite de rester coincé dans une mauvaise partie de l'arbre.
  7. Réduction : on supprime régulièrement la moitié des clauses apprises les moins
     utiles (LBD élevé = nombre de niveaux de décision distincts dans la clause).

Correction : les clauses apprises sont des conséquences logiques (résolution), donc les
ajouter ou les supprimer ne change pas l'ensemble des modèles. UNSAT n'est renvoyé que
si un conflit survient au niveau 0 (sans aucune décision). SAT n'est renvoyé que quand
toutes les variables sont affectées sans conflit, donc toutes les clauses sont vraies.

Représentation : littéraux DIMACS signés (k = x_k, -k = ¬x_k). Les tableaux indexés par
littéral ont 2n+1 cases : t[l] pour l > 0 (cases 1..n) et t[-l] = t[2n+1-l] pour l < 0
(cases n+1..2n, grâce aux indices négatifs de Python). Ainsi pas de calcul d'indice.
"""
from heapq import heapify, heappop, heappush


def lire(path):
    """Lit un fichier DIMACS CNF ; renvoie (nb_vars, clauses), clauses = listes d'entiers
    sans le 0 final. Tolérant : commentaires n'importe où, espaces et tabulations, fins de
    ligne Windows, plusieurs clauses par ligne ou une clause sur plusieurs lignes, dernier 0
    manquant, fin '%' (format SATLIB), variables au-delà de l'en-tête."""
    n = 0
    mots = []
    with open(path, "rb") as f:                  # binaire : plus rapide que le texte
        for ligne in f:
            ligne = ligne.lstrip()
            if not ligne or ligne[0] == 99:        # ligne vide ou 'c' (commentaire)
                continue
            if ligne[0] == 112:                     # 'p cnf <nb_vars> <nb_clauses>'
                n = int(ligne.split()[2])
                continue
            if ligne[0] == 37:                      # '%' : fin de fichier SATLIB
                break
            mots.append(ligne)
    # Le 0 est le seul séparateur de clauses : on lit donc un flot d'entiers, sans
    # tenir compte des fins de ligne.
    clauses = []
    c = []
    for x in map(int, b" ".join(mots).split()):
        if x:
            c.append(x)
        else:
            clauses.append(c)
            c = []
    if c:                                           # dernière clause sans 0
        clauses.append(c)
    for c in clauses:                               # en-tête sous-estimé : on corrige
        for x in c:
            if x > n or -x > n:
                n = abs(x)
    return n, clauses


def luby(i):
    """i-ème terme (i >= 1) de la suite de Luby : 1 1 2 1 1 2 4 1 1 2 1 1 2 4 8 ...
    Si i = 2^k - 1, le terme vaut 2^(k-1) ; sinon on se ramène au début de la suite en
    retirant le plus grand bloc complet 2^(k-1) - 1 qui précède i."""
    k = 1
    while (1 << k) - 1 < i:
        k += 1
    while (1 << k) - 1 != i:
        i -= (1 << (k - 1)) - 1
        k = 1
        while (1 << k) - 1 < i:
            k += 1
    return 1 << (k - 1)


def resoudre(n, clauses, unite_luby=100, min_apprises=2000, decroissance=0.95):
    """Renvoie un modèle (liste [±1, ±2, ..., ±n]) ou None si la formule est UNSAT.
    Paramètres : redémarrage après unite_luby * luby(k) conflits ; réduction des clauses
    apprises au-delà de len(longues)/3 + min_apprises ; décroissance VSIDS. Les valeurs
    par défaut sont celles de MiniSat ; les tests les réduisent pour forcer ces chemins."""
    # ---------- structures ----------
    val = [0] * (2 * n + 1)           # par littéral : 1 vrai, -1 faux, 0 libre
    lev = [0] * (2 * n + 1)           # lev[l] : niveau de décision où l a été rendu vrai
    reason = [None] * (2 * n + 1)     # reason[l] : clause qui a impliqué l (None = décision)
    seen = [False] * (2 * n + 1)      # marques de l'analyse de conflit (littéraux vrais)
    imp = [[] for _ in range(2 * n + 1)]      # imp[l] : couples (q, clause) : l vrai => q vrai
    watches = [[] for _ in range(2 * n + 1)]  # watches[l] : clauses longues surveillant l
    act = [0.0] * (n + 1)             # activité VSIDS de chaque variable
    polar = [-v for v in range(n + 1)]  # phase sauvegardée : littéral à essayer pour v

    # ---------- chargement des clauses ----------
    # Invariant des clauses longues : les littéraux surveillés sont c[0] et c[1].
    longues = []
    units = []
    for c in clauses:
        s = set(c)
        if len(s) < len(c):
            c = list(s)                     # doublons : (1 ∨ 1 ∨ 2) devient (1 ∨ 2)
        if any(-x in s for x in c):
            continue                        # tautologie (x ∨ ¬x ∨ ...) : toujours vraie
        if len(c) == 0:
            return None                     # clause vide : jamais satisfiable
        if len(c) == 1:
            units.append(c[0])
        elif len(c) == 2:
            a, b = c
            imp[-a].append((b, c))          # a faux => b vrai
            imp[-b].append((a, c))          # b faux => a vrai
        else:
            longues.append(c)
            watches[c[0]].append(c)
            watches[c[1]].append(c)
        # Activité initiale = poids de Jeroslow-Wang (somme des 2^-|c|) : avant tout
        # conflit, on commence par les variables des clauses courtes (comme H7).
        w = 2.0 ** -len(c)
        for x in c:
            act[x if x > 0 else -x] += w
    # Phase initiale : vrai pour les variables des clauses longues positives. Sur Meowdoku
    # ce sont les clauses « au moins un chat dans la région » : on essaie de poser un chat
    # (forte propagation), conclusion de la Q5 (H8). Ailleurs : faux (choix de MiniSat).
    for c in longues:
        if all(x > 0 for x in c):
            for x in c:
                polar[x] = x

    # Clauses unitaires : affectées au niveau 0 (propagées au premier tour de boucle).
    trail = []
    for u in units:
        if val[u] < 0:
            return None                     # x et ¬x tous deux unitaires
        if val[u] == 0:
            val[u] = 1
            val[-u] = -1
            trail.append(u)

    heap = [(-act[v], v) for v in range(1, n + 1)]  # tas min sur -activité = tas max
    heapify(heap)
    trail_lim = []          # trail_lim[d-1] : position dans trail de la décision du niveau d
    qhead = 0               # trail[:qhead] a déjà été propagé
    dl = 0                  # niveau de décision courant
    inc = 1.0               # incrément VSIDS courant
    apprises = []           # couples (LBD, clause) des clauses apprises longues
    max_apprises = len(longues) // 3 + min_apprises
    nb_conflits = 0
    k_luby = 1
    prochain_restart = unite_luby * luby(1)

    while True:
        # ================= propagation unitaire =================
        # Pour chaque littéral p de la trace non encore traité, on cherche les clauses
        # devenues unitaires (=> on affecte) ou fausses (=> conflit) parce que ¬p est faux.
        confl = None
        while qhead < len(trail):
            p = trail[qhead]
            qhead += 1
            # -- clauses binaires : p vrai => q vrai pour chaque (q, c) de imp[p]
            for q, c in imp[p]:
                vq = val[q]
                if vq == 0:
                    val[q] = 1
                    val[-q] = -1
                    lev[q] = dl
                    reason[q] = c
                    trail.append(q)
                elif vq < 0:                # q déjà faux : la clause binaire est fausse
                    confl = c
                    break
            if confl is not None:
                break
            # -- clauses longues surveillant fl = ¬p, qui vient de devenir faux.
            # On parcourt ws en le compactant sur place : ws[:j] = clauses qui gardent
            # fl comme surveillé ; les autres changent de liste de surveillance.
            fl = -p
            ws = watches[fl]
            i = j = 0
            nw = len(ws)
            while i < nw:
                c = ws[i]
                i += 1
                a = c[0]                    # on range fl en c[1] ; a = l'autre surveillé
                if a == fl:
                    a = c[1]
                    c[0] = a
                    c[1] = fl
                va = val[a]
                if va > 0:                  # clause déjà vraie : rien à faire
                    ws[j] = c
                    j += 1
                    continue
                for k in range(2, len(c)):  # cherche un remplaçant non faux pour fl
                    x = c[k]
                    if val[x] >= 0:
                        c[1] = x
                        c[k] = fl
                        watches[x].append(c)
                        break
                else:                       # aucun remplaçant : tout est faux sauf peut-être a
                    ws[j] = c
                    j += 1
                    if va == 0:             # clause unitaire : a doit être vrai
                        val[a] = 1
                        val[-a] = -1
                        lev[a] = dl
                        reason[a] = c
                        trail.append(a)
                    else:                   # a faux aussi : conflit ; on garde le reste de ws
                        confl = c
                        while i < nw:
                            ws[j] = ws[i]
                            j += 1
                            i += 1
            del ws[j:]
            if confl is not None:
                break

        if confl is not None:
            # ================= analyse du conflit (1-UIP) =================
            nb_conflits += 1
            if dl == 0:
                return None                 # conflit sans aucune décision : UNSAT
            # On résout la clause de conflit avec les raisons des littéraux du niveau
            # courant, en remontant la trace, jusqu'à ce qu'il ne reste qu'un seul littéral
            # de ce niveau (le premier point d'implication unique, 1-UIP). `chemin` compte
            # les littéraux du niveau courant restant à résoudre. Les littéraux des niveaux
            # inférieurs vont directement dans la clause apprise `appr` (appr[0] réservé
            # au littéral du 1-UIP). Les littéraux du niveau 0 sont omis (toujours faux).
            appr = [0]
            chemin = 0
            p = 0
            idx = len(trail) - 1
            c = confl
            while True:
                for x in c:                 # x est faux, sauf x == p (le littéral impliqué)
                    if x == p:
                        continue
                    t = -x                  # littéral vrai correspondant, sur la trace
                    if seen[t]:
                        continue
                    lt = lev[t]
                    if lt == 0:
                        continue
                    seen[t] = True
                    v = t if t > 0 else -t
                    act[v] += inc           # VSIDS : la variable participe au conflit
                    if act[v] > 1e100:      # renormalisation (éviter le dépassement)
                        for w in range(1, n + 1):
                            act[w] *= 1e-100
                        inc *= 1e-100
                        heap = [(-act[w], w) for w in range(1, n + 1) if val[w] == 0]
                        heapify(heap)
                    if lt >= dl:
                        chemin += 1
                    else:
                        appr.append(x)
                while not seen[trail[idx]]:  # dernier littéral marqué de la trace
                    idx -= 1
                p = trail[idx]
                idx -= 1
                seen[p] = False
                chemin -= 1
                if chemin == 0:             # p est le 1-UIP
                    break
                c = reason[p]               # sinon on résout avec la raison de p
            appr[0] = -p

            # Minimisation : x est inutile si tous les autres littéraux de sa raison sont
            # déjà dans la clause (marqués) ou du niveau 0 (résolution avec cette raison).
            m = [appr[0]]
            for x in appr[1:]:
                r = reason[-x]
                if r is None:               # décision : indispensable
                    m.append(x)
                    continue
                for y in r:
                    if y != -x and not seen[-y] and lev[-y] > 0:
                        m.append(x)
                        break
            for x in appr[1:]:
                seen[-x] = False            # remise à zéro des marques
            appr = m

            # Niveau de retour = plus haut niveau parmi appr[1:] (0 si clause unitaire).
            # Ce littéral est placé en appr[1] pour être surveillé avec appr[0].
            bt = 0
            if len(appr) > 1:
                ib = 1
                for k in range(1, len(appr)):
                    lk = lev[-appr[k]]
                    if lk > bt:
                        bt = lk
                        ib = k
                appr[1], appr[ib] = appr[ib], appr[1]

            # Retour arrière : on défait tous les niveaux > bt.
            lim = trail_lim[bt]
            for k in range(len(trail) - 1, lim - 1, -1):
                l = trail[k]
                val[l] = 0
                val[-l] = 0
                v = l if l > 0 else -l
                polar[v] = l                # sauvegarde de phase
                heappush(heap, (-act[v], v))  # la variable redevient candidate
            del trail[lim:]
            del trail_lim[bt:]
            qhead = lim
            dl = bt

            # Ajout de la clause apprise ; elle est unitaire au niveau bt : appr[0] vrai.
            u = appr[0]
            if len(appr) == 1:
                reason[u] = None            # fait de niveau 0
            elif len(appr) == 2:
                b = appr[1]
                imp[-u].append((b, appr))
                imp[-b].append((u, appr))
                reason[u] = appr
            else:
                watches[u].append(appr)
                watches[appr[1]].append(appr)
                apprises.append((len({lev[-x] for x in appr}), appr))  # (LBD, clause)
                reason[u] = appr
            val[u] = 1
            val[-u] = -1
            lev[u] = dl
            trail.append(u)
            inc /= decroissance             # = multiplier toutes les activités par 0,95
            continue

        # ================= redémarrage et réduction =================
        if nb_conflits >= prochain_restart and dl > 0:
            k_luby += 1
            prochain_restart = nb_conflits + unite_luby * luby(k_luby)
            lim = trail_lim[0]              # on défait tout sauf le niveau 0
            for k in range(len(trail) - 1, lim - 1, -1):
                l = trail[k]
                val[l] = 0
                val[-l] = 0
                v = l if l > 0 else -l
                polar[v] = l
                heappush(heap, (-act[v], v))
            del trail[lim:]
            trail_lim.clear()
            qhead = lim
            dl = 0
            # Réduction faite au niveau 0 : aucune clause apprise n'est alors la raison
            # d'un littéral utilisé par l'analyse (elle ignore le niveau 0), on peut donc
            # en supprimer. On garde la meilleure moitié (LBD faible) et toutes les LBD <= 2.
            if len(apprises) > max_apprises:
                apprises.sort(key=lambda e: e[0])
                garde = len(apprises) // 2
                apprises = [e for k, e in enumerate(apprises) if k < garde or e[0] <= 2]
                max_apprises = int(max_apprises * 1.1)
                for ws in watches:          # on reconstruit les listes de surveillance
                    ws.clear()
                for c in longues:
                    watches[c[0]].append(c)
                    watches[c[1]].append(c)
                for _, c in apprises:
                    watches[c[0]].append(c)
                    watches[c[1]].append(c)
            # Le tas accumule des entrées périmées (variables affectées) : on le purge.
            if len(heap) > 4 * n + 1000:
                heap = [(-act[v], v) for v in range(1, n + 1) if val[v] == 0]
                heapify(heap)

        # ================= décision =================
        # Variable libre la plus active ; les entrées du tas déjà affectées sont ignorées.
        while heap:
            v = heappop(heap)[1]
            if val[v] == 0:
                break
        else:                               # plus de variable libre, pas de conflit : SAT
            return [v if val[v] > 0 else -v for v in range(1, n + 1)]
        dl += 1
        trail_lim.append(len(trail))
        l = polar[v]
        val[l] = 1
        val[-l] = -1
        lev[l] = dl
        reason[l] = None
        trail.append(l)
