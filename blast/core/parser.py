"""
blast.core.parser — AST-based import extractor.

Pure function: takes a file path, returns which local modules and
third-party packages it imports. No I/O beyond reading the file,
no database calls.
"""

import ast
import os
from typing import NamedTuple


class ParseResult(NamedTuple):
    local_imports: list[str]   # relative module paths (e.g. "api.client")
    third_party_deps: list[str]  # top-level package names (e.g. "fakehttp")


# Names that are part of the Python standard library at the top level.
# We skip these so they don't pollute the third-party dep list.
_STDLIB_TOP_LEVEL = frozenset({
    "abc", "ast", "asyncio", "base64", "builtins", "collections", "contextlib",
    "copy", "csv", "dataclasses", "datetime", "decimal", "enum", "functools",
    "glob", "hashlib", "http", "importlib", "inspect", "io", "itertools",
    "json", "logging", "math", "os", "pathlib", "pickle", "platform",
    "pprint", "queue", "random", "re", "shutil", "signal", "socket",
    "sqlite3", "ssl", "string", "struct", "subprocess", "sys", "tempfile",
    "textwrap", "threading", "time", "traceback", "typing", "unittest",
    "urllib", "uuid", "warnings", "weakref", "xml", "zipfile",
})


def parse_file(file_path: str, repo_root: str = "") -> ParseResult:
    """
    Parse a single Python file and return its import relationships.

    Args:
        file_path:  Absolute or relative path to the .py file.
        repo_root:  Root of the repo (used to resolve relative imports
                    into dotted module paths). If empty, the file's
                    directory is used as a fallback.

    Returns:
        ParseResult(local_imports, third_party_deps)
        - local_imports:     dotted names of modules inside the same repo
        - third_party_deps:  top-level names of external packages used
    """
    with open(file_path, encoding="utf-8", errors="replace") as fh:
        source = fh.read()

    try:
        tree = ast.parse(source, filename=file_path)
    except SyntaxError:
        # Unparseable file — return empty rather than crashing the whole ingest
        return ParseResult([], [])

    root = repo_root or os.path.dirname(os.path.abspath(file_path))

    local: list[str] = []
    third_party: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                _classify(top, alias.name, root, file_path, local, third_party)

        elif isinstance(node, ast.ImportFrom):
            if node.module is None:
                continue
            if node.level and node.level > 0:
                # Relative import — always local
                resolved = _resolve_relative(
                    node.module, node.level, file_path, root
                )
                if resolved and resolved not in local:
                    local.append(resolved)
            else:
                top = node.module.split(".")[0]
                _classify(top, node.module, root, file_path, local, third_party)
                # Also check if any imported name is itself a submodule
                # e.g. `from api import client` — "client" may be api/client.py
                for alias in node.names:
                    candidate = f"{node.module}.{alias.name}"
                    cand_file = os.path.join(root, candidate.replace(".", os.sep) + ".py")
                    cand_pkg  = os.path.join(root, candidate.replace(".", os.sep), "__init__.py")
                    if os.path.exists(cand_file) or os.path.exists(cand_pkg):
                        if candidate not in local:
                            local.append(candidate)

    return ParseResult(
        local_imports=sorted(set(local)),
        third_party_deps=sorted(set(third_party)),
    )


# ── Helpers ────────────────────────────────────────────────────────────────────

def _classify(
    top_level: str,
    full_name: str,
    repo_root: str,
    file_path: str,
    local: list,
    third_party: list,
) -> None:
    """Decide if an import is local (same repo) or third-party."""
    if top_level in _STDLIB_TOP_LEVEL:
        return  # standard library — ignore

    # Check if a matching file/package exists inside the repo
    candidate_file = os.path.join(repo_root, full_name.replace(".", os.sep) + ".py")
    candidate_pkg  = os.path.join(repo_root, full_name.replace(".", os.sep), "__init__.py")

    if os.path.exists(candidate_file) or os.path.exists(candidate_pkg):
        if full_name not in local:
            local.append(full_name)
    else:
        if top_level not in third_party:
            third_party.append(top_level)


def _resolve_relative(
    module: str, level: int, file_path: str, repo_root: str
) -> str:
    """
    Convert a relative import (e.g. `from ..utils import x`) into a
    dotted module path relative to repo_root.
    """
    parts = os.path.abspath(file_path).replace(repo_root, "").lstrip(os.sep)
    parts = parts.replace(os.sep, ".").rstrip(".py")
    # Go up `level` package levels
    segments = parts.split(".")
    if level >= len(segments):
        return module
    base = ".".join(segments[: len(segments) - level])
    return f"{base}.{module}" if base else module
