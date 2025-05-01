from pathlib import Path
from typing import Dict, Any, List, Optional

def resolve_imported_module_path(
    imp: Dict[str, Any],
    target_module_path: Path,
    repo_root: Path,
    ast_results: List[Dict[str, Any]]
) -> Optional[Path]:
    """
    Map a single import entry to an indexed module file path from ast_results.
    Returns the Path if found, else None.

    imp dict fields:
      - 'module': dotted module path (absolute) or module name (relative)
      - 'kind': 'absolute' or 'relative'
      - 'level': 0 for absolute, ≥1 for number of leading dots in relative imports
    """
    # Build a set of all known module file paths (as strings)
    ast_paths = { entry["module"] for entry in ast_results }

    kind = imp.get("kind")
    level = imp.get("level", 0)
    module_base = imp.get("module", "")

    if kind == "absolute" or level == 0:
        # Convert dotted name to slash-separated relative path
        rel = module_base.replace(".", "/")
        cand_py   = str(repo_root / f"{rel}.py")
        cand_init = str(repo_root / rel / "__init__.py")

        if cand_py in ast_paths:
            return Path(cand_py)
        if cand_init in ast_paths:
            return Path(cand_init)
        return None

    # Relative import: climb up `level` directories from the target, then append module_base
    directory = target_module_path.parent
    for _ in range(level):
        directory = directory.parent

    if module_base:
        rel = module_base.replace(".", "/")
        cand_py   = str(directory / f"{rel}.py")
        cand_init = str(directory / rel / "__init__.py")
    else:
        # Bare `from . import X` or similar
        cand_py   = str(directory / "__init__.py")
        cand_init = cand_py

    if cand_py in ast_paths:
        return Path(cand_py)
    if cand_init in ast_paths:
        return Path(cand_init)
    return None
