# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

`ylearn` — a personal knowledge system that ingests scattered life-advice
material (YouTube transcripts, book excerpts), distills it into sourced
"advice cards" per life-domain, and answers free-form questions by
retrieving and synthesizing the relevant cards. See `docs/VISION.md` for
why it exists and `docs/ARCHITECTURE.md` for the full data-flow diagram
and module responsibility table — read both before making structural
changes; this file only covers what those two don't.

## Commands

```bash
# Install the only required dependency
pip install -r requirements.txt

# Run the whole suite (24 tests, no network/API key needed)
python -m unittest discover -s tests -t tests

# Run a single test file / class / method (must cd into tests/ — see below)
cd tests && python -m unittest test_textutil.TestSplitSentences.test_basic

# CLI entry points (run from repo root)
PYTHONPATH=src python -m ylearn.cli domains
PYTHONPATH=src python -m ylearn.cli ingest --text "제목|저자|본문"
PYTHONPATH=src python -m ylearn.cli ingest --youtube "<url>"
PYTHONPATH=src python -m ylearn.cli ask "<question>"
PYTHONPATH=src python -m ylearn.cli stats
```

There is no build step, linter, or formatter configured in this repo — it's
pure-stdlib-plus-PyYAML Python with no `pyproject.toml`/`setup.cfg`.

Tests import `ylearn.*` via `tests/_pathfix.py`, which inserts `src/` onto
`sys.path` — that's why single-test invocation must run with `tests/` as
the working directory (or top-level dir for `unittest discover`), not
`PYTHONPATH=src` from the repo root.

## Architecture points that span multiple files

- **Everything optional-degrades to a working pipeline.** `anthropic`,
  `youtube-transcript-api`, and `yt-dlp` are all optional imports.
  `Settings.from_env()` (`config.py`) picks `AnthropicDistiller` only if
  `ANTHROPIC_API_KEY` is set and importable; `make_default_distiller()` in
  `distill/llm.py` otherwise falls back to `ExtractiveFallbackDistiller`
  (regex/keyword heuristics, zero dependencies). Any change to the
  ingest/distill layers must keep this fallback path fully functional —
  it's what the test suite runs against, not the Anthropic path.
- **Two swap points are the intended extension seams**, both already
  interface-shaped for it:
  - New source types (podcast, e-library, Aladin...) implement
    `SourceAdapter.fetch(ref) -> Fetched` (`ingest/base.py`) — nothing else
    in the pipeline needs to change.
  - Swapping TF-IDF for real embeddings means keeping
    `TfidfIndex.add_document` / `.build` / `.search` (`retrieval.py`) as
    the contract; `pipeline.ask()` only calls through that surface.
- **`Pipeline` (`pipeline.py`) is the only orchestrator** — it wires
  `Settings` → `Store` → `Distiller` → `domains` together and is what both
  `cli.py` and the tests construct directly (often with an explicit
  `distiller=ExtractiveFallbackDistiller()` override to avoid needing an
  API key). `ingest()` dedupes by source URL before fetching/chunking a
  second time — do the existing-source check first in any change to that
  method, or duplicate ingests will silently re-run distillation.
- **Domain taxonomy lives in `data/domains.yaml`, not code** —
  `config.Domain` / `load_domains()` just deserialize it. Adding or
  renaming a life-domain never requires a code change.
- **IDs are opaque prefixed UUIDs** (`src_`, `chk_`, `adv_` — see
  `models._new_id`), and `Chunk`/`AdviceCard` always carry back-references
  (`source_id`, `chunk_id`) so every advice card can be traced to the exact
  chunk and source it came from — don't add a card-producing path that
  skips setting these.
- **Storage is a single SQLite file** (`store.py`) with three tables
  (`sources`, `chunks`, `advice_cards`) and no migration framework —
  schema changes are `CREATE TABLE IF NOT EXISTS` edits applied directly.
