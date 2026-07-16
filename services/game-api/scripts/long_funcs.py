#!/usr/bin/env python3
"""Print every function >20 lines in the app package using ast."""

import ast
import sys
from pathlib import Path


def walk_functions(node, parent_name=""):
    """Yield (qualified_name, start_line, end_line) for each function/method."""
    for child in ast.iter_child_nodes(node):
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
            name = f"{parent_name}.{child.name}" if parent_name else child.name
            n_lines = child.end_lineno - child.lineno + 1
            if n_lines > 20:
                yield (name, child.lineno, child.end_lineno, n_lines)
        elif isinstance(child, ast.ClassDef):
            yield from walk_functions(child, f"{parent_name}.{child.name}" if parent_name else child.name)
        elif isinstance(child, (ast.Module,)):
            yield from walk_functions(child, parent_name)


def main():
    app_dir = Path(__file__).resolve().parent.parent / "app"
    if not app_dir.is_dir():
        print(f"ERROR: app directory not found at {app_dir}", file=sys.stderr)
        sys.exit(1)

    for py_file in sorted(app_dir.rglob("*.py")):
        rel = py_file.relative_to(app_dir.parent)
        try:
            source = py_file.read_text()
            tree = ast.parse(source, filename=str(py_file))
        except SyntaxError as e:
            print(f"SKIP {rel}: syntax error - {e}")
            continue

        long_funcs = list(walk_functions(tree))
        if long_funcs:
            print(f"\n--- {rel} ---")
            for name, start, end, lines in sorted(long_funcs, key=lambda x: x[1]):
                print(f"  {name}:{start}-{end} ({lines} lines)")


if __name__ == "__main__":
    main()
