"""Solveur optimisé (Q6) : le DPLL de dpll.py, corrigé sur deux de ses causes de lenteur.

Profil de dpll.py (heuristique H8) : `simplifier` prend environ 60 % du temps, `trouver_unitaire`
et `trouver_pur` environ 17 %, H8 environ 16 %. Les trois parcourent toute la formule à chaque étape.

  1. `simplifier(F, l)` reconstruit un nouvel ensemble de clauses à chaque affectation,
     en O(|F|), alors qu'une affectation ne touche que les clauses contenant l ou -l.
     -> Ici la formule ne change jamais. On garde une affectation `val` et la liste
        `trail` des littéraux affectés dans l'ordre ; revenir en arrière = défaire la fin
        de `trail` (coût = nombre de littéraux défaits).

  2. `trouver_unitaire(F)` cherche une clause unitaire en parcourant F.
     -> Deux littéraux surveillés par clause (ses deux premiers, c[0] et c[1]). Tant que ces deux
        littéraux ne sont pas faux, la clause n'est ni unitaire ni fausse. Quand un littéral
        devient faux, on ne regarde que les clauses qui le surveillent : on lui cherche un
        remplaçant non faux dans la clause ; s'il n'y en a pas, l'autre surveillé doit être
        vrai (clause unitaire) ou bien la clause est fausse (conflit).

  3. L'heuristique H8 relit F à chaque décision.
     -> Les seules clauses qui l'intéressent sont les clauses entièrement positives de la
        formule de départ (sur Meowdoku : « au moins un chat dans la région »). On les
        met de côté une fois pour toutes ; une décision ne parcourt qu'elles.

Le reste est identique à dpll.py : propagation des clauses unitaires, littéral pur (cherché par un
parcours de la formule, seulement avant chaque décision), puis décision, branche 1 puis branche 0,
retour arrière chronologique. H8 se replie sur H2 statique, plus simple que H7d et comparable sur les instances Meowdoku.

Représentation : littéraux DIMACS signés (k = x_k, -k = ¬x_k). Les tableaux indexés par
littéral ont 2n+1 cases : t[l] pour l > 0 et t[-l] pour l < 0 (les indices négatifs de
Python comptent depuis la fin : t[-l] = t[2n+1-l]). Pas de calcul d'indice.
"""
import sys

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


