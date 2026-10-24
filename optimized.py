"""Solveur optimisé (Q6) : le DPLL de dpll.py, corrigé sur ses trois causes de lenteur.

Profil de dpll.py (heuristique H8) : 92 à 94 % du temps part dans trois causes (simplifier 60 %, unitaire/pur 17 %, H8 16 %) qui
parcourent toute la formule F à chaque étape.

  1. `simplifier(F, l)` reconstruit un nouvel ensemble de clauses à chaque affectation,
     en O(|F|), alors qu'une affectation ne touche que les clauses contenant l ou -l.
     -> Ici la formule ne change jamais. On garde une affectation `val` et la liste
        `trail` des littéraux affectés dans l'ordre ; revenir en arrière = défaire la fin
        de `trail` (coût = nombre de littéraux défaits).

  2. `trouver_unitaire(F)` (et `trouver_pur`) cherchent en parcourant F.
     -> Deux littéraux surveillés par clause (c[0] et c[1]) : tant que les deux ne sont
        pas faux, la clause n'est ni unitaire ni fausse. Quand un littéral devient faux,
        on ne regarde que les clauses qui le surveillent, et on lui cherche un
        remplaçant non faux ; s'il n'y en a pas, la clause est unitaire (ou fausse).
        Le littéral pur est abandonné : le test coûte O(|F|) et ne sert à rien sur
        Meowdoku (aucun littéral pur, voir NOTES_Q5.md). Cela ne change pas la correction.

  3. L'heuristique H8 relit F à chaque décision.
     -> Les seules clauses qui l'intéressent sont les clauses entièrement positives de la
        formule de départ (sur Meowdoku : « au moins un chat dans la région »). On les
        met de côté une fois pour toutes ; une décision ne parcourt qu'elles.

Le reste est identique à dpll.py : même recherche (décision, branche 1 puis branche 0,
retour arrière chronologique), donc la même logique que `dpll` avec H8 (sauf le littéral pur, abandonné, et le repli quand il n'y a plus de clause positive).

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
    watches = [[] for _ in range(2 * n + 1)]   # watches[l] : clauses dont l est surveillé
    occ = [0] * (2 * n + 1)            # nombre d'occurrences de chaque littéral
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
        while len(trail) > marque:
            l = trail.pop()
            val[l] = 0
            val[-l] = 0
        tete = marque                  # !!!!! ce qui reste a été entièrement propagé

    # ---------- chargement ----------
    # Invariant : une clause de taille >= 2 est dans watches[c[0]] et watches[c[1]].
    for c in clauses:
        c = list(dict.fromkeys(c))     # copie sans doublons : (1 ∨ 1 ∨ 2) devient (1 ∨ 2)
        if any(-x in c for x in c):
            continue                   # tautologie (x ∨ ¬x ∨ ...) : toujours vraie
        if not c:
            return None                # clause vide : jamais satisfiable
        if len(c) == 1:
            if val[c[0]] < 0:          # c[0] est déjà faux : au chargement seule une clause de taille 1 affecte,
                                       # donc une clause (¬c[0]) est passée avant ; (x) et (¬x) se contredisent, UNSAT 
                return None           
            if val[c[0]] == 0:
                affecter(c[0])         # propagé plus tard, avec les décisions
            continue
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
            i = j = 0                  # ws[:j] : clauses qui gardent `faux` surveillé
            while i < len(ws):
                c = ws[i]
                i += 1
                if c[0] == faux:       # on range `faux` en c[1] ; a = l'autre surveillé
                    c[0] = c[1]
                    c[1] = faux
                a = c[0]
                if val[a] > 0:         # clause déjà vraie : rien à faire
                    ws[j] = c
                    j += 1
                    continue
                for k in range(2, len(c)):          # remplaçant non faux pour `faux` ?
                    x = c[k]
                    if val[x] >= 0:
                        c[1] = x
                        c[k] = faux
                        watches[x].append(c)        # x != faux, donc pas la liste ws
                        break
                else:                  # aucun remplaçant : tout est faux sauf peut-être a
                    ws[j] = c
                    j += 1
                    if val[a] == 0:
                        affecter(a)    # clause unitaire : a doit être vrai
                    else:              # a faux aussi : conflit ; on garde le reste de ws
                        ws[j:] = ws[i:]
                        return False
            del ws[j:]
        return True

    def choisir():
        """Littéral à rendre vrai, ou None si toutes les variables sont affectées.
        H8 : parmi les clauses positives non satisfaites, celle qui a le moins de
        littéraux libres ; dans cette clause, la variable la plus fréquente, valeur 1.
        S'il n'y en a pas : première variable libre de `ordre`."""
        meilleure = None
        k_min = n + 1
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
            return max((x for x in meilleure if val[x] == 0), key=lambda x: (occ[x] + occ[-x], -x))
        for l in ordre:
            if val[l] == 0:
                return l
        return None

    def chercher():
        if not propager():
            return False
        l = choisir()
        if l is None:
            return True                # tout est affecté sans conflit : toutes les clauses sont vraies
        marque = len(trail)
        for x in (l, -l):              # branche « l vrai » puis branche « l faux »
            affecter(x)
            if chercher():
                return True
            defaire(marque)
        return False

    if not chercher():
        return None
    return [v if val[v] > 0 else -v for v in range(1, n + 1)]
