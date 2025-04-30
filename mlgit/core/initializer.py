"""
Module: mlgit.core.initializer

This module provides the `mlgit init` functionality, bootstrapping a new MLGit
repository in any existing Git project by:

1) Creating the `.mlgit/` directory at the repository root.
2) Within `.mlgit/`, creating two subdirectories:
   - `objects/`    – content-addressed storage of compressed JSON blobs.
   - `manifests/`  – per-commit manifests mapping modules → blob digests.
3) Writing a default `config.json` with:
   - The MLGit tool version.
   - Repository metadata placeholders (`commit`, `branch`).
   - Scheduler settings (`static_workers`, `dynamic_workers`).
   - LLM backend settings (`provider`, `model`).
   - Storage settings (`strategy`, `hash_algo`, `compression`, `objects_dir`, `manifests_dir`).
   - Housekeeping defaults (`prune_unreferenced`, `keep_last_manifests`).

Exports:
- `init_repo(repo_root: Path)`: Creates the folder structure and default config.
- `main()`: CLI entrypoint that calls `init_repo` on the current or provided path.

Author: Hokyung (Andy) Lee
Email: techandy42@gmail.com
Date: April 29, 2025
"""

import sys
import json
from pathlib import Path

def init_repo(repo_root: Path) -> None:
    """
    Initialize an MLGit repository by creating the .mlgit directory
    with content-addressable storage and per-commit manifests, and a
    default config.json for content-addressable + manifests setup.

    Args:
        repo_root (Path): Path to the root of the Git repository.
    """
    mlgit_dir = repo_root / ".mlgit"
    objects_dir = mlgit_dir / "objects"
    manifests_dir = mlgit_dir / "manifests"

    # Create directories
    objects_dir.mkdir(parents=True, exist_ok=True)
    manifests_dir.mkdir(parents=True, exist_ok=True)

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
        },
        "storage": {
            "strategy": "content-addressable",
            "hash_algo": "sha256",
            "compression": "gzip",
            "objects_dir": ".mlgit/objects",
            "manifests_dir": ".mlgit/manifests"
        },
        "housekeeping": {
            "prune_unreferenced": True,
            "keep_last_manifests": 5
        }
    }
    config_file = mlgit_dir / "config.json"
    with config_file.open("w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)

    print(f"Created {mlgit_dir}/ with 'objects', 'manifests' and default config.json.")

def main():
    """
    CLI entrypoint to initialize MLGit in the current or provided directory.
    """
    if len(sys.argv) > 1:
        repo_root = Path(sys.argv[1]).resolve()
    else:
        repo_root = Path.cwd()
    init_repo(repo_root)

if __name__ == "__main__":
    main()
