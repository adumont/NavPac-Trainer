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

TBD

# Key decisions

TBD