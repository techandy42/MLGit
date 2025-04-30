from pathlib import Path
import ast
import re
from typing import Any, Dict, List, Optional, Union

TODO_PATTERN = re.compile(r'#\s*TODO[:\s]*(.*)')

def get_signature(func_node: Union[ast.FunctionDef, ast.AsyncFunctionDef]) -> Dict[str, Any]:
    """
    Build a nested signature dict for a FunctionDef or AsyncFunctionDef node:
      - parameters: list of {name: str, annotation: Optional[str], default: Optional[str]}
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
        sig['parameters'].append({'name': f'*{name}', 'annotation': annotation, 'default': None})
    # Keyword-only args
    for kwarg, default in zip(args.kwonlyargs, args.kw_defaults):
        name = kwarg.arg
        annotation = ast.unparse(kwarg.annotation) if kwarg.annotation else None
        default_str = ast.unparse(default) if default is not None else None
        sig['parameters'].append({'name': name, 'annotation': annotation, 'default': default_str})
    # Kwarg (**kwargs)
    if args.kwarg:
        name = args.kwarg.arg
        annotation = ast.unparse(args.kwarg.annotation) if args.kwarg.annotation else None
        sig['parameters'].append({'name': f'**{name}', 'annotation': annotation, 'default': None})
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
      - imports: list of {'module': str, 'alias': Optional[str]}
      - constants: list of {'name': str, 'value': Any}
      - functions: list of {
            'name': str,
            'signature': {parameters: [...], returns: ...},
            'docstring': Optional[str],
            'decorators': List[str],
            'calls': List[str]
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
      - todos: list of TODO comment strings
    """
    path = Path(file_path)
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(file_path))

    # Extract TODO comments
    todos = TODO_PATTERN.findall(source)

    # Module-level docstring
    module_docstring = ast.get_docstring(tree)

    # Imports
    imports: List[Dict[str, Optional[str]]] = []
    imported_names = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                alias_name = alias.asname or alias.name
                imports.append({'module': alias.name, 'alias': alias.asname})
                imported_names.add(alias_name)
        elif isinstance(node, ast.ImportFrom):
            module_name = node.module or ""
            for alias in node.names:
                if alias.name == "*":
                    continue
                full_name = f"{module_name}.{alias.name}" if module_name else alias.name
                alias_name = alias.asname or alias.name
                imports.append({'module': full_name, 'alias': alias.asname})
                imported_names.add(alias_name)

    # Global constants
    constants: List[Dict[str, Any]] = []
    for node in tree.body:
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    constants.append({'name': t.id, 'value': node.value.value})

    # Collect callable identifiers: top-level functions and imported names
    defined_functions = {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}
    callable_names = defined_functions.union(imported_names)

    # Helper to collect calls in a node
    def collect_calls(node: ast.AST) -> List[str]:
        calls = set()
        for sub in ast.walk(node):
            if isinstance(sub, ast.Call):
                func = sub.func
                if isinstance(func, ast.Name) and func.id in callable_names:
                    calls.add(func.id)
                elif isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
                    owner = func.value.id
                    method = func.attr
                    if owner in imported_names or owner in defined_functions:
                        calls.add(f"{owner}.{method}")
        return sorted(calls)

    # Functions
    functions: List[Dict[str, Any]] = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            func_info = {
                'name': node.name,
                'signature': get_signature(node),
                'docstring': ast.get_docstring(node),
                'decorators': [ast.unparse(d) for d in node.decorator_list],
                'calls': collect_calls(node)
            }
            functions.append(func_info)

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
                    method_info = {
                        'name': child.name,
                        'signature': get_signature(child),
                        'docstring': ast.get_docstring(child),
                        'decorators': [ast.unparse(d) for d in child.decorator_list],
                        'calls': collect_calls(child)
                    }
                    class_info['methods'].append(method_info)
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
        'functions': functions,
        'classes': classes,
        'main_guard': main_guard,
        'todos': todos
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
