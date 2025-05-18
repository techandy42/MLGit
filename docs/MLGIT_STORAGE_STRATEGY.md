# MLGit: Content-Addressable + Manifests & Smart Re-Indexing Summary

This document summarizes our end-to-end design for storing and updating MLGit’s index using a content-addressable object store, per-commit manifests, and a “nearest-ancestor” re-indexing strategy.

---

## 1. `.mlgit/` Folder Layout

```
.mlgit/
├─ config.json            ← tool settings & “last indexed” pointer
│
├─ objects/               ← compressed JSON blobs, keyed by SHA256
│   ├─ ab/                ← first 2 hex chars of digest
│   │   └─ cdef…json.gz   ← rest of digest + `.json.gz`
│   ├─ 12/
│   └─ …
│
└─ manifests/             ← one small JSON per commit SHA
    ├─ a1b2c3d4e5f6.json   ← maps modules → blob hashes
    ├─ d4e5f6a1b2c3.json
    └─ …
```

---

## 2. `config.json` Schema

```json
{
  "mlgit_version": "0.1.0",
  "repo": {
    "commit": "<last-indexed-SHA|null>",
    "branch": "<last-indexed-branch|null>"
  },
  "scheduler": { "static_workers": null, "dynamic_workers": 8 },
  "llm":      { "provider": "openai", "model": "gpt-4.1-mini-2025-04-14" },
  "storage": {
    "strategy":       "content-addressable",
    "hash_algo":      "sha256",
    "compression":    "gzip",
    "objects_dir":    ".mlgit/objects",
    "manifests_dir":  ".mlgit/manifests"
  },
  "housekeeping": {
    "prune_unreferenced": true,
    "keep_last_manifests": 5
  }
}
```

---

## 3. Indexing / Re-indexing Workflow

1. **Select target SHA**  
   - Default: `HEAD` → `git rev-parse HEAD`  
   - Or user-supplied: `mlgit index --rev <SHA>`  

2. **Locate baseline manifest**  
   - **Nearest-ancestor strategy**:  
     - List all files in `.mlgit/manifests/`  
     - Pick the SHA that is a Git ancestor of `<SHA>` and is closest on commit graph  
   - If none found, treat as full index (baseline = empty).  

3. **Compute delta**  
   ```bash
   git diff --name-only <baseline>..<SHA> -- '*.py'
   ```  
   ⇒ list of changed `.py` files

4. **Build graph & SCCs**  
   - Read file contents via `git show <SHA>:path`  
   - Run `build_import_graph`, `find_sccs`, `estimate_component_weights`, `compute_critical_path`  

5. **Generate & store blobs**  
   For each module/SCC JSON blob:
   ```python
   data = json.dumps(obj, sort_keys=True, separators=(",",":")).encode()
   digest = sha256(data).hexdigest()
   path = objects_dir / digest[:2] / f"{digest[2:]}.json.gz"
   gzip.write(path, data)  # skip if exists
   ```
   ⇒ maximal deduplication

6. **Write commit manifest**  
   `.mlgit/manifests/<SHA>.json`:
   ```json
   {
     "modules": {
       "package.module": "<digest>",
       …
     }
   }
   ```

7. **Update `config.json.repo`**  
   ```json
   "repo": { "commit": "<SHA>", "branch": "<current-branch>" }
   ```

---

## 4. Retrieval / Loading

To load index for `<SHA>`:

```python
manifest = load_json(".mlgit/manifests/<SHA>.json")
for module, digest in manifest["modules"].items():
    blob = gzip.open(".mlgit/objects/" + digest[:2] + "/" + digest[2:] + ".json.gz")
    data = json.load(blob)
    index[module] = data
```

- If manifest missing ⇒ `mlgit index --rev <SHA>` (full or delta).

---

## 5. Smart Baseline Selection

- **Nearest-ancestor**: always diff against the indexed commit closest to your target on the Git DAG.  
- Benefits: minimal diff-set even when jumping backwards or across branches, no redundant work.

---

## 6. Git Hooks for Auto-sync

Install in `.git/hooks/` (make executable):

```sh
# post-checkout, post-merge, post-rewrite
#!/bin/sh
exec mlgit index --changed
```

- Automatically re-indexes only changed files whenever HEAD moves.

---

## 7. Housekeeping

- **Prune unreferenced**:  
  `mlgit clean --prune-unreferenced`  
  ⇒ delete any `objects/` blobs not referenced by **any** manifest.
- **Keep last N manifests**:  
  `mlgit clean --keep-last 5`  
  ⇒ delete manifest files older than the 5 most-recent SHAs.

---

## 8. Regeneration Fallback

Even if all local cache is deleted:

```bash
mlgit index --rev <SHA>
```

- Reads code from Git at `<SHA>`, rebuilds everything, repopulates `objects/` & `manifests/`.

---

> With this design you get:  
> - **Reproducibility**: every commit’s index is fully reconstructible.  
> - **Efficiency**: only new or changed blobs are written; diffs against nearest ancestor minimize work.  
> - **Deduplication**: identical JSON outputs across commits stored once.  
> - **Shareability**: manifests are small shareable pointers; objects can be packaged or served.  

