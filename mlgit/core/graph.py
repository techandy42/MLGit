"""
Module: mlgit.core.graph

This module builds an import‐statement dependency graph for a given Git repository,
then groups and schedules the resulting strongly‐connected components (SCCs)
for optimal processing.  

1) Dependency Graph Construction
   - Use `git ls-tree -r --name-only HEAD` to list every committed `.py` file.
   - Map each file’s module name (derived from its path) to its filesystem path.
   - For each file:
     * Read its on‐disk source and parse the AST.
     * Walk `ast.Import` and `ast.ImportFrom` nodes.
     * Perform a longest‐prefix lookup against the module map so that
       imports like `pkg.subpkg.mod` match the deepest available module.
     * Build an adjacency list mapping each file → set of files it imports.
   - Ensure files with no imports still appear as isolated nodes.

2) SCC Grouping & Weighted Topological Scheduling
   - Run Tarjan’s algorithm to collapse any import‐cycles into SCCs (each SCC
     becomes a single processing unit).
   - Construct a condensed DAG whose edges run from each provider component
     → each consumer component (i.e. “provider imports → consumer”).
   - Estimate a weight for each component (sum of on‐disk byte sizes) as
     a proxy for processing cost.
   - Compute each component’s critical‐path length (longest total weight
     to any leaf) via a reverse topological DP.
   - Schedule with Kahn’s algorithm, maintaining a ready set of components
     with no unmet dependencies.  Always pick the ready component with the
     largest critical‐path length first.  
     * This guarantees **producer-before-consumer** (no consumer runs before
       its providers), and within each dependency “layer,” it schedules
       **bigger before smaller** tasks to minimize overall I/O wait time.
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


def process_modules(graph: Dict[Path, Set[Path]]) -> List[FrozenSet[Path]]:
    """
    Collapse SCCs into components, build a provider→consumer DAG,
    then schedule components by descending critical-path length
    while ensuring all producers come before their consumers.
    """
    # 1) SCC collapse
    sccs = find_sccs(graph)
    comp_map: Dict[Path, FrozenSet[Path]] = {}
    for comp in sccs:
        for f in comp:
            comp_map[f] = comp

    # add singleton components
    all_comps: Set[FrozenSet[Path]] = set(sccs)
    for f in graph:
        if f not in comp_map:
            solo = frozenset({f})
            comp_map[f] = solo
            all_comps.add(solo)

    # 2) build provider→consumer DAG
    comp_out: Dict[FrozenSet[Path], Set[FrozenSet[Path]]] = {c: set() for c in all_comps}
    indegree: Dict[FrozenSet[Path], int] = {c: 0 for c in all_comps}

    for consumer, deps in graph.items():
        consumer_c = comp_map[consumer]
        for provider in deps:
            provider_c = comp_map[provider]
            if provider_c is not consumer_c:
                comp_out[provider_c].add(consumer_c)
                indegree[consumer_c] += 1

    # 3) compute weights & critical-path lengths
    weights = estimate_component_weights(all_comps)
    cp_lengths = compute_critical_path(comp_out, weights)

    # 4) Kahn’s algorithm with weight-priority among ready nodes
    ready = [c for c, deg in indegree.items() if deg == 0]
    ready.sort(key=lambda c: -cp_lengths[c])

    ordered: List[FrozenSet[Path]] = []
    while ready:
        comp = ready.pop(0)
        ordered.append(comp)
        for consumer_c in comp_out[comp]:
            indegree[consumer_c] -= 1
            if indegree[consumer_c] == 0:
                ready.append(consumer_c)
        ready.sort(key=lambda c: -cp_lengths[c])

    return ordered


def print_import_graph(graph: Dict[Path, Set[Path]]) -> None:
    """
    Pretty-print the import graph as JSON.
    """
    serializable = {
        str(src): sorted(str(dst) for dst in dsts)
        for src, dsts in graph.items()
    }
    print(json.dumps(serializable, indent=2))


def print_processing_queue(queue: List[FrozenSet[Path]]) -> None:
    """
    Print each component (or singleton) in the order they should be processed.
    Groups (SCCs) are printed together.
    """
    print("\nProcessing order:")
    for comp in queue:
        if len(comp) > 1:
            print("Group:")
        for f in sorted(comp, key=lambda p: str(p)):
            print("  -", f)
