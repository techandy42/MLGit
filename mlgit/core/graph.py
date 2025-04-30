"""
Module: mlgit.core.graph

This module provides functions to analyze Python source files in a Git repository by:

1) Dependency Graph Construction
   - Uses `git ls-tree -r --name-only HEAD` to list every committed `.py` file.
   - Maps each file’s module name (derived from its path) to its filesystem path.
   - Parses each file’s AST to extract `import` and `from ... import` statements.
   - Resolves imports via a longest-prefix match against the module map.
   - Builds an adjacency list mapping each file → set of files it imports.
   - Ensures files with no imports still appear as isolated nodes.

2) Strongly-Connected Component Analysis
   - Runs Tarjan’s algorithm to collapse import cycles into SCCs.
   - Returns each SCC as a frozenset of file paths.

3) Component Weight Estimation
   - Estimates each component’s weight by summing on-disk byte sizes of its files.

4) Critical-Path Computation
   - Given a DAG of provider→consumer edges and per-component weights,
     computes each component’s critical-path length (longest total weight to any leaf)
     via a reverse topological DP.

5) Utilities
   - `print_import_graph`: Pretty-prints the import graph as JSON.

Author: Hokyung (Andy) Lee
Email: techandy42@gmail.com
Date: April 27, 2025
"""

import ast
import subprocess
import json
from pathlib import Path
from collections import defaultdict, deque
from typing import Dict, Set, FrozenSet, List

def build_import_graph(repo_root: Path) -> Dict[Path, Set[Path]]:
    """
    Walk the committed .py files in the repo and build a graph where each
    file maps to the set of other files it imports.
    """
    repo_root = repo_root.resolve()

    # 1) List only committed .py files
    raw = subprocess.check_output(
        ["git", "ls-tree", "-r", "--name-only", "HEAD"],
        cwd=str(repo_root), stderr=subprocess.DEVNULL
    ).decode().splitlines()
    py_files = [repo_root / p for p in raw if p.endswith(".py")]

    # 2) Map module names to file paths
    module_map: Dict[str, Path] = {}
    for f in py_files:
        rel = f.relative_to(repo_root)
        module_map[".".join(rel.with_suffix("").parts)] = f

    # 3) Parse each file and resolve imports via longest-prefix match
    graph: Dict[Path, Set[Path]] = defaultdict(set)
    for f in py_files:
        text = f.read_text(encoding="utf-8")
        tree = ast.parse(text, filename=str(f))

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    parts = alias.name.split(".")
                    for i in range(len(parts), 0, -1):
                        candidate = ".".join(parts[:i])
                        if candidate in module_map:
                            graph[f].add(module_map[candidate])
                            break

            elif isinstance(node, ast.ImportFrom):
                # skip star imports
                for alias in node.names:
                    if alias.name == "*":
                        continue
                    # attempt module.alias as full name
                    if node.module:
                        full = f"{node.module}.{alias.name}"
                    else:
                        full = alias.name
                    parts = full.split(".")
                    for i in range(len(parts), 0, -1):
                        candidate = ".".join(parts[:i])
                        if candidate in module_map:
                            graph[f].add(module_map[candidate])
                            break

        # ensure even files with no imports still appear
        graph.setdefault(f, set())

    return graph


def find_sccs(graph: Dict[Path, Set[Path]]) -> Set[FrozenSet[Path]]:
    """
    Tarjan’s algorithm, returning each strongly‐connected component as a frozenset.
    """
    index = 0
    indices: Dict[Path, int] = {}
    lowlink: Dict[Path, int] = {}
    stack: List[Path] = []
    on_stack: Set[Path] = set()
    sccs: List[FrozenSet[Path]] = []

    def strongconnect(v: Path):
        nonlocal index
        indices[v] = lowlink[v] = index
        index += 1
        stack.append(v)
        on_stack.add(v)

        for w in graph[v]:
            if w not in indices:
                strongconnect(w)
                lowlink[v] = min(lowlink[v], lowlink[w])
            elif w in on_stack:
                lowlink[v] = min(lowlink[v], indices[w])

        if lowlink[v] == indices[v]:
            comp: List[Path] = []
            while True:
                w = stack.pop()
                on_stack.remove(w)
                comp.append(w)
                if w == v:
                    break
            sccs.append(frozenset(comp))

    for v in graph:
        if v not in indices:
            strongconnect(v)

    return set(sccs)


def estimate_component_weights(comps: Set[FrozenSet[Path]]) -> Dict[FrozenSet[Path], float]:
    """
    Estimate each component’s weight by summing on-disk byte sizes of its files.
    """
    weights: Dict[FrozenSet[Path], float] = {}
    for comp in comps:
        total_bytes = sum(f.stat().st_size for f in comp)
        weights[comp] = float(total_bytes)
    return weights


def compute_critical_path(
    dag: Dict[FrozenSet[Path], Set[FrozenSet[Path]]],
    weight: Dict[FrozenSet[Path], float]
) -> Dict[FrozenSet[Path], float]:
    """
    Given a DAG of provider→consumer edges and per-component weights,
    compute each node’s critical-path length.
    """
    # build indegree map
    indegree: Dict[FrozenSet[Path], int] = {n: 0 for n in dag}
    for src, consumers in dag.items():
        for c in consumers:
            indegree[c] += 1

    # topo sort
    q = deque([n for n, deg in indegree.items() if deg == 0])
    topo: List[FrozenSet[Path]] = []
    while q:
        n = q.popleft()
        topo.append(n)
        for c in dag[n]:
            indegree[c] -= 1
            if indegree[c] == 0:
                q.append(c)

    # DP backwards to compute longest path
    cp: Dict[FrozenSet[Path], float] = {n: weight.get(n, 1.0) for n in dag}
    for n in reversed(topo):
        for c in dag[n]:
            cp[n] = max(cp[n], weight.get(n, 1.0) + cp[c])
    return cp


def print_import_graph(graph: Dict[Path, Set[Path]]) -> None:
    """
    Pretty-print the import graph as JSON.
    """
    serializable = {
        str(src): sorted(str(dst) for dst in dsts)
        for src, dsts in graph.items()
    }
    print(json.dumps(serializable, indent=2))
