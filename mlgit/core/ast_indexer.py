"""
Module: mlgit.core.ast_indexer

This module provides AST-based extraction of Python file metadata,
excluding call-resolution.

Key functionalities:

1) get_signature(func_node)
   • Builds a nested signature dictionary for FunctionDef and AsyncFunctionDef nodes:
     – parameters: list of {name: str, type: Optional[str], default: Optional[str]}
     – returns: Optional[str]

2) index_file(file_path)
   • Parses a Python source file and extracts:
     – module: the path or name of the file
     – docstring: module-level docstring
     – imports: list of {
           module: str,              # imported module path (e.g., "os" or module base for from-import)
           identifier: Optional[str], # specific name imported (None for broad imports)
           alias: Optional[str],      # alias for module or identifier
           kind: str,                # "absolute" or "relative"
           level: int                # number of leading dots (0 for absolute, 1 for "from .module" imports, etc.)
       }
     – constants: list of {name: str, value: Any}
     – type_aliases: list of {name: str, definition: str}
     – functions: list of {
           name: str,
           signature: {parameters: [...], returns: ...},
           docstring: Optional[str],
           decorators: List[str]
       }
     – classes: list of {
           name: str,
           bases: List[str],
           docstring: Optional[str],
           decorators: List[str],
           attributes: List[{name: str, value: Any}],
           methods: List[... same as functions ...]
       }
     – main_guard: bool (True if an `if __name__ == "__main__":` block exists)

3) ast_index_modules(file_paths)
   • Applies index_file over a list of file paths (e.g., each SCC) and
     returns a flat list of metadata dictionaries for each module.

Exports:
- get_signature
- index_file
- ast_index_modules

Author: Hokyung (Andy) Lee
Email: techandy42@gmail.com
Date: May 1, 2025
"""

from pathlib import Path
import ast
from typing import Any, Dict, List, Optional, Union


def get_signature(func_node: Union[ast.FunctionDef, ast.AsyncFunctionDef]) -> Dict[str, Any]:
    """
    Build a nested signature dict for a FunctionDef or AsyncFunctionDef node:
      - parameters: list of {name: str, type: Optional[str], default: Optional[str]}
      - returns: Optional[str]
    """
    sig: Dict[str, Any] = {'parameters': [], 'returns': None}
    args = func_node.args
    # Positional args
    pos_args = args.args
    defaults = [None] * (len(pos_args) - len(args.defaults)) + list(args.defaults)
    for arg, default in zip(pos_args, defaults):
        name = arg.arg
        annotation = ast.unparse(arg.annotation) if arg.annotation else None
        default_str = ast.unparse(default) if default is not None else None
        sig['parameters'].append({'name': name, 'type': annotation, 'default': default_str})
    # Vararg (*args)
    if args.vararg:
        name = args.vararg.arg
        annotation = ast.unparse(args.vararg.annotation) if args.vararg.annotation else None
        sig['parameters'].append({'name': f'*{name}', 'type': annotation, 'default': None})
    # Keyword-only args
    for kwarg, default in zip(args.kwonlyargs, args.kw_defaults):
        name = kwarg.arg
        annotation = ast.unparse(kwarg.annotation) if kwarg.annotation else None
        default_str = ast.unparse(default) if default is not None else None
        sig['parameters'].append({'name': name, 'type': annotation, 'default': default_str})
    # Kwarg (**kwargs)
    if args.kwarg:
        name = args.kwarg.arg
        annotation = ast.unparse(args.kwarg.annotation) if args.kwarg.annotation else None
        sig['parameters'].append({'name': f'**{name}', 'type': annotation, 'default': None})
    # Return annotation
    if getattr(func_node, 'returns', None):
        sig['returns'] = ast.unparse(func_node.returns)
    return sig


