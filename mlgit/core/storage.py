"""
Module: mlgit.core.storage

Handles content-addressable storage of AST/LLM analysis results into ".mlgit/objects" and manifests in ".mlgit/manifests".
It serializes metadata blobs, writes commit manifests, updates config, and performs housekeeping.

Exports:
- store_ast_results(results: List[Dict[str, Any]], repo_root: Path)

Author: Hokyung (Andy) Lee
Email: techandy42@gmail.com
Date: April 30, 2025
"""

import json
import gzip
import hashlib
import tempfile
import subprocess
from pathlib import Path
from typing import List, Dict, Any


def load_config(repo_root: Path) -> Dict[str, Any]:
    config_path = repo_root / ".mlgit" / "config.json"
    with config_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_config(config: Dict[str, Any], repo_root: Path) -> None:
    config_path = repo_root / ".mlgit" / "config.json"
    temp_path = config_path.with_suffix(".tmp")
    with temp_path.open("w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)
    temp_path.replace(config_path)


def ensure_dirs(objects_dir: Path, manifests_dir: Path) -> None:
    objects_dir.mkdir(parents=True, exist_ok=True)
    manifests_dir.mkdir(parents=True, exist_ok=True)


def compute_digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_blob(digest: str, data: bytes, objects_dir: Path) -> None:
    subdir = objects_dir / digest[:2]
    subdir.mkdir(parents=True, exist_ok=True)
    blob_path = subdir / f"{digest[2:]}.json.gz"
    if blob_path.exists():
        return
    # Atomic write via temp file
    with tempfile.NamedTemporaryFile(dir=subdir, delete=False) as tmpf:
        with gzip.GzipFile(fileobj=tmpf, mode="wb") as gz:
            gz.write(data)
    Path(tmpf.name).replace(blob_path)


def write_manifest(commit: str, modules_map: Dict[str, str], manifests_dir: Path) -> None:
    manifest_path = manifests_dir / f"{commit}.json"
    temp_path = manifest_path.with_suffix(".tmp")
    manifest = {"modules": modules_map}
    with temp_path.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, sort_keys=True)
    temp_path.replace(manifest_path)


def prune_unreferenced(objects_dir: Path, manifests_dir: Path) -> None:
    referenced: set = set()
    # Collect all referenced digests from manifests
    for mf in manifests_dir.glob("*.json"):
        try:
            mdata = json.loads(mf.read_text(encoding="utf-8"))
            referenced.update(mdata.get("modules", {}).values())
        except Exception:
            continue
    # Remove blobs not referenced
    for prefix in objects_dir.iterdir():
        if not prefix.is_dir() or len(prefix.name) != 2:
            continue
        for blob_file in prefix.glob("*.json.gz"):
            name = blob_file.name  # e.g. 'cdef0123...json.gz'
            if not name.endswith(".json.gz"):
                continue
            hex_tail = name[:-len(".json.gz")]
            digest = prefix.name + hex_tail
            if digest not in referenced:
                blob_file.unlink()
        # Remove empty prefix dirs
        if not any(prefix.iterdir()):
            prefix.rmdir()


def trim_manifests(manifests_dir: Path, keep: int) -> None:
    files = sorted(
        manifests_dir.glob("*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )
    for old in files[keep:]:
        old.unlink()


def get_git_commit(repo_root: Path) -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=str(repo_root)
    ).decode().strip()


def get_git_branch(repo_root: Path) -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=str(repo_root)
    ).decode().strip()


def store_ast_results(results: List[Dict[str, Any]], repo_root: Path) -> None:
    """
    Store a list of AST-analysis metadata dicts into the .mlgit store:
      - Serializes each dict to canonical JSON, hashes & compresses to objects/
      - Builds a manifest mapping module names to digests
      - Updates config.json with latest commit/branch
      - Performs housekeeping (prune & trim)
    """
    cfg = load_config(repo_root)
    storage_cfg = cfg.get("storage", {})
    hk_cfg = cfg.get("housekeeping", {})

    objects_dir = repo_root / storage_cfg.get("objects_dir", ".mlgit/objects")
    manifests_dir = repo_root / storage_cfg.get("manifests_dir", ".mlgit/manifests")
    ensure_dirs(objects_dir, manifests_dir)

    modules_map: Dict[str, str] = {}
    for module_obj in results:
        # Derive module name from file path relative to repo root
        path = Path(module_obj.get("module", ""))
        rel = path.relative_to(repo_root)
        module_name = ".".join(rel.with_suffix("").parts)

        # Serialize to canonical JSON
        data = json.dumps(
            module_obj, sort_keys=True, separators=(",",":" )
        ).encode("utf-8")
        digest = compute_digest(data)
        write_blob(digest, data, objects_dir)
        modules_map[module_name] = digest

    commit = get_git_commit(repo_root)
    branch = get_git_branch(repo_root)

    write_manifest(commit, modules_map, manifests_dir)

    # Update config
    cfg.setdefault("repo", {})["commit"] = commit
    cfg.setdefault("repo", {})["branch"] = branch
    save_config(cfg, repo_root)

    # Housekeeping
    if hk_cfg.get("prune_unreferenced", False):
        prune_unreferenced(objects_dir, manifests_dir)
    keep = hk_cfg.get("keep_last_manifests")
    if isinstance(keep, int) and keep > 0:
        trim_manifests(manifests_dir, keep)
