# Blast Radius

> **Know what breaks before you upgrade a library.**

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Streamlit%20App-FF4B4B?style=for-the-badge)](https://blastradius.streamlit.app)
[![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?style=flat-square&logo=python)](https://www.python.org/)
[![MongoDB](https://img.shields.io/badge/MongoDB-Atlas-13AA52?style=flat-square&logo=mongodb)](https://www.mongodb.com/)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

---

## The Problem

Upgrading a library is a gamble. You know a new version exists, you might know it has security fixes, but you don't know **what breaks in your code**.

Existing tools like Dependabot and pip-audit tell you:
- ✓ A newer version is available
- ✓ Your version has a known vulnerability
- ✗ What it does to your code is left to you (or your tests, if you have them)

**Blast Radius answers the question they don't:**

1. **What breaks** — exact file and line, with the reason (removed function, renamed parameter, missing argument)
2. **How far it spreads** — every file hit indirectly through imports, with distance
3. **What to fix first** — safe fix order respecting dependencies and import cycles
4. **Did it break before** — real outcomes from your team, remembered across upgrades

---

## The Solution

Blast Radius parses your entire codebase, maps your import graph, compares library versions, and tells you exactly what will break—before you make the upgrade.

**Example:** Upgrading `pydantic 1.10 → 2.0`

```
pydantic 1.10 → 2.0

DO NOT BUMP YET

LIKELY BREAKS models/user.py line 6
  ConstrainedStr() not available in pydantic 2.0

LIKELY BREAKS models/user.py line 19
  @validator decorator removed, use @field_validator

CHECK THIS routes/users.py line 10
  response_model=UserResponse fails on instantiation

11 files affected: 8 break · 3 to check · 0 safe

Safe fix order:
1. models/user.py — Replace ConstrainedStr, update validators
2. models/item.py — Same changes
3. services/user_service.py — Update model instantiation
4. routes/users.py + routes/items.py — Retest
5. main.py — Final validation
```

---

## Features

### 🔍 Static Analysis
- Parses Python code using Python's `ast` module (nothing is run)
- Safe to analyze any public repository
- Detects direct calls, import chains, and validation signatures

### 📊 Graph Tracing
- Maps the full import dependency graph
- Uses MongoDB `$graphLookup` to trace cascading breakage
- Identifies import cycles automatically

### 📝 Historical Learning
- Remembers what actually broke in previous upgrades
- Adjusts severity labels based on real outcomes
- Stores history in MongoDB for continuous improvement

### 🎯 Fix Prioritization
- Topological sort for safe fix order
- Groups import cycles so they're fixed together
- Shows which files others depend on (must fix first)

---

## How It Works

### 6-Step Pipeline

1. **Read** — Parse every `.py` file with Python's `ast`. Nothing is run.
2. **Store** — Save files, imports, and calls as a snapshot in MongoDB.
3. **Compare** — Diff the library's old and new functions from PyPI.
4. **Trace** — Use `$graphLookup` to walk the import chain outwards.
5. **Judge** — Check every recorded call against the new function signature.
6. **Remember** — Save real outcomes and warn next time.

### Data Model

One **snapshot per commit** with collections for:

| Collection | Purpose |
|-----------|---------|
| `snapshots` | One ingested commit: counts, cycles, parent |
| `nodes` | One file: content hash, fan-in, has tests? |
| `edges` | One import with the calls it makes |
| `packages` | One library and its pinned version |
| `api_changes` | Cached diff of two library versions |
| `bump_runs` | One simulation and its real outcome |
| `advisories` | Known vulnerable version ranges |

---

## Why MongoDB

Five features doing real work:

| Feature | Why It Matters |
|---------|---------------|
| **Unique Index** | Same commit can't be stored twice, even with concurrent requests |
| **$graphLookup** | Walks import chains safely on cycles; records depth |
| **Aggregation Pipeline** | Compares commits file-by-file using content hashes |
| **$jsonSchema Validation** | Enforces required fields at the database level |
| **Documents as History** | Past outcomes are read back and change the next answer |

---

## Quick Start

### Live Demo
Try it now: **[blastradius.streamlit.app](https://blastradius.streamlit.app)**

Paste any public Python GitHub repo URL and pick a library to upgrade. Example:
```
github.com/miguelgrinberg/microblog → redis, elasticsearch, or jinja2
```

### Local Installation

```bash
# Clone the repo
git clone https://github.com/Preet-Kotak/blast-raduis
cd blast-raduis

# Install dependencies
pip install -r requirements.txt

# Run the Streamlit app
streamlit run app.py
```

### Docker (optional)
```bash
docker build -t blast-radius .
docker run -p 8501:8501 blast-radius
```

---

## Architecture

### Tech Stack

| Component | Choice | Why |
|-----------|--------|-----|
| **Parsing** | Python `ast` | Reads code without running it |
| **Version Rules** | `packaging` | Matches pip's version semantics exactly |
| **Dependencies** | `networkx` | Import cycles, topological sort |
| **Database** | MongoDB Atlas | Graphs, validation, history |
| **Web UI** | Streamlit | Pure Python, deployed for free |
| **Library Source** | PyPI JSON API | Compare any version without downloading |

### Why No AI?

Every warning points to a real line of code, so anyone can verify it. The same input always gives the same answer. A model's guess is harder to trust when you're deciding whether to ship.

---

## Limitations & Roadmap

### Current Limitations

- ⚠️ **Python only** — Other languages aren't supported yet
- ⚠️ **Root `requirements.txt` only** — `pyproject.toml`, `setup.py`, `Pipfile` not yet supported
- ⚠️ **Signature changes only** — Functions that change behavior while keeping the same signature aren't detected
- ⚠️ **Direct calls only** — Indirect calls (via variables, wrappers, `getattr`) are invisible
- ⚠️ **Public repos only** — Very large repos may time out on the free Streamlit server
- ⚠️ **Compiled libraries** — C-based libraries expose fewer functions to compare

### Coming Soon

1. Support `pyproject.toml`, `setup.py`, `Pipfile`
2. GitHub Action: post reports on every pull request
3. More languages: JavaScript (package.json) first
4. Release notes integration: catch behavioral changes too

---

## Example Use Cases

### Pydantic 1.10 → 2.0 Migration
Real migration pain across models → services → routes with 8+ breaking changes.

### Redis 5.0 → 6.0 Upgrade
Detect dropped parameters early; Blast Radius flags `Redis()` client construction before it breaks production.

### Flask-SQLAlchemy Version Bumps
Multi-layer dependencies; Blast Radius maps which queries, models, and routes are affected.

### Security Hotfixes
Teams urgently patch vulnerabilities when they know exactly what to fix and the effort required.

---

## Development

### Running Tests

```bash
# End-to-end tests against MongoDB Atlas
pytest tests/

# Lint
black . && flake8 .
```

### Contributing

We welcome contributions! Please:

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Issues & Feedback

Found a bug? Have a suggestion? [Open an issue](https://github.com/Preet-Kotak/blast-raduis/issues) or [start a discussion](https://github.com/Preet-Kotak/blast-raduis/discussions).

---



## FAQ

### Why not just run the tests?

Many files have no tests (the tool shows which ones), and Blast Radius answers **before** you change anything.

### How is this different from Dependabot?

Dependabot says an update exists. **Blast Radius says what it does to your code.**

### Why MongoDB, not a graph database?

One small graph per commit, plus documents, validation, and history. `$graphLookup` covers the walk.

### What if a function is called via a variable?

We can't see it—that's why labels say "likely", not "will". It's in our documented limitations.

### Can it analyze my repo?

Yes, any **public Python repo with a `requirements.txt`**. Paste its GitHub URL into the live app.

---

## License

This project is licensed under the [MIT License](LICENSE) — see the file for details.

---

## Acknowledgments

- **MongoDB** for the hands-on workshop and challenge track
- **n8n** for collaboration
- **SVNIT** for hosting UNCHARTED 2026
- Our testers who uncovered edge cases early

---

## Stay Connected

- 🔗 **Live App:** [blastradius.streamlit.app](https://blastradius.streamlit.app)
- 📦 **Source:** [github.com/Preet-Kotak/blast-raduis](https://github.com/Preet-Kotak/blast-raduis)
- 🐦 **Updates:** Follow for features and improvements

---

**Build boldly. Know what breaks. Upgrade sooner.** 🚀
