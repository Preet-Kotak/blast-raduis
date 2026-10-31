"""
blast.core.pypi_diff — Real API diff using packages downloaded from PyPI.

Downloads two versions of a package, extracts the source, and AST-parses
the top-level public names to find what was removed between versions.

Falls back to the fakelibs approach if the package isn't on PyPI or the
download fails.
"""

import ast
import os
import tempfile
import zipfile
from functools import lru_cache
from typing import Optional

import requests as http

PYPI_JSON_URL = "https://pypi.org/pypi/{package}/{version}/json"
CACHE_DIR = os.path.join(tempfile.gettempdir(), "blast_radius_pypi_cache")


# ── Public API ─────────────────────────────────────────────────────────────────

def diff_versions(dep: str, from_ver: str, to_ver: str) -> list[str]:
    """
    Return names present in `from_ver` but absent in `to_ver`.

    Tries PyPI first; falls back to fakelibs if unavailable.

    Args:
        dep:      Package name as on PyPI (e.g. "discord.py", "requests").
        from_ver: Old version string (e.g. "1.7.3").
        to_ver:   New version string (e.g. "2.0.0").

    Returns:
        Sorted list of removed top-level public names.
    """
    try:
        names_old = _get_public_names(dep, from_ver)
        names_new = _get_public_names(dep, to_ver)
        removed = sorted(names_old - names_new)
        return removed
    except Exception as exc:
        # Fall back to fakelibs if PyPI fetch fails
        try:
            from blast.core.apidiff import diff_versions as _fakelib_diff
            return _fakelib_diff(dep, from_ver, to_ver)
        except Exception:
            return []


def get_package_versions(dep: str) -> list[str]:
    """
    Return all available versions for a package on PyPI, newest first.

    Args:
        dep: Package name as on PyPI.

    Returns:
        List of version strings, or empty list if package not found.
    """
    try:
        resp = http.get(
            f"https://pypi.org/pypi/{dep}/json",
            timeout=10,
            headers={"Accept": "application/json"},
        )
        if resp.status_code != 200:
            return []
        data = resp.json()
        versions = list(data.get("releases", {}).keys())

        # Filter to stable releases only (no alpha/beta/rc/dev)
        import re as _re
        versions = [
            v for v in versions
            if not _re.search(r'(a|b|rc|dev|post|alpha|beta)\d*', v, _re.IGNORECASE)
        ]

        # Sort using proper semantic versioning (newest first)
        def _ver_key(v: str):
            parts = []
            for part in v.replace("-", ".").split("."):
                num = ""
                for ch in part:
                    if ch.isdigit():
                        num += ch
                    else:
                        break
                parts.append(int(num) if num else 0)
            return parts

        versions.sort(key=_ver_key, reverse=True)
        return versions
    except Exception:
        return []


# ── Download + extract ─────────────────────────────────────────────────────────

@lru_cache(maxsize=20)
def _get_public_names(dep: str, version: str) -> frozenset:
    """
    Download a package version from PyPI and return its public names.
    Result is cached so repeated calls for the same version are free.
    """
    whl_path = _get_or_download_wheel(dep, version)
    if whl_path is None:
        return frozenset()
    names = _extract_names_from_wheel(whl_path, dep)
    return frozenset(names)


def _get_or_download_wheel(dep: str, version: str) -> Optional[str]:
    """
    Return path to a cached .whl for dep==version, downloading if needed.
    Returns None if the package/version isn't available on PyPI.
    """
    os.makedirs(CACHE_DIR, exist_ok=True)

    # Normalise package name for filename (e.g. "discord.py" → "discord_py")
    safe_name = dep.replace(".", "_").replace("-", "_")
    cache_path = os.path.join(CACHE_DIR, f"{safe_name}-{version}.whl")

    if os.path.exists(cache_path):
        return cache_path

    # Fetch PyPI metadata for this version
    url = PYPI_JSON_URL.format(package=dep, version=version)
    try:
        resp = http.get(url, timeout=15, headers={"Accept": "application/json"})
    except Exception:
        return None

    if resp.status_code != 200:
        return None

    data = resp.json()
    whl_url = _pick_wheel_url(data)
    if whl_url is None:
        # No wheel available — try sdist
        whl_url = _pick_sdist_url(data)
    if whl_url is None:
        return None

    # Download
    try:
        dl = http.get(whl_url, timeout=60, stream=True)
        dl.raise_for_status()
        with open(cache_path, "wb") as fh:
            for chunk in dl.iter_content(chunk_size=65536):
                fh.write(chunk)
        return cache_path
    except Exception:
        if os.path.exists(cache_path):
            os.remove(cache_path)
        return None


