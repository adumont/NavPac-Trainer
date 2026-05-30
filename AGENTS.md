# Context

- uv based python lib, never bare `python`, always via `uv run`
- modular, not monolithic
- Pydantic models for all data
- Test before handover
- Language: only english!

## Testing and Code Quality

- pytest in tests/
- ruff for lint+format (run: `uv run ruff check --fix .` and `uv run ruff format`)
- Coverage: min 90% overall, 80% per file.
- cover Streamlit test with AppTest
- No ignores, Fix all
    S311: import secrets; secrets.randbelow(10) instead of random.randrange(10)

## Commit

- Clean commit, single line (small) or multiline (massive)
- Never `git add .`, only touched files
- Never `--no-ff` on merges — fast-forward only

# Architecture

- Two-repo: `celnav-core` (celestial nav library), `NavPac-Trainer` (Streamlit app)
- NavPac-Trainer depends on celnav-core via git URL: `git+https://github.com/adumont/celnav-core.git`
- `src/navpac/webapp/app.py` is the Streamlit app entry point
- `src/navpac/navigation.py` has DR simulation only (`mover_barco`, constants)
- `src/navpac/angulos.py` has NavPac-specific display formatters only
- `src/navpac/tipos.py` re-exports `Position` from celnav-core

# Key decisions

- celnav-core dependency: git URL, not local path (local path for dev only)
- Coverage `fail_under=80` accepted as target; current ~3% from navigation tests only
- Body names: English ("Sun", "Moon") not Spanish ("Sol", "Luna")
- `solve_fix_from_intercepts()` replaces both `lop.py` functions