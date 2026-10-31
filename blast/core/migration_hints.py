"""
blast.core.migration_hints — Per-library migration guidance for removed names.

Maps (package, removed_name) → human-readable fix instruction.
Falls back to a generic message for unknown packages/names.
"""

# Structure: { "package_name": { "removed_name": "fix instruction" } }
_HINTS: dict[str, dict[str, str]] = {
    "pydantic": {
        "BaseSettings":               "Move to `pydantic-settings` package: `from pydantic_settings import BaseSettings`",
        "validator":                  "Replace with `@field_validator` decorator (pydantic v2)",
        "root_validator":             "Replace with `@model_validator(mode='before')` or `mode='after'`",
        "validate_arguments":         "Replace with `@validate_call` decorator (pydantic v2)",
        "validate_model":             "Use `model.model_validate(data)` instead",
        "ConstrainedStr":             "Use `Annotated[str, StringConstraints(...)]` instead",
        "ConstrainedInt":             "Use `Annotated[int, Field(ge=..., le=...)]` instead",
        "ConstrainedFloat":           "Use `Annotated[float, Field(ge=..., le=...)]` instead",
        "ConstrainedDecimal":         "Use `Annotated[Decimal, Field(...)]` instead",
        "ConstrainedBytes":           "Use `Annotated[bytes, Field(min_length=..., max_length=...)]` instead",
        "ConstrainedDate":            "Use `Annotated[date, Field(...)]` instead",
        "ConstrainedList":            "Use `Annotated[list, Field(min_length=..., max_length=...)]` instead",
        "ConstrainedSet":             "Use `Annotated[set, Field(min_length=..., max_length=...)]` instead",
        "ConstrainedFrozenSet":       "Use `Annotated[frozenset, Field(...)]` instead",
        "parse_raw_as":               "Use `TypeAdapter(T).validate_json(raw)` instead",
        "parse_file_as":              "Use `TypeAdapter(T).validate_json(Path(file).read_text())` instead",
        "parse_obj_as":               "Use `TypeAdapter(T).validate_python(obj)` instead",
        "SecretField":                "Use `Field(default=...) with SecretStr` type instead",
        "JsonWrapper":                "Use `Json[T]` annotation directly instead",
        "NoneStr":                    "Use `Optional[str]` instead",
        "NoneBytes":                  "Use `Optional[bytes]` instead",
        "NoneStrBytes":               "Use `Optional[Union[str, bytes]]` instead",
        "StrBytes":                   "Use `Union[str, bytes]` instead",
        "Protocol":                   "Use `typing.Protocol` from standard library instead",
        "Required":                   "Use `...` (Ellipsis) as default for required fields",
        "PyObject":                   "Use `ImportString` instead (pydantic v2)",
        "compiled":                   "Removed — pydantic v2 uses Rust core, no `compiled` flag needed",
        "stricturl":                  "Use `AnyUrl` with `UrlConstraints` instead",
        "create_model_from_namedtuple": "Use `create_model` directly with field annotations",
        "create_model_from_typeddict":  "Use `create_model` directly with field annotations",
    },
    "fakehttp": {
        "delete":    "fakehttp v2 removed `delete()` — use `session.request('DELETE', url)` instead",
        "HTTPError": "fakehttp v2 removed `HTTPError` — catch `Exception` or use `StatusError` instead",
    },
    "flask": {
        "Session": "Removed top-level `Session` class — use `flask.session` proxy object instead",
    },
}

_GENERIC = "Removed in this version — check the library's migration guide for a replacement."


def get_hint(package: str, name: str) -> str:
    """
    Return a migration hint for a specific removed name.

    Args:
        package: Package name as on PyPI (e.g. "pydantic").
        name:    Removed name (e.g. "BaseSettings").

    Returns:
        Human-readable fix instruction string.
    """
    pkg_hints = _HINTS.get(package, {})
    # Try exact match first, then case-insensitive
    return pkg_hints.get(name) or pkg_hints.get(name.lower()) or _GENERIC


def get_hints_for_file(package: str, usages: list[dict]) -> list[dict]:
    """
    Enrich a list of usage dicts with migration hints.

    Args:
        package: Package name.
        usages:  List of usage dicts from find_name_usages.

    Returns:
        Same list with a "hint" key added to each entry.
    """
    enriched = []
    seen_names: set[str] = set()
    for u in usages:
        entry = dict(u)
        name = u.get("name", "")
        entry["hint"] = get_hint(package, name)
        # Mark whether this is the first occurrence of this name
        entry["first_occurrence"] = name not in seen_names
        seen_names.add(name)
        enriched.append(entry)
    return enriched


def get_unique_hints(package: str, removed_names: list[str]) -> list[dict]:
    """
    Return one hint per removed name for a summary panel.

    Args:
        package:       Package name.
        removed_names: List of removed names from diff_versions.

    Returns:
        List of {"name": str, "hint": str} dicts.
    """
    return [
        {"name": name, "hint": get_hint(package, name)}
        for name in removed_names
    ]