def _pick_wheel_url(pypi_data: dict) -> Optional[str]:
    """Pick the best (pure-Python or any) wheel from PyPI release data."""
    urls = pypi_data.get("urls", [])
    # Prefer py3 universal wheel, then any wheel
    wheels = [u for u in urls if u["filename"].endswith(".whl")]
    if not wheels:
        return None
    # Prefer py3-none-any, then cp3x-none-any, then anything
    for priority in ("py3-none-any", "py2.py3-none-any", "cp3"):
        for w in wheels:
            if priority in w["filename"]:
                return w["url"]
    return wheels[0]["url"]


def _pick_sdist_url(pypi_data: dict) -> Optional[str]:
    """Fall back to sdist (tar.gz) if no wheel is available."""
    urls = pypi_data.get("urls", [])
    for u in urls:
        if u["filename"].endswith(".tar.gz"):
            return u["url"]
    return None


# ── Name extraction ────────────────────────────────────────────────────────────

def _extract_names_from_wheel(whl_path: str, dep: str) -> set[str]:
    """
    Open a .whl (zip) file and extract public names from the package's
    top-level __init__.py (or the closest equivalent).
    """
    # Normalise: "discord.py" → "discord", "discord-py" → "discord"
    pkg_name = dep.replace(".py", "").replace("-", "_").replace(".", "_")

    names: set[str] = set()
    try:
        with zipfile.ZipFile(whl_path, "r") as zf:
            all_files = zf.namelist()

            # Find __init__.py candidates, best match first
            candidates = _rank_init_candidates(all_files, pkg_name)

            for candidate in candidates[:3]:  # try top 3
                try:
                    source = zf.read(candidate).decode("utf-8", errors="replace")
                    found = _extract_names_from_source(source)
                    if found:
                        names.update(found)
                        break
                except Exception:
                    continue

    except zipfile.BadZipFile:
        # Might be a tar.gz — try extracting differently
        names = _extract_names_from_sdist(whl_path, pkg_name)

    return names


def _rank_init_candidates(all_files: list[str], pkg_name: str) -> list[str]:
    """
    Return __init__.py files ranked by relevance to pkg_name.
    Prefers exact package match, then any top-level __init__.py.
    """
    exact = []
    close = []
    fallback = []

    for f in all_files:
        if not f.endswith("__init__.py"):
            continue
        parts = f.replace("\\", "/").split("/")
        if len(parts) == 2 and parts[0].lower().replace("-", "_") == pkg_name.lower():
            exact.append(f)
        elif len(parts) == 2:
            close.append(f)
        else:
            fallback.append(f)

    return exact + close + fallback


def _extract_names_from_sdist(path: str, pkg_name: str) -> set[str]:
    """Try to extract names from a .tar.gz sdist."""
    import tarfile
    names: set[str] = set()
    try:
        with tarfile.open(path, "r:gz") as tf:
            for member in tf.getmembers():
                if not member.name.endswith("__init__.py"):
                    continue
                parts = member.name.replace("\\", "/").split("/")
                # e.g. requests-2.28.0/requests/__init__.py
                if len(parts) >= 2 and parts[-2].lower().replace("-", "_") == pkg_name.lower():
                    f = tf.extractfile(member)
                    if f:
                        source = f.read().decode("utf-8", errors="replace")
                        found = _extract_names_from_source(source)
                        if found:
                            names.update(found)
                            break
    except Exception:
        pass
    return names


def _extract_names_from_source(source: str) -> set[str]:
    """
    AST-parse source and return top-level public names.
    Respects __all__ if defined.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return set()

    names: set[str] = set()
    all_list: Optional[list] = None

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if not node.name.startswith("_"):
                names.add(node.name)

        elif isinstance(node, ast.ClassDef):
            if not node.name.startswith("_"):
                names.add(node.name)

        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    if target.id == "__all__":
                        if isinstance(node.value, (ast.List, ast.Tuple)):
                            all_list = [
                                elt.s for elt in node.value.elts
                                if isinstance(elt, ast.Constant)
                                and isinstance(elt.s, str)
                            ]
                    elif not target.id.startswith("_") and target.id.isupper():
                        names.add(target.id)

        # Handle `from .submodule import Name` re-exports
        elif isinstance(node, ast.ImportFrom):
            if node.level and node.level > 0:  # relative import = re-export
                for alias in node.names:
                    exported = alias.asname or alias.name
                    if not exported.startswith("_"):
                        names.add(exported)

    return set(all_list) if all_list is not None else names
