"""
Module: mlgit.core.scheduler

Orchestrates parallel, dependency-aware indexing and enrichment of Python source files
within a Git repository. Supports four modes of operation:

1) Static Analysis (`ast`)
   - Uses a ProcessPoolExecutor to perform AST-based extraction for each strongly-connected
     component (SCC) of the import graph.

2) LLM-Based Type Inference (`llm_types`)
   - Uses a ThreadPoolExecutor as a placeholder for an LLM pass to infer missing types.

3) LLM-Based Docstring Generation (`llm_docs`)
   - Uses a ThreadPoolExecutor as a placeholder for an LLM pass to generate docstrings.

4) Test Simulation (`test`)
   - Uses a ThreadPoolExecutor to sleep proportional to file sizes, simulating work.

The core function `schedule(repo_root: Path, max_workers: int, mode: str)`:
  - Constructs the import graph and finds SCCs via Tarjan's algorithm.
  - Estimates component weights and computes critical-path lengths for prioritization.
  - Maintains a max-heap of ready components and dispatches tasks to the selected executor.
  - In `ast` mode, gathers AST results and writes them to storage.
  - In `llm_types` and `llm_docs` modes, loads cached AST results and invokes LLM enrichment.
  - In `test` mode, prints simulated processing order.

Exports:
- test_index_modules
- llm_index_modules
- schedule

Author: Hokyung (Andy) Lee
Email: techandy42@gmail.com
Date: April 28, 2025
"""

from pathlib import Path
import os
import time
import json
from queue import PriorityQueue
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, wait, FIRST_COMPLETED

from mlgit.core.graph import (
    build_import_graph,
    find_sccs,
    estimate_component_weights,
    compute_critical_path,
)
from mlgit.core.ast_indexer import ast_index_modules
from mlgit.core.storage import store_ast_results
from mlgit.core.retriever import load_ast_results


def test_index_modules(file_paths):
    """
    Simulate indexing of modules by sleeping proportional to total file size.

    Args:
        file_paths (List[Path]): Files in the SCC group.

    Returns:
        List[str]: The string paths of processed files.
    """
    total_bytes = sum(p.stat().st_size for p in file_paths)
    seconds = total_bytes / 1024
    time.sleep(seconds)
    return [str(p) for p in file_paths]


def llm_index_modules(file_paths):
    """
    Placeholder for LLM-based enrichment of modules.

    Args:
        file_paths (List[Path]): Files in the SCC group.

    Returns:
        List[str]: The string paths of processed files.
    """
    # TODO: implement LLM request & enrichment
    return [str(p) for p in file_paths]


def schedule(repo_root: Path, max_workers: int = None, mode: str = 'test'):
    """
    Orchestrate parallel, dependency-aware indexing of Python files in a Git repo.

    Modes:
      - 'ast': AST-only analysis pass
      - 'llm_types': LLM-based type inference pass (placeholder)
      - 'llm_docs': LLM-based docstring generation pass (placeholder)
      - 'test': simulation pass for testing scheduler behavior

    Args:
        repo_root (Path): Path to the Git repository root.
        max_workers (int, optional): Number of parallel worker processes (defaults to CPU count).
        mode (str): One of 'ast', 'llm_types', 'llm_docs', or 'test'.
    """
    max_workers = max_workers or os.cpu_count() or 1

    if mode == 'ast':
        process_fn = ast_index_modules
        executor_cls = ProcessPoolExecutor
        ast_results = []
    elif mode in ('llm_types', 'llm_docs'):
        process_fn = llm_index_modules
        executor_cls = ThreadPoolExecutor
    elif mode == 'test':
        process_fn = test_index_modules
        executor_cls = ThreadPoolExecutor
    else:
        raise ValueError(f"Unknown mode: {mode}. Expected 'ast', 'llm_types', 'llm_docs', or 'test'.")

    graph = build_import_graph(repo_root)
    sccs = find_sccs(graph)

    comp_map = {f: comp for comp in sccs for f in comp}
    all_comps = set(sccs)
    for f in graph:
        if f not in comp_map:
            solo = frozenset({f})
            comp_map[f] = solo
            all_comps.add(solo)

    comp_out = {c: set() for c in all_comps}
    indegree = {c: 0 for c in all_comps}
    for consumer, deps in graph.items():
        consumer_c = comp_map[consumer]
        for provider in deps:
            provider_c = comp_map[provider]
            if provider_c is not consumer_c:
                comp_out[provider_c].add(consumer_c)
                indegree[consumer_c] += 1

    weights = estimate_component_weights(all_comps)
    cp_lengths = compute_critical_path(comp_out, weights)

    ready = PriorityQueue()
    for comp in all_comps:
        if indegree[comp] == 0:
            ready.put((-cp_lengths[comp], comp))

    processed_comps = []

    with executor_cls(max_workers=max_workers) as executor:
        futures = {}
        while not ready.empty() and len(futures) < max_workers:
            _, comp = ready.get()
            future = executor.submit(process_fn, list(comp))
            futures[future] = comp

        while futures:
            done, _ = wait(futures.keys(), return_when=FIRST_COMPLETED)
            for fut in done:
                comp = futures.pop(fut)
                result = fut.result()
                if mode == 'ast':
                    ast_results.extend(result)
                elif mode == 'test':
                    processed_comps.append((comp, result))

                for child in comp_out[comp]:
                    indegree[child] -= 1
                    if indegree[child] == 0:
                        ready.put((-cp_lengths[child], child))

            while not ready.empty() and len(futures) < max_workers:
                _, comp = ready.get()
                future = executor.submit(process_fn, list(comp))
                futures[future] = comp

    if mode == 'ast':
        print("AST Analysis Results:")
        for module_dict in ast_results:
            print("-" * 40)
            print(json.dumps(module_dict, indent=4, sort_keys=True))
        print("-" * 40)
        store_ast_results(ast_results, repo_root)

    if mode in ('llm_types', 'llm_docs'):
        ast_results = load_ast_results(repo_root)
        print("Cached AST Analysis Results:")
        for module_dict in ast_results:
            print("-" * 40)
            print(json.dumps(module_dict, indent=4, sort_keys=True))
        print("-" * 40)

    if mode == 'test':
        print("Processing order:")
        for comp, paths in processed_comps:
            print("-" * 40)
            for path in paths:
                print(path)
        print("-" * 40)


if __name__ == "__main__":
    import sys
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    schedule(root, mode='test')
