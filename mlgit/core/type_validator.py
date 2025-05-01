from pathlib import Path
from typing import Dict, Any, List, Optional, Set


def resolve_imported_module_path(
    imp: Dict[str, Any],
    target_module_path: Path,
    repo_root: Path,
    ast_results: List[Dict[str, Any]]
) -> Optional[Path]:
    ast_paths: Set[str] = { entry["module"] for entry in ast_results }
    kind = imp.get("kind")
    level = imp.get("level", 0)
    base = imp.get("module", "")

    if kind == "absolute" or level == 0:
        rel = base.replace('.', '/')
        cand_py   = str(repo_root / f"{rel}.py")
        cand_init = str(repo_root / rel / "__init__.py")
        if cand_py in ast_paths:
            return Path(cand_py)
        if cand_init in ast_paths:
            return Path(cand_init)
        return None

    directory = target_module_path.parent
    for _ in range(level):
        directory = directory.parent
    if base:
        rel = base.replace('.', '/')
        cand_py   = str(directory / f"{rel}.py")
        cand_init = str(directory / rel / "__init__.py")
    else:
        cand_py   = str(directory / "__init__.py")
        cand_init = cand_py

    if cand_py in ast_paths:
        return Path(cand_py)
    if cand_init in ast_paths:
        return Path(cand_init)
    return None


def get_type_names(
    target_module_path: Path,
    ast_results: List[Dict[str, Any]],
    repo_root: Path
) -> Dict[str, Any]:
    path_map: Dict[str, Dict[str, Any]] = {entry['module']: entry for entry in ast_results}
    target_key = str(Path(target_module_path).resolve())
    module_meta = path_map.get(target_key)
    if not module_meta:
        return {
            'internal_classes': {},
            'internal_type_aliases': {},
            'external_modules': [],
            'external_identifiers': {}
        }

    internal_classes: Dict[str, Any] = {}
    internal_type_aliases: Dict[str, Any] = {}
    external_modules: Set[str] = set()
    external_identifiers: Dict[str, str] = {}

    # Collect own classes
    for cls in module_meta.get('classes', []):
        name = cls.get('name')
        if name:
            internal_classes[name] = {
                'docstring': cls.get('docstring'),
                'attributes': cls.get('attributes', []),
                'methods': cls.get('methods', [])
            }

    # Collect own type aliases
    for alias in module_meta.get('type_aliases', []):
        name = alias.get('name')
        if name:
            internal_type_aliases[name] = alias.get('definition')

    # Classify imports
    imports = module_meta.get('imports', [])
    broad_imports: Set[str] = set()
    specific_imports: Dict[str, Set[str]] = {}

    for imp in imports:
        mod_base = imp.get('module') or ''
        ident = imp.get('identifier')
        if ident is None:
            broad_imports.add(mod_base)
        else:
            specific_imports.setdefault(mod_base, set()).add(ident)

    # If broad import exists, drop specific
    for mod in list(specific_imports):
        if mod in broad_imports:
            del specific_imports[mod]

    # Handle broad imports
    for mod in broad_imports:
        imp_entry = {'module': mod, 'kind': 'absolute', 'level': 0}
        path = resolve_imported_module_path(
            imp_entry,
            Path(target_module_path),
            repo_root,
            ast_results
        )
        if not path:
            external_modules.add(mod)
            continue
        meta = path_map.get(str(path))
        if not meta:
            external_modules.add(mod)
            continue
        for cls in meta.get('classes', []):
            name = cls.get('name')
            if name:
                internal_classes[f"{mod}.{name}"] = {
                    'docstring': cls.get('docstring'),
                    'attributes': cls.get('attributes', []),
                    'methods': cls.get('methods', [])
                }
        for alias in meta.get('type_aliases', []):
            name = alias.get('name')
            if name:
                internal_type_aliases[f"{mod}.{name}"] = alias.get('definition')

    # Handle specific imports
    for mod, idents in specific_imports.items():
        imp_entry = {'module': mod, 'kind': 'absolute', 'level': 0}
        path = resolve_imported_module_path(
            imp_entry,
            Path(target_module_path),
            repo_root,
            ast_results
        )
        if not path:
            for ident in idents:
                external_identifiers[ident] = mod
            continue
        meta = path_map.get(str(path))
        if not meta:
            for ident in idents:
                external_identifiers[ident] = mod
            continue
        class_map = {c.get('name'): c for c in meta.get('classes', [])}
        alias_map = {a.get('name'): a for a in meta.get('type_aliases', [])}
        for ident in idents:
            if ident in class_map:
                cls = class_map[ident]
                internal_classes[ident] = {
                    'docstring': cls.get('docstring'),
                    'attributes': cls.get('attributes', []),
                    'methods': cls.get('methods', [])
                }
            elif ident in alias_map:
                alias = alias_map[ident]
                internal_type_aliases[ident] = alias.get('definition')

    return {
        'internal_classes': internal_classes,
        'internal_type_aliases': internal_type_aliases,
        'external_modules': sorted(external_modules),
        'external_identifiers': external_identifiers
    }
