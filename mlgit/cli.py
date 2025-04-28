import argparse
import subprocess
from pathlib import Path

# For finding the top-level Git repository; used for indexing
def find_git_root() -> Path:
    """Return the top-level Git repository path or cwd if not in a repo."""
    try:
        top = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"],
            stderr=subprocess.DEVNULL,
        ).decode().strip()
        return Path(top)
    except subprocess.CalledProcessError:
        return Path.cwd()

def main():
    parser = argparse.ArgumentParser(
        description="MLGit: Index Codebase into Natural Language Descriptions; Works Just Like Git."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("init", help="Initialize a new MLGit repository")
    subparsers.add_parser("index", help="Index the current repository")

    args = parser.parse_args()
    if args.command == "init":
        print("mlgit init")
    elif args.command == "index":
        print("mlgit index")
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
