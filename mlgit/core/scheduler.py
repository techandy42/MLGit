"""
Module: mlgit.core.scheduler

This module orchestrates parallel, dependency‐aware indexing of Python source files
in a Git repository. It provides three distinct modes of operation:

1) Static Analysis Mode (`ast`)
   - Uses a `ProcessPoolExecutor` to perform AST‐based extraction and serialization
     for each strongly‐connected component (SCC) of the import graph.
   - Implements:
     * `build_import_graph` to discover file‐to‐file dependencies.
     * `find_sccs` to collapse import cycles into SCCs.
     * `estimate_component_weights` and `compute_critical_path` for prioritization.
     * A dependency‐respecting, critical‐path‐driven ready queue.

2) Dynamic Analysis Mode (`llm`)
   - Uses a `ThreadPoolExecutor` to issue LLM enrichment requests for each SCC,
     reading the previously written AST “raw” output and writing back “enriched” JSON.
   - Shares the same dependency graph and prioritization logic as static mode,
     but swaps compute‐bound workers for I/O‐bound threads.

3) Test Mode (`test`)
   - Also uses a `ThreadPoolExecutor` to simulate processing by sleeping
     proportional to file size, and prints out the completion order grouped by SCC.
   - Provides the `test_index_modules` stub to validate scheduling behavior
     without external dependencies.

The core function `schedule(repo_root: Path, max_workers: int, mode: str)`:
   - Builds the import graph and SCCs.
   - Constructs a provider→consumer DAG and calculates indegrees.
   - Computes component weights and critical‐path lengths.
   - Maintains a priority queue of ready SCCs.
   - Dispatches tasks to the appropriate executor, re‐enqueueing dependents
     only when all producers finish.
   - In test mode, records and prints the order of processed files.

When invoked as a script (`__main__`), the scheduler runs in `test` mode by default.

Author: Hokyung (Andy) Lee  
Email: techandy42@gmail.com  
Date: April 28, 2025
"""

import os
import time
import json
from pathlib import Path
from queue import PriorityQueue
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, wait, FIRST_COMPLETED

from mlgit.core.graph import (
    build_import_graph,
    find_sccs,
    estimate_component_weights,
    compute_critical_path,
)
from mlgit.core.ast_indexer import ast_index_modules


def test_index_modules(file_paths):
    """
    Simulate indexing of modules by sleeping proportional to total file size.

    Args:
        file_paths (List[Path]): Files in the SCC group.

    Returns:
        List[str]: The string paths of processed files.
    """
    total_bytes = sum(p.stat().st_size for p in file_paths)
    # Sleep ~1 second per KiB of total file size
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


def schedule(repo_root: Path, max_workers: int = None, mode: str = 'llm'):
    """
    Orchestrate parallel, dependency-aware indexing of Python files in a Git repo.

    Args:
        repo_root (Path): Path to the Git repository root.
        max_workers (int, optional): Number of parallel worker processes (defaults to CPU count).
        mode (str): 'ast' for AST-only pass, 'llm' for LLM pass, 'test' for test simulation.
    """
    # Determine worker count
    if max_workers is None:
        max_workers = os.cpu_count() or 1

    # Select processing function and executor based on mode
    if mode == 'ast':
        process_fn = ast_index_modules
        executor_cls = ProcessPoolExecutor
        ast_results = []
    elif mode == 'llm':
        process_fn = llm_index_modules
        executor_cls = ThreadPoolExecutor
    elif mode == 'test':
        process_fn = test_index_modules
        executor_cls = ThreadPoolExecutor
    else:
        raise ValueError(f"Unknown mode: {mode}. Expected 'ast', 'llm', or 'test'.")

    # Step 1: Build the import graph and collapse into SCCs
    graph = build_import_graph(repo_root)
    sccs = find_sccs(graph)

    # Map each file to its component
    comp_map = {f: comp for comp in sccs for f in comp}
    all_comps = set(sccs)
    # Add singleton components for files not in any cycle
    for f in graph:
        if f not in comp_map:
            solo = frozenset({f})
            comp_map[f] = solo
            all_comps.add(solo)

    # Step 2: Build provider->consumer DAG and indegree map
    comp_out = {c: set() for c in all_comps}
    indegree = {c: 0 for c in all_comps}
    for consumer, deps in graph.items():
        consumer_c = comp_map[consumer]
        for provider in deps:
            provider_c = comp_map[provider]
            if provider_c is not consumer_c:
                comp_out[provider_c].add(consumer_c)
                indegree[consumer_c] += 1

    # Step 3: Compute weights and critical-path lengths
    weights = estimate_component_weights(all_comps)
    cp_lengths = compute_critical_path(comp_out, weights)

    # Step 4: Initialize ready priority queue (max-heap via negative priority)
    ready = PriorityQueue()
    for comp in all_comps:
        if indegree[comp] == 0:
            ready.put((-cp_lengths[comp], comp))

    # Track finished components and their files in test mode
    processed_comps = []

    # Step 5: Worker pool for parallel processing
    with executor_cls(max_workers=max_workers) as executor:
        futures = {}

        # Submit initial tasks up to max_workers
        while not ready.empty() and len(futures) < max_workers:
            _, comp = ready.get()
            future = executor.submit(process_fn, list(comp))
            futures[future] = comp

        # Continue scheduling until all tasks complete
        while futures:
            done, _ = wait(futures.keys(), return_when=FIRST_COMPLETED)
            for fut in done:
                comp = futures.pop(fut)
                result = fut.result()
                if mode == 'ast':
                    ast_results.extend(result)
                elif mode == 'test':
                    processed_comps.append((comp, result))

                # Enqueue dependents whose indegree drops to zero
                for child in comp_out[comp]:
                    indegree[child] -= 1
                    if indegree[child] == 0:
                        ready.put((-cp_lengths[child], child))

            # Fill available worker slots
            while not ready.empty() and len(futures) < max_workers:
                _, comp = ready.get()
                future = executor.submit(process_fn, list(comp))
                futures[future] = comp

    # Print out final AST results in formatted manner
    if mode == 'ast':
        print("AST Analysis Results:")
        for module_dict in ast_results:
            print("-" * 40)
            print(json.dumps(module_dict, indent=2, sort_keys=True))
        print("-" * 40)

    # Print out final processing order, grouped by SCC in test mode
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
    # Run in test mode by default when executed as a script
    schedule(root, mode='test')
