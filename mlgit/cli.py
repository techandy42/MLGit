import argparse
import os
import subprocess
import sys
from pathlib import Path
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

    if args.command == "init":
        print("mlgit init")

    elif args.command == "index":
        repo_root = find_git_root()
        schedule(repo_root, test_mode=True)

    else:
        parser.print_help()

if __name__ == "__main__":
    main()
