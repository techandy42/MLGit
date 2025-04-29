import sys
import json
from pathlib import Path

def init_repo(repo_root: Path) -> None:
    """
    Initialize an MLGit repository by creating the .mlgit directory
    with 'raw' and 'enriched' subfolders and a default config.json.

    Args:
        repo_root (Path): Path to the root of the Git repository.
    """
    mlgit_dir = repo_root / ".mlgit"
    raw_dir = mlgit_dir / "raw"
    enriched_dir = mlgit_dir / "enriched"

    # Create directories
    raw_dir.mkdir(parents=True, exist_ok=True)
    enriched_dir.mkdir(parents=True, exist_ok=True)

    # Create default config.json
    config = {
        "mlgit_version": "0.1.0",
        "repo": {
            "commit": None,
            "branch": None
        },
        "scheduler": {
            "static_workers": None,
            "dynamic_workers": 8
        },
        "llm": {
            "provider": "openai",
            "model": "gpt-4.1-mini-2025-04-14"
        }
    }
    config_file = mlgit_dir / "config.json"
    with config_file.open("w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)

    print(f"Created {mlgit_dir}/ with subfolders 'raw', 'enriched' and default config.json.")

def main():
    # Determine target directory: current working directory
    repo_root = Path.cwd()
    init_repo(repo_root)

if __name__ == "__main__":
    # Allow an optional path argument
    if len(sys.argv) > 1:
        repo_root = Path(sys.argv[1]).resolve()
    else:
        repo_root = Path.cwd()
    init_repo(repo_root)
