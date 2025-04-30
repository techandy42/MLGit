from pathlib import Path
import ast
import re
from typing import Any, Dict, List, Optional, Union

TODO_PATTERN = re.compile(r'#\s*TODO[:\s]*(.*)')

def make_signature(func_node: ast.FunctionDef) -> str:
    """
    Generate a signature string for a FunctionDef or AsyncFunctionDef node.
    """
    try:
        # ast.unparse is available in Python 3.9+
        args_str = ast.unparse(func_node.args)
    except AttributeError:
        # Fallback: basic reconstruction
        args = []
        for arg in func_node.args.args:
            arg_str = arg.arg
            if arg.annotation:
                arg_str += f": {ast.unparse(arg.annotation)}"
            args.append(arg_str)
        if func_node.args.vararg:
            args.append(f"*{func_node.args.vararg.arg}")
        args_str = "(" + ", ".join(args) + ")"
    return f"{func_node.name}{args_str}"

def index_file(file_path: Union[str, Path]) -> Dict[str, Any]:
    """
    Parse and extract structured metadata from a Python file.

    Returns a dictionary with:
      - module: module name or file path
      - docstring: module-level docstring
      - imports: list of {'module': str, 'alias': Optional[str]}
      - constants: list of {'name': str, 'value': Any}
      - functions: list of {
            'name': str, 'signature': str, 'docstring': Optional[str],
            'decorators': List[str], 'calls': List[str]
        }
      - classes: list of {
            'name': str, 'bases': List[str], 'docstring': Optional[str],
            'decorators': List[str], 'attributes': List[Dict], 'methods': List[Dict]
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
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append({'module': alias.name, 'alias': alias.asname})
        elif isinstance(node, ast.ImportFrom):
            module_name = node.module or ""
            for alias in node.names:
                if alias.name == "*":
                    continue
                full_name = f"{module_name}.{alias.name}" if module_name else alias.name
                imports.append({'module': full_name, 'alias': alias.asname})

    # Global constants (simple assignments with constant values)
    constants: List[Dict[str, Any]] = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            if all(isinstance(t, ast.Name) for t in node.targets) and isinstance(node.value, ast.Constant):
                for t in node.targets:
                    constants.append({'name': t.id, 'value': node.value.value})

    # Functions
    functions: List[Dict[str, Any]] = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            func_info = {
                'name': node.name,
                'signature': make_signature(node),
                'docstring': ast.get_docstring(node),
                'decorators': [ast.unparse(d) for d in node.decorator_list],
                'calls': []
            }
            # Collect function call names
            calls = set()
            for sub in ast.walk(node):
                if isinstance(sub, ast.Call):
                    if isinstance(sub.func, ast.Name):
                        calls.add(sub.func.id)
                    elif isinstance(sub.func, ast.Attribute):
                        calls.add(sub.func.attr)
            func_info['calls'] = sorted(calls)
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
                if isinstance(child, ast.Assign):
                    for t in child.targets:
                        if isinstance(t, ast.Name) and isinstance(child.value, ast.Constant):
                            class_info['attributes'].append({
                                'name': t.id,
                                'value': child.value.value
                            })
                elif isinstance(child, ast.FunctionDef):
                    method_info = {
                        'name': child.name,
                        'signature': make_signature(child),
                        'docstring': ast.get_docstring(child),
                        'decorators': [ast.unparse(d) for d in child.decorator_list]
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
    Index a list of Python files (e.g., an SCC), returning a list of
    metadata dictionaries for each file.
    """
    results = []
    for fp in file_paths:
        try:
            results.append(index_file(fp))
        except Exception as e:
            # You might choose to log or handle errors differently
            results.append({
                'module': str(fp),
                'error': str(e)
            })
    return results
