# AGENTS.md

Guidance for AI coding agents working in this repository.

## Project
Training repo for building a Cognite Data Fusion (CDF) extractor with
test-driven development, using the extractor-utils framework.

The extractor copies document metadata (RAW) and files (Data Modeling,
CogniteFile) from a source space (`isp_CLOV`) to a target space defined
in config.

Before you finish, run uv run mypy tddextractexercise and uv run ruff check, along with the tests.

- Package: `tddextractexercise/`
- Entry points to implement: `process_metadata`, `process_row`, `run_extractor`
- Unit tests: `tddextractexercise/tests/unit` (mocked client, no CDF, no .env)
- Integration tests: `tddextractexercise/tests/integration` (live CDF)

## Contract the extractor must satisfy
- Read RAW metadata and Data Modeling files from the config-defined source
- Write RAW metadata and files to the config-defined target
- Prefix target `name` and `external_id` with `Target_`
- Set `sourceContext` to `fromDMS`
- Create the target space from config if it does not exist
- Preserve file bytes and metadata (including the source MIME type)

## Working method: red/green TDD (always)
1. Write ONE failing test first. Run it and confirm it fails for the
   right reason. Show the failing output before writing any code.
2. Write the minimum code to make that test pass. Run it and confirm green.
3. Refactor only while tests are green.
4. Repeat in small increments. Never implement several behaviors at once.
5. Run the unit tests immediately after every code change.
6. Do not edit a test just to make it pass. If a test seems wrong, explain
   why and ask first.
7. Prefer commits that separate the red test from the green implementation.

## Writing good tests
- Also write tests that try to break the code: missing data, API errors,
  partial failures, empty results, not only the happy path.
- Design code to need few mocks: keep pure logic (for example
  `process_metadata`) separate from I/O.
- Avoid over-mocking. A mock that is too lenient can make a test prove nothing.
  Prefer specced mocks (`create_autospec`, or the SDK's `CogniteClientMock`)
  so wrong attribute names fail instead of passing silently.
- Use the exact attribute names of the SDK classes in tests and fixtures
  (for example, check `mime_type` vs `mimeType`, `source_id` vs `sourceId`).
- Import helpers (ID builders, filename builders) from the extractor.
  Never redefine production logic inside a test file.
- Patch `time.sleep` in retry tests so tests stay fast.
- Test error handling by making mocks raise `CogniteAPIError`.

## Integration tests
- They validate the contract against real CDF; they do not replace unit tests.
- Never run them without `.env` loaded and a prior successful extractor run.
- Do not commit credentials. `.env` is gitignored.
- Do not add hard-coded keys or client names without noting them in the README.

## Code style and safety
- Python 3.11 or later. Run `ruff` and `mypy` before finishing.
- Do not swallow errors silently. Failed rows must be counted or reported,
  not only logged.
- Think about ordering of side effects: do not write a RAW row that points to
  a file that may not exist yet.
- Keep changes small and focused. Do not refactor unrelated code.

## Commands
```bash
# Unit tests (no CDF)
pytest tddextractexercise/tests/unit -v

# Load credentials, run the extractor, run integration tests
set -a && source .env && set +a
python -m tddextractexercise --config tddextractexercise/config.yaml
pytest tddextractexercise/tests/integration/ \
  --config tddextractexercise/tests/integration/config.yaml -v
```

## Definition of done
- All unit tests green, written before the code they cover
- Integration tests green against live CDF
- No dead code, no stale comments, imports use `tddextractexercise`
- README paths match the actual package layout