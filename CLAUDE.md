# CLAUDE.md

Factor allocation research project. Full spec and milestones: `PLAN.md`. Read it at the start of every session.

## Working rules

- Work one milestone at a time (PLAN.md Section 7). Stop after its acceptance checks pass and summarize results. Do not start the next milestone without approval.
- Ask before making any decision listed in PLAN.md Section 12.
- Free public data only. Never use or suggest WRDS, CRSP, or Compustat data.
- If a data download fails or a URL can't be found, stop and ask the user to download the file manually into `data/raw/`.

## Research integrity (non-negotiable)

- No look-ahead: weights at date t use only data strictly before t. Weights chosen at t earn the return of t+1.
- No factor gets weight before its `pub_date`.
- Any normalization, hyperparameter tuning, or volatility estimate uses only past data.
- Every backtest run appends a row to `results/trials.csv`. Never delete rows.
- Report negative or null results as they are. Do not tune until a method beats the baseline.

## Code conventions

- Python 3.12, `uv`. Run `uv run pytest` and `uv run ruff check .` before declaring a task done.
- Logic in `src/factor_alloc/`; notebooks are for exploration only.
- All allocators follow the interface in PLAN.md Section 6.3.
- Returns are monthly decimals in wide DataFrames (index = month-end date, columns = factor id).
- Raw and processed data are gitignored. Store processed data as Parquet.
- Type hints and short docstrings on public functions. No em dashes in docs or the writeup.