def index_file(file_path: Union[str, Path]) -> Dict[str, Any]:
    """
    Parse and extract structured metadata from a Python file.

    Returns a dictionary with:
      - module: module name or file path
      - docstring: module-level docstring
      - imports: list of {
            module: str,        # imported module path
            identifier: Optional[str],  # name imported from module (None for broad imports)
            alias: Optional[str],       # alias for module or identifier
            kind: str,        # "absolute" or "relative"
            level: int        # 0 for absolute, >0 for number of leading dots
        }
      - constants: list of {'name': str, 'value': Any}
      - type_aliases: list of {'name': str, 'definition': str}
      - functions: list of {
            'name': str,
            'signature': {parameters: [...], returns: ...},
            'docstring': Optional[str],
            'decorators': List[str]
        }
      - classes: list of {
            'name': str,
            'bases': List[str],
            'docstring': Optional[str],
            'decorators': List[str],
            'attributes': List[Dict],
            'methods': List[... same as functions ...]
        }
      - main_guard: True if `if __name__ == "__main__":` block exists
    """
    path = Path(file_path)
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(file_path))

    # Module-level docstring
    module_docstring = ast.get_docstring(tree)

    # Imports: handle both `import module` and `from module import name1, name2`
    imports: List[Dict[str, Union[str,int]]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append({
                    'module': alias.name,
                    'identifier': None,
                    'alias': alias.asname,
                    'kind': 'absolute',
                    'level': 0
                })
        elif isinstance(node, ast.ImportFrom):
            level = node.level
            kind = 'relative' if level > 0 else 'absolute'
            base = node.module or ''
            for alias in node.names:
                if alias.name == '*':
                    continue
                imports.append({
                    'module': base,
                    'identifier': alias.name,
                    'alias': alias.asname,
                    'kind': kind,
                    'level': level
                })

    # Global constants
    constants: List[Dict[str, Any]] = []
    for node in tree.body:
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    constants.append({'name': t.id, 'value': node.value.value})

    # Type aliases
    type_aliases: List[Dict[str, str]] = []
    for node in tree.body:
        if isinstance(node, ast.Assign) and not isinstance(node.value, ast.Constant):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    type_aliases.append({'name': t.id, 'definition': ast.unparse(node.value)})
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            name = node.target.id
            if node.annotation:
                definition = ast.unparse(node.annotation)
            elif node.value:
                definition = ast.unparse(node.value)
            else:
                continue
            type_aliases.append({'name': name, 'definition': definition})

    # Functions
    functions: List[Dict[str, Any]] = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            functions.append({
                'name': node.name,
                'signature': get_signature(node),
                'docstring': ast.get_docstring(node),
                'decorators': [ast.unparse(d) for d in node.decorator_list]
            })

    # Classes
    classes: List[Dict[str, Any]] = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            class_info = {
                'name': node.name,
                'bases': [ast.unparse(b) for b in node.bases],
                'docstring': ast.get_docstring(node),
                'decorators': [ast.unparse(d) for d in node.decorator_list],
                'attributes': [],
                'methods': []
            }
            for child in node.body:
                if isinstance(child, ast.Assign) and isinstance(child.value, ast.Constant):
                    for t in child.targets:
                        if isinstance(t, ast.Name):
                            class_info['attributes'].append({'name': t.id, 'value': child.value.value})
                elif isinstance(child, ast.FunctionDef):
                    class_info['methods'].append({
                        'name': child.name,
                        'signature': get_signature(child),
                        'docstring': ast.get_docstring(child),
                        'decorators': [ast.unparse(d) for d in child.decorator_list]
                    })
            classes.append(class_info)

    # Detect main guard
    main_guard = any(
        isinstance(node, ast.If) and
        isinstance(node.test, ast.Compare) and
        isinstance(node.test.left, ast.Name) and
        node.test.left.id == "__name__"
        for node in tree.body
    )

    return {
        'module': str(file_path),
        'docstring': module_docstring,
        'imports': imports,
        'constants': constants,
        'type_aliases': type_aliases,
        'functions': functions,
        'classes': classes,
        'main_guard': main_guard
    }


def ast_index_modules(file_paths: List[Union[str, Path]]) -> List[Dict[str, Any]]:
    """
    Index a list of Python files (e.g., an SCC), returning a flat list of
    metadata dictionaries for each file.
    """
    results: List[Dict[str, Any]] = []
    for fp in file_paths:
        try:
            results.append(index_file(fp))
        except Exception as e:
            results.append({'module': str(fp), 'error': str(e)})
    return results
