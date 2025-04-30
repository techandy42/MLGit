"""
Module: mlgit.cli

This module implements the command‐line interface for MLGit, providing Git-like
subcommands to initialize and index a repository:

1) `mlgit init`  
   - Finds the Git repository root via `find_git_root()`.  
   - Calls `init_repo()` to bootstrap the `.mlgit/` directory structure and default config.

2) `mlgit index`  
   - Locates the Git root.  
   - Invokes the dependency‐aware scheduler (`schedule()`) in test mode by default,
     which builds the import graph, collapses SCCs, and simulates processing.

Key Functions:

- `find_git_root() -> Path`  
  Discovers the top-level Git directory from the `$PWD` environment variable,
  exiting with an error if not inside a Git repo.

- `main()`  
  Parses subcommands (`init` and `index`), delegates to the appropriate core routines,
  and prints help for unsupported commands.

Author: Hokyung (Andy) Lee  
Email: techandy42@gamil.com  
Date: April 28, 2025
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path
from mlgit.core.initializer import init_repo
from mlgit.core.scheduler import schedule

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
            cwd=str(search_dir),
            stderr=subprocess.DEVNULL,
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

    subparsers.add_parser("init", help="Initialize a new MLGit repository")
    subparsers.add_parser("index", help="Index the current repository and show graphs")

    args = parser.parse_args()
    repo_root = find_git_root()

    if args.command == "init":
        init_repo(repo_root)

    elif args.command == "index":
        schedule(repo_root, mode='ast')

    else:
        parser.print_help()

if __name__ == "__main__":
    main()
