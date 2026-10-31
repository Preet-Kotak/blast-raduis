"""
blast.core.apidiff — Detect names removed between two library versions.

Compares the top-level public names exported by two versions of a fake library
using AST parsing. Returns the list of names present in v1 but missing in v2.

Works against the fakelibs/ directory structure:
    fakelibs/<dep>/v1/__init__.py
    fakelibs/<dep>/v2/__init__.py
"""

import ast
import os


# Location of fakelibs relative to the project root.
# Resolved at runtime so it works regardless of cwd.
_FAKELIBS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "fakelibs",
)


def diff_versions(dep: str, from_ver: str, to_ver: str) -> list[str]:
    """
    Return names that were in `from_ver` but are absent in `to_ver`.

    Args:
        dep:       Package name (e.g. "fakehttp").
        from_ver:  Old version string (e.g. "1.0").
        to_ver:    New version string (e.g. "2.0").

    Returns:
        Sorted list of removed top-level names.
        Empty list if either version directory doesn't exist.
    """
    v1_path = _find_version_path(dep, from_ver)
    v2_path = _find_version_path(dep, to_ver)

    if v1_path is None or v2_path is None:
        return []

    names_v1 = _extract_public_names(v1_path)
    names_v2 = _extract_public_names(v2_path)

    removed = sorted(names_v1 - names_v2)
    return removed


def get_removed_names(dep: str, from_ver: str, to_ver: str) -> list[str]:
    """Alias for diff_versions — matches the service layer naming."""
    return diff_versions(dep, from_ver, to_ver)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _find_version_path(dep: str, version: str) -> str | None:
    """
    Locate the __init__.py for a given dep version under fakelibs/.

    Tries:
      fakelibs/<dep>/v<version>/__init__.py   (e.g. v1.0 → v1)
      fakelibs/<dep>/<version>/__init__.py    (exact match)
    """
    # Normalise: "1.0" → "v1", "2.0" → "v2", "1" → "v1"
    short = version.split(".")[0]
    candidates = [
        os.path.join(_FAKELIBS_DIR, dep, f"v{short}", "__init__.py"),
        os.path.join(_FAKELIBS_DIR, dep, f"v{version}", "__init__.py"),
        os.path.join(_FAKELIBS_DIR, dep, version, "__init__.py"),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return None


def _extract_public_names(init_path: str) -> set[str]:
    """
    Parse a __init__.py file and return all top-level public names.

    Collects:
      - Top-level function definitions (def foo)
      - Top-level class definitions (class Foo)
      - Top-level assignments that look like constants (UPPER_CASE)
      - Names listed in __all__ if present
    """
    with open(init_path, encoding="utf-8") as fh:
        source = fh.read()

    try:
        tree = ast.parse(source, filename=init_path)
    except SyntaxError:
        return set()

    names: set[str] = set()
    all_list: list[str] | None = None

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if not node.name.startswith("_"):
                names.add(node.name)

        elif isinstance(node, ast.ClassDef):
            if not node.name.startswith("_"):
                names.add(node.name)

        elif isinstance(node, ast.Assign):
            # Check for __all__ = [...]
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__all__":
                    if isinstance(node.value, (ast.List, ast.Tuple)):
                        all_list = [
                            elt.s for elt in node.value.elts
                            if isinstance(elt, ast.Constant) and isinstance(elt.s, str)
                        ]
                # Top-level CONSTANT = value
                elif isinstance(target, ast.Name) and not target.id.startswith("_"):
                    if target.id.isupper():
                        names.add(target.id)

    # If __all__ is defined, it's the authoritative public API
    if all_list is not None:
        return set(all_list)

    return names
