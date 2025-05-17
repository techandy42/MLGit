"""
Module: mlgit.core.old_type_validator

This module provides utilities for mapping import statements to in-repo modules,
extracting available classes and type aliases (both local and linked), and validating
LLM-generated type annotations against a strict, deterministic type policy.

Key functions:

1) resolve_imported_module_path(imp, target_module_path, repo_root, ast_results) -> Optional[Path]
   • Given a single AST-extracted import dict, computes the absolute file path of the
     referenced module within the repository (or returns None if it’s external).

2) get_type_names(target_module_path, ast_results, repo_root) -> Dict[str, Any]
   • For a given module path, gathers:
       – internal_classes: detailed metadata for every class defined or imported broadly
       – internal_type_aliases: every type alias defined or imported broadly
       – external_modules: module names imported but unresolved in ast_results
       – external_identifiers: specific names imported from unresolved external modules

3) validate_type(annotation, internal_classes, internal_type_aliases,
                 external_identifiers, external_modules) -> bool
   • Parses an annotation string and ensures it only uses:
       – Built-ins and typing generics (e.g., int, List[T], Optional[U], Callable[..., R])
       – Project-defined classes and type aliases
       – Qualified names from recognized external modules
       – Nested combinations thereof

Author: Hokyung (Andy) Lee
Email: techandy42@gmail.com
Date: May 1, 2025
"""

from pathlib import Path
from typing import Dict, Any, List, Optional, Set, Tuple


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

    for cls in module_meta.get('classes', []):
        name = cls.get('name')
        if name:
            internal_classes[name] = {
                'docstring': cls.get('docstring'),
                'attributes': cls.get('attributes', []),
                'methods': cls.get('methods', [])
            }

    for alias in module_meta.get('type_aliases', []):
        name = alias.get('name')
        if name:
            internal_type_aliases[name] = alias.get('definition')

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

    for mod in list(specific_imports):
        if mod in broad_imports:
            del specific_imports[mod]

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

    result = {
        'internal_classes': internal_classes,
        'internal_type_aliases': internal_type_aliases,
        'external_modules': sorted(external_modules),
        'external_identifiers': external_identifiers
    }

    return result


def validate_type(
    annotation: str,
    internal_classes: Set[str],
    internal_type_aliases: Set[str],
    external_identifiers: Set[str],
    external_modules: Set[str]
) -> bool:
    """
    Validate that `annotation` is a valid type under strict rules:
      - Basic types: int, float, complex, str, bool, bytes, bytearray, memoryview, Any, None
      - Custom types: names in internal_classes or internal_type_aliases
      - External identifiers: names imported from external modules
      - External modules: module names used in qualified names
      - Generic containers: List, Dict, Tuple, Set, FrozenSet,
        Deque, DefaultDict, Counter, OrderedDict, Iterable, Iterator,
        Sequence, MutableSequence, Mapping, MutableMapping,
        AbstractSet, Container, Collection, Reversible, Callable,
        Awaitable, Coroutine, AsyncIterable, AsyncIterator,
        AsyncContextManager, Generator, AsyncGenerator, Optional, Union,
        Literal, Final, ClassVar, Type, NoReturn, Annotated,
        and their lowercase built-in counterparts.
    """
    s = annotation.replace(' ', '')
    containers = {
        'List','Dict','Tuple','Set','FrozenSet',
        'Deque','DefaultDict','Counter','OrderedDict',
        'Iterable','Iterator','Sequence','MutableSequence',
        'Mapping','MutableMapping',
        'AbstractSet','Container','Collection','Reversible',
        'Callable','Awaitable','Coroutine',
        'AsyncIterable','AsyncIterator','AsyncContextManager',
        'Generator','AsyncGenerator',
        'Optional','Union','Literal','Final','ClassVar','Type',
        'NoReturn','Annotated',
        'list','dict','tuple','set','frozenset','range'
    }
    basic = {
        'int','float','complex','str','bool','bytes','bytearray',
        'memoryview','Any','None'
    }
    simple_allowed = basic.union(internal_classes, internal_type_aliases, external_identifiers)

    def parse_type(s: str, i: int) -> Tuple[bool, int]:
        n = len(s)
        j = i
        while j < n and (s[j].isalnum() or s[j]=='_' or s[j]=='.'):
            j += 1
        if j == i:
            return False, i
        name = s[i:j]
        if j < n and s[j] == '[':
            if name not in containers:
                return False, i
            j += 1
            ok, j = parse_args(s, j)
            if not ok or j >= n or s[j] != ']':
                return False, i
            return True, j+1
        if name in simple_allowed:
            return True, j
        prefix = name.split('.',1)[0]
        if prefix in external_modules:
            return True, j
        return False, i

    def parse_args(s: str, i: int) -> Tuple[bool, int]:
        ok, j = parse_type(s, i)
        if not ok:
            return False, i
        n = len(s)
        while j < n and s[j] == ',':
            j += 1
            ok, j = parse_type(s, j)
            if not ok:
                return False, i
        return True, j

    ok, pos = parse_type(s, 0)
    return ok and pos == len(s)
