"""
Module: mlgit.core.retriever

Provides retrieval functions for loading AST/LLM analysis JSON blobs
from the .mlgit content-addressable store and per-commit manifests.

Exports:
- load_manifest(repo_root: Path) -> Dict[str, str]
- load_blob(digest: str, repo_root: Path) -> Dict[str, Any]
- load_ast_index(repo_root: Path) -> Dict[str, Any]
- load_ast_results(repo_root: Path) -> List[Dict[str, Any]]

Author: Hokyung (Andy) Lee
Email: techandy42@gmail.com
Date: April 30, 2025
"""

import json
import gzip
from pathlib import Path
from typing import Dict, Any, List

from mlgit.core.storage import load_config


def load_manifest(repo_root: Path) -> Dict[str, str]:
    """
    Load the manifest for the current commit from .mlgit/manifests.

    Returns a mapping of module names to blob digests.
    """
    cfg = load_config(repo_root)
    manifest_dir = repo_root / cfg["storage"]["manifests_dir"]
    commit = cfg.get("repo", {}).get("commit")
    if not commit:
        raise ValueError("No commit recorded in config.json; please run `mlgit index` first.")

    manifest_path = manifest_dir / f"{commit}.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest file not found: {manifest_path}")

    with manifest_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("modules", {})


def load_blob(digest: str, repo_root: Path) -> Dict[str, Any]:
    """
    Given a blob digest, load and return its JSON content from .mlgit/objects.
    """
    cfg = load_config(repo_root)
    objects_dir = repo_root / cfg["storage"]["objects_dir"]
    prefix = digest[:2]
    filename = f"{digest[2:]}.json.gz"
    blob_path = objects_dir / prefix / filename
    if not blob_path.exists():
        raise FileNotFoundError(f"Blob not found: {blob_path}")

    with gzip.open(blob_path, "rt", encoding="utf-8") as gz:
        return json.load(gz)


def load_ast_results(repo_root: Path) -> List[Dict[str, Any]]:
    """
    Retrieve the AST-analysis results as a list of metadata dicts,
    exactly as passed into store_ast_results.

    Returns a list of metadata dictionaries in no particular order.
    """
    modules = load_manifest(repo_root)
    results: List[Dict[str, Any]] = []
    for _, digest in modules.items():
        results.append(load_blob(digest, repo_root))
    return results
