"""Visualisation/vérification Q1.
usage: python demo_q1.py N [graine]      (génère une grille)
       python demo_q1.py grille.txt      (charge une grille)
"""
import sys
from itertools import permutations
import generator
import meowdoku as mk


def show(grid, cats=()):
    cats = set(cats)
    for i, row in enumerate(grid):
        out = []
        for j, z in enumerate(row):
            col = 31 + sum(map(ord, z)) % 7
            out.append(f"\033[{col};{'7;' if (i, j) in cats else ''}1m{z:>2}{'*' if (i, j) in cats else ' '}\033[0m")
        print(" ".join(out))


def sat(cl, true_vars):
    return all(any((l > 0) == (abs(l) in true_vars) for l in c) for c in cl)


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    planted = None
    if sys.argv[1].isdigit():
        n = int(sys.argv[1])
        seed = int(sys.argv[2]) if len(sys.argv) > 2 else None
        grid, planted = generator.generate(n, seed)
        print(f"Grille générée N={n} graine={seed}; solution plantée = cases marquées *\n")
        show(grid, planted)
    else:
        grid = mk.parse_grid(sys.argv[1])
        n = len(grid)
        print("Grille chargée\n")
        show(grid)
    cl = mk.encode(grid)
    sizes = {}
    for c in cl:
        sizes[len(c)] = sizes.get(len(c), 0) + 1
    print(f"\nCNF : {n*n} variables, {len(cl)} clauses, tailles {dict(sorted(sizes.items()))}")
    print("exemples :", cl[0], cl[len(cl) // 2], cl[-1])
    if planted:
        print("solution plantée valide (règles)  :", mk.is_valid(grid, planted))
        print("solution plantée satisfait le CNF :", sat(cl, {mk.var(i, j, n) for i, j in planted}))
    if n <= 8:
        sols = [p for p in permutations(range(n))
                if sat(cl, {mk.var(i, j, n) for i, j in enumerate(p)})]
        agree = all(mk.is_valid(grid, list(enumerate(p))) for p in sols)
        print(f"solutions par force brute (permutations) : {len(sols)} ; toutes valides au sens des règles : {agree}")
        for p in sols[:3]:
            print("\nsolution :")
            show(grid, list(enumerate(p)))
    mk.write_dimacs("demo.cnf", n * n, cl)
    print("\nDIMACS écrit dans demo.cnf")


main()
