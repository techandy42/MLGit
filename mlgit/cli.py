"""
Module: mlgit.cli

This module implements the command‐line interface for MLGit, providing Git-like
subcommands to initialize, index, and (temporary) retrieve AST results:

1) `mlgit init`
   - Finds the Git repository root via `find_git_root()`.
   - Calls `init_repo()` to bootstrap the `.mlgit/` directory structure and default config.

2) `mlgit index`
   - Locates the Git root.
   - Invokes the dependency‐aware scheduler (`schedule()`) in AST mode by default.

3) `mlgit debug-graph` (development only)
   - Builds and displays the import graph for the repository.
   - Requires MLGIT_DEV_MODE=1 to run.

4) `mlgit debug-ast-results-retrieve` (development only)
   - Loads AST-analysis JSON blobs for the current commit.
   - Optionally filters by a simple substring pattern on file paths.
   - Requires MLGIT_DEV_MODE=1 to run.

Key Functions:
- `main()`

Author: Hokyung (Andy) Lee
Email: techandy42@gmail.com
Date: May 17, 2025
"""

import argparse
import json
import os
import sys
from pathlib import Path
from mlgit.core.utils import find_git_root
from mlgit.core.initializer import init_repo
from mlgit.core.scheduler import schedule
from mlgit.core.retriever import load_ast_results
from mlgit.core.graph import build_import_graph, serialize_import_graph


def main():
    parser = argparse.ArgumentParser(
        description="MLGit: Index Codebase into Natural Language Descriptions; Works Just Like Git."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Regular commands
    subparsers.add_parser("init", help="Initialize a new MLGit repository")
    subparsers.add_parser("index", help="Index the current repository and show AST results")
    
    # Debug/Development commands
    debug_graph = subparsers.add_parser(
        "debug-graph",
        help=argparse.SUPPRESS  # Hide from help
    )

    debug_ast_retrieve = subparsers.add_parser(
        "debug-ast-results-retrieve",
        help=argparse.SUPPRESS  # Hide from help
    )
    debug_ast_retrieve.add_argument(
        "-p", "--pattern",
        help="Only include modules whose file path contains this substring",
        default=None
    )

    args = parser.parse_args()
    repo_root = find_git_root()

    if args.command == "init":
        init_repo(repo_root)
    elif args.command == "index":
        schedule(repo_root, mode='ast')
    elif args.command == "debug-graph":
        # Development-only command
        if not os.environ.get('MLGIT_DEV_MODE'):
            print("Error: This command is for development purposes only.", file=sys.stderr)
            print("Set MLGIT_DEV_MODE=1 to enable debug commands.", file=sys.stderr)
            sys.exit(1)
            
        graph = build_import_graph(repo_root)
        serialized_graph = serialize_import_graph(graph)
        print("\nImport Graph:")
        print("-" * 40)
        print(json.dumps(serialized_graph, indent=4))
        print("-" * 40)
    elif args.command == "debug-ast-results-retrieve":
        # Development-only command
        if not os.environ.get('MLGIT_DEV_MODE'):
            print("Error: This command is for development purposes only.", file=sys.stderr)
            print("Set MLGIT_DEV_MODE=1 to enable debug commands.", file=sys.stderr)
            sys.exit(1)
            
        ast_results = load_ast_results(repo_root)
        if args.pattern:
            ast_results_filtered = [r for r in ast_results if args.pattern in r.get('module', '')]
        print("Filtered AST Results:")
        for result in ast_results_filtered:
            print("-" * 40)
            print(json.dumps(result, indent=4))
        print("-" * 40)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
