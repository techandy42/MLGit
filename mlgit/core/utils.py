"""
Module: mlgit.core.utils

This module provides utility functions for MLGit's core functionality, focusing on
Git repository operations and path management:

1) `find_git_root()`
   - Determines the root directory of the current Git repository
   - Uses the shell's PWD environment variable to start the search
   - Exits with error if PWD is unset or current directory is not in a Git repo
   - Returns a Path object pointing to the Git repository root

Key Functions:
- `find_git_root()`

Author: Hokyung (Andy) Lee
Email: techandy42@gmail.com
Date: May 17, 2025
"""

import os
import subprocess
import sys
from pathlib import Path


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
