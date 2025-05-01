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

3) `mlgit retrieve` (temporary)
   - Loads AST-analysis JSON blobs for the current commit.
   - Optionally filters by a simple substring pattern on file paths.

Key Functions:
- `find_git_root() -> Path`
- `main()`

Author: Hokyung (Andy) Lee
Email: techandy42@gmail.com
Date: April 28, 2025
"""
import argparse
import os
import subprocess
import sys
import json
from pathlib import Path
from mlgit.core.initializer import init_repo
from mlgit.core.scheduler import schedule
from mlgit.core.retriever import load_ast_results
from mlgit.core.type_validator import resolve_imported_module_path


def find_git_root() -> Path:
    """
    Look in the original shell directory (from $PWD) for the Git root.
    If PWD isn’t set or it’s not inside a Git repo, exit with an error.
    """
    shell_pwd = os.environ.get("PWD")
    if not shell_pwd:
        print("Error: could not determine your working directory (PWD is unset)", file=sys.stderr)
        sys.exit(1)

    search_dir = Path(shell_pwd)
    try:
        top = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=str(search_dir), stderr=subprocess.DEVNULL
        ).decode().strip()
        return Path(top)
    except subprocess.CalledProcessError:
        print(f"Error: '{search_dir}' is not inside a Git repository", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="MLGit: Index Codebase into Natural Language Descriptions; Works Just Like Git."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # init subcommand
    subparsers.add_parser("init", help="Initialize a new MLGit repository")
    # index subcommand
    subparsers.add_parser("index", help="Index the current repository and show AST results")
    # retrieve subcommand (temporary)
    retrieve_parser = subparsers.add_parser(
        "retrieve",
        help="(temporary) Retrieve AST results, optionally filtered by file pattern"
    )
    retrieve_parser.add_argument(
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

    elif args.command == "retrieve":
        # Temporary command for development
        ast_results = load_ast_results(repo_root)
        if args.pattern:
            ast_results_filtered = [r for r in ast_results if args.pattern in r.get('module', '')]
        print("AST Results:")
        for result in ast_results_filtered:
            print("-" * 40)
            print(json.dumps(result, indent=4))
            imports  = result.get('imports', [])
            module_path = Path(result.get('module', ''))
            for imp in imports:
                resolved_path = resolve_imported_module_path(imp, module_path, repo_root, ast_results)
                if resolved_path:
                    print(f"Resolved import: {imp} -> {resolved_path}")
                else:
                    print(f"Could not resolve import: {imp}")
        print("-" * 40)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
