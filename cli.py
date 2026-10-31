"""
Blast Radius — CLI

Usage:
    python cli.py check <repo_path> <dep> <version>

Example:
    python cli.py check sample_repo fakehttp 2.0
"""

import os
import sys


def _setup_mongo():
    """Read MONGO_URI from secrets.toml or env before importing blast modules."""
    uri = os.environ.get("MONGO_URI", "")
    if not uri:
        toml_path = os.path.join(os.path.dirname(__file__), ".streamlit", "secrets.toml")
        if os.path.exists(toml_path):
            with open(toml_path, encoding="utf-8") as f:
                for line in f:
                    if line.strip().startswith("MONGO_URI"):
                        uri = line.split("=", 1)[1].strip().strip('"').strip("'")
                        os.environ["MONGO_URI"] = uri
                        break


def _colour(text: str, code: str) -> str:
    """Wrap text in ANSI colour if stdout is a terminal."""
    if sys.stdout.isatty():
        return f"\033[{code}m{text}\033[0m"
    return text


RED    = lambda t: _colour(t, "31")
YELLOW = lambda t: _colour(t, "33")
GREEN  = lambda t: _colour(t, "32")
BOLD   = lambda t: _colour(t, "1")
DIM    = lambda t: _colour(t, "2")


def cmd_check(repo_path: str, dep: str, version: str) -> int:
    """
    Run blast radius and print a grouped report.
    Returns exit code: 0 = safe, 1 = unsafe, 2 = error.
    """
    from blast.core.service import (
        ingest_repo,
        simulate_bump,
        get_affected_files,
        get_fix_order,
        get_api_diff,
        get_bump_history,
    )

    width = 60
    print()
    print(BOLD("  BLAST RADIUS"))
    print(DIM(f"  {dep}  →  {version}"))
    print(DIM("  " + "─" * (width - 2)))

    # Ingest
    try:
        print(DIM(f"  Ingesting {repo_path}…"))
        repo_id = ingest_repo(repo_path)
    except Exception as exc:
        print(RED(f"  ✗ Ingest failed: {exc}"))
        return 2

    # Simulate
    try:
        result   = simulate_bump(repo_id, dep, version)
        bump_id  = result["bump_id"]
        affected = get_affected_files(bump_id)
        fix_order = get_fix_order(bump_id)
        removed  = get_api_diff(dep, "1.0", version)
    except Exception as exc:
        print(RED(f"  ✗ Simulation failed: {exc}"))
        return 2

    direct     = [f for f in affected if f["label"] == "DIRECT"]
    transitive = [f for f in affected if f["label"] == "TRANSITIVE"]
    safe       = [f for f in affected if f["label"] == "SAFE"]

    # ── Banner ────────────────────────────────────────────────────────────────
    print()
    if result["is_safe"]:
        print(GREEN(f"  ✓ SAFE TO BUMP — no files affected"))
    else:
        unsafe = len(direct) + len(transitive)
        print(RED(f"  ✗ NOT SAFE — {unsafe} file(s) need updating"))

    # Removed names
    if removed:
        print(DIM(f"\n  Removed names: ") + ", ".join(f"`{n}`" for n in removed))

    # ── DIRECT ────────────────────────────────────────────────────────────────
    if direct:
        print()
        print(RED(BOLD(f"  DIRECT  ({len(direct)} file(s) — call removed names)")))
        for f in direct:
            print(f"    {f['path']}")
            usages = f.get("usages", [])
            if usages:
                for u in usages:
                    line_info = DIM(f"line {u['line']:>3d}")
                    name_info = RED(f"{u['name']:<14s}")
                    snippet   = DIM(u["snippet"])
                    print(f"      {line_info}  {name_info}  {snippet}")
            else:
                print(DIM("      (imports dep — no removed-name calls detected, review manually)"))

    # ── TRANSITIVE ────────────────────────────────────────────────────────────
    if transitive:
        print()
        print(YELLOW(BOLD(f"  TRANSITIVE  ({len(transitive)} file(s) — import affected files)")))
        for f in transitive:
            via = f.get("via") or "?"
            print(f"    {f['path']:<40s}  " + DIM(f"via {via}"))

    # ── SAFE ──────────────────────────────────────────────────────────────────
    if safe:
        print()
        safe_paths = ", ".join(f["path"] for f in safe)
        print(GREEN(BOLD(f"  SAFE  ({len(safe)} file(s))")))
        print(DIM(f"    {safe_paths}"))

    # ── Fix order ─────────────────────────────────────────────────────────────
    if fix_order:
        print()
        print(BOLD("  FIX ORDER  (bottom-up — fix leaves first)"))
        for i, path in enumerate(fix_order, 1):
            print(f"    {DIM(str(i) + '.')}  {path}")

    # ── History warning ───────────────────────────────────────────────────────
    try:
        history = get_bump_history(repo_id, dep)
        if len(history) > 1 and not history[1]["is_safe"]:
            prev = history[1]
            print()
            print(YELLOW(
                f"  ⚠  Last attempt ({prev['ran_at'][:10]}) was also unsafe "
                f"({prev['affected_count']} file(s))."
            ))
    except Exception:
        pass

    print()
    return 0 if result["is_safe"] else 1


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    command = sys.argv[1]

    if command == "check":
        if len(sys.argv) != 5:
            print("Usage: python cli.py check <repo_path> <dep> <version>")
            sys.exit(2)
        _setup_mongo()
        code = cmd_check(sys.argv[2], sys.argv[3], sys.argv[4])
        sys.exit(code)
    else:
        print(f"Unknown command: {command}")
        print("Available commands: check")
        sys.exit(2)


if __name__ == "__main__":
    main()