def resoudre(n, clauses):
    """Renvoie un modèle (liste [±1, ±2, ..., ±n]) ou None si la formule est UNSAT."""
    sys.setrecursionlimit(max(sys.getrecursionlimit(), n + 1000))   # profondeur = nb de décisions

    val = [0] * (2 * n + 1)            # par littéral : 1 vrai, -1 faux, 0 libre
    occ = [0] * (2 * n + 1)            # nombre d'occurrences de chaque littéral
    cl = []                            # clauses de taille >= 2 (sans doublons ni tautologies)
    watches = [[] for _ in range(2 * n + 1)]   # watches[l] : clauses dont l est l'un des deux surveillés
    positives = []                     # clauses de départ entièrement positives (pour H8)
    trail = []                         # littéraux affectés, dans l'ordre
    tete = 0                           # trail[:tete] a déjà été propagé

    def affecter(l):
        val[l] = 1
        val[-l] = -1
        trail.append(l)

    def defaire(marque):
        """Défait les affectations jusqu'à ce que trail ait la longueur `marque`."""
        nonlocal tete
        tete = marque                  # ce qui reste a déjà été entièrement propagé
        while len(trail) > marque:
            l = trail.pop()
            val[l] = 0
            val[-l] = 0

    # ---------- chargement ----------
    for c in clauses:
        c = list(dict.fromkeys(c))     # copie sans doublons : (1 ∨ 1 ∨ 2) devient (1 ∨ 2)
        if any(-x in c for x in c):
            continue                   # tautologie (x ∨ ¬x ∨ ...) : toujours vraie
        if not c:
            return None                # clause vide : jamais satisfiable
        if len(c) == 1:
            if val[c[0]] < 0:
                return None            # (x) et (¬x) : contradiction
            if val[c[0]] == 0:
                affecter(c[0])         # sera propagé avec le reste
            continue
        cl.append(c)
        watches[c[0]].append(c)
        watches[c[1]].append(c)
        for x in c:
            occ[x] += 1
        if all(x > 0 for x in c):
            positives.append(c)

    # Repli de l'heuristique : variables par nombre d'occurrences décroissant, valeur =
    # polarité majoritaire (H2 statique).
    ordre = sorted(range(1, n + 1), key=lambda v: -(occ[v] + occ[-v]))
    ordre = [v if occ[v] >= occ[-v] else -v for v in ordre]

    def propager():
        """Propagation unitaire. Renvoie False si une clause est fausse (conflit)."""
        nonlocal tete
        while tete < len(trail):
            faux = -trail[tete]        # littéral qui vient de devenir faux
            tete += 1
            ws = watches[faux]
            watches[faux] = []         # on y remet les clauses qui gardent `faux` surveillé
            for i, c in enumerate(ws):
                if c[0] == faux:       # on range `faux` en c[1] ; c[0] est l'autre surveillé
                    c[0], c[1] = c[1], c[0]
                if val[c[0]] > 0:      # clause déjà vraie : on garde la surveillance
                    watches[faux].append(c)
                    continue
                for k in range(2, len(c)):          # remplaçant non faux pour `faux` ?
                    if val[c[k]] >= 0:
                        c[1], c[k] = c[k], c[1]
                        watches[c[1]].append(c)     # la clause passe sur le nouveau littéral
                        break
                else:                  # aucun remplaçant : tout est faux sauf peut-être c[0]
                    watches[faux].append(c)
                    if val[c[0]] < 0:              # c[0] faux aussi : conflit
                        watches[faux].extend(ws[i + 1:])
                        return False
                    if val[c[0]] == 0:
                        affecter(c[0])             # clause unitaire : c[0] doit être vrai
        return True

    def trouver_pur():
        """Un littéral libre qui n'apparaît que sous une polarité dans les clauses non satisfaites."""
        vus = set()
        for c in cl:
            if not any(val[x] > 0 for x in c):
                vus.update(x for x in c if val[x] == 0)
        for x in vus:
            if -x not in vus:
                return x
        return None

    def choisir():
        """Littéral à rendre vrai, ou None si toutes les variables sont affectées.
        H8 : parmi les clauses positives non satisfaites, celle qui a le moins de
        littéraux libres ; dans cette clause, la variable la plus fréquente, valeur 1.
        S'il n'y en a pas : première variable libre de `ordre` (H2 statique)."""
        meilleure = None
        k_min = n + 1   # compteur pour savoir quelle clause a le - de littéraux libres, meilleure note laquelle c'est 
        for c in positives:
            libres = 0
            for x in c:
                if val[x] > 0:
                    break              # clause satisfaite
                if val[x] == 0:
                    libres += 1
            else:
                if libres < k_min:
                    k_min = libres
                    meilleure = c
        if meilleure is not None:
            return max((x for x in meilleure if val[x] == 0), key=lambda x: (occ[x] + occ[-x], -x)) # dans la plus petite clause, quel littéral a le + d'occurences
        for l in ordre: # si plus de clause positive, on fait H2
            if val[l] == 0:
                return l
        return None

    def chercher():
        marque = len(trail)
        while True:                    # propagation, puis littéraux purs
            if not propager():
                defaire(marque)
                return False
            l = trouver_pur()
            if l is None:
                break
            affecter(l)
        l = choisir()
        if l is None:
            return True                # tout est affecté sans conflit
        marque2 = len(trail)
        for x in (l, -l):              # branche « l vrai » puis branche « l faux »
            affecter(x)
            if chercher():
                return True
            defaire(marque2)
        defaire(marque)
        return False

    if not chercher():
        return None
    return [v if val[v] > 0 else -v for v in range(1, n + 1)]
