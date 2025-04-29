import os
import time
from pathlib import Path
from queue import PriorityQueue
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, wait, FIRST_COMPLETED

from mlgit.core.graph import (
    build_import_graph,
    find_sccs,
    estimate_component_weights,
    compute_critical_path,
)


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


def statically_index_modules(file_paths):
    """
    Placeholder for static AST-based indexing of modules.

    Args:
        file_paths (List[Path]): Files in the SCC group.

    Returns:
        List[str]: The string paths of processed files.
    """
    # TODO: implement AST extraction & serialization
    return [str(p) for p in file_paths]


def dynamically_index_modules(file_paths):
    """
    Placeholder for dynamic LLM-based enrichment of modules.

    Args:
        file_paths (List[Path]): Files in the SCC group.

    Returns:
        List[str]: The string paths of processed files.
    """
    # TODO: implement LLM request & enrichment
    return [str(p) for p in file_paths]


def schedule(repo_root: Path, max_workers: int = None, mode: str = 'dynamic'):
    """
    Orchestrate parallel, dependency-aware indexing of Python files in a Git repo.

    Args:
        repo_root (Path): Path to the Git repository root.
        max_workers (int, optional): Number of parallel worker processes (defaults to CPU count).
        mode (str): 'static' for AST-only pass, 'dynamic' for LLM pass, 'test' for test simulation.
    """
    # Determine worker count
    if max_workers is None:
        max_workers = os.cpu_count() or 1

    # Select processing function and executor based on mode
    if mode == 'static':
        process_fn = statically_index_modules
        executor_cls = ProcessPoolExecutor
    elif mode == 'dynamic':
        process_fn = dynamically_index_modules
        executor_cls = ThreadPoolExecutor
    elif mode == 'test':
        process_fn = test_index_modules
        executor_cls = ThreadPoolExecutor
    else:
        raise ValueError(f"Unknown mode: {mode}. Expected 'static', 'dynamic', or 'test'.")

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
                result_paths = fut.result()
                if mode == 'test':
                    processed_comps.append((comp, result_paths))

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
