# CDF Extractor TDD Training

Training repository for building Cognite Data Fusion (CDF) extractors with test-driven development. The exercise copies document metadata and files from a source CDF space (`isp_CLOV`) to a target space (`isp_Target`), using the [extractor-utils](https://github.com/cognitedata/python-extractor-utils) framework.

## Repository layout

| Path | Purpose |
|------|---------|
| [`dmsextractor/`](dmsextractor/) | Reference implementation and full test suite (unit + integration) |
| [`tddextractexercise/`](tddextractexercise/) | Hands-on starting point — implement the extractor yourself via TDD |
| [`customrestextractor/`](customrestextractor/) | Seeds source RAW metadata and files into CDF (simulates an external REST source) |

In production, the source would be an external system. For this training exercise, source data is pre-populated in CDF so you can focus on extraction logic and tests.

## Extractor requirements

The contract to satisfy (from [`tddextractexercise/extractor.py`](tddextractexercise/extractor.py)):

| Requirement | Expected behavior |
|-------------|-------------------|
| Read source | RAW metadata and Data Modeling files from config-defined source |
| Write target | RAW metadata and Data Modeling files to config-defined target space |
| Naming | Prefix target `name` and `external_id` with `Target_` |
| Marking | Set `sourceContext` to `fromDMS` |
| Space | Create the target space from config if it does not exist |
| Fidelity | Preserve file bytes and metadata mapping |

Reference implementation: [`dmsextractor/extractor.py`](dmsextractor/extractor.py).

## Prerequisites

- Python 3.11 or later
- Access to a CDF project with OAuth client credentials
- Source data in CDF (`TEST_RAW_DATABASE` / `TEST_METADATA_TABLE`, files in `isp_CLOV`) — typically seeded by running `customrestextractor` once before the session

## Setup

### 1. Install dependencies

Using [uv](https://docs.astral.sh/uv/) (recommended):

```bash
uv sync --group dev
uv pip install pytest
```

Or with pip:

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .
pip install pytest ruff mypy pre-commit
```

### 2. Configure environment variables

Create a `.env` file in the repository root (this file is gitignored). Config YAML files reference these variables via `${COGNITE_*}` placeholders:

```bash
COGNITE_BASE_URL=https://<cluster>.cognitedata.com
COGNITE_PROJECT=<your-project>
COGNITE_TOKEN_URL=https://login.microsoftonline.com/<tenant-id>/oauth2/v2.0/token
COGNITE_CLIENT_ID=<client-id>
COGNITE_CLIENT_SECRET=<client-secret>
```

| Variable | Description |
|----------|-------------|
| `COGNITE_BASE_URL` | CDF cluster base URL (also used as OAuth scope prefix) |
| `COGNITE_PROJECT` | CDF project name |
| `COGNITE_TOKEN_URL` | OAuth 2.0 token endpoint for your identity provider |
| `COGNITE_CLIENT_ID` | OAuth client ID |
| `COGNITE_CLIENT_SECRET` | OAuth client secret |

Load the variables into your shell before running extractors or integration tests, for example:

```bash
set -a && source .env && set +a
```

## Running extractors

Run from the repository root so Python can resolve the local packages.

### Reference extractor (`dmsextractor`)

```bash
python -m dmsextractor --config dmsextractor/config.yaml
```

Config defines source RAW (`TEST_RAW_DATABASE`), target RAW (`TEST_RAW_TARGET`), and target space (`isp_Target`). Run this once before integration tests so target data exists.

### Hands-on exercise (`tddextractexercise`)

```bash
python -m tddextractexercise --config dmsextractor/config.yaml
```

Start from the stub in [`tddextractexercise/extractor.py`](tddextractexercise/extractor.py) and implement `process_metadata`, `process_row`, and `run_extractor` using TDD. Use the same config as `dmsextractor` or provide your own YAML with the same structure.

### Source data seeder (`customrestextractor`)

Populates source RAW tables and files in `isp_CLOV`. Requires a separate config file with site/API settings (see `config.yaml.old` for an example layout). Run once to prepare the training environment:

```bash
python -m customrestextractor --config <path-to-customrestextractor-config.yaml>
```

## Running tests

### Unit tests (no CDF, no `.env`)

Fast tests with mocked Cognite client calls. Safe to run anywhere.

```bash
pytest dmsextractor/tests/unit -v
pytest tddextractexercise/tests/unit -v
```

Unit test config uses static placeholder values in [`dmsextractor/tests/unit/config.yaml`](dmsextractor/tests/unit/config.yaml) — no network or secrets required.

### Integration tests (live CDF)

Requires `.env` credentials and a prior successful run of `dmsextractor` so target RAW rows and files exist.

```bash
# 1. Populate target (if not already done)
python -m dmsextractor --config dmsextractor/config.yaml

# 2. Run integration tests
pytest dmsextractor/tests/integration/ \
  --config dmsextractor/tests/integration/config.yaml \
  -v
```

Integration tests verify end-to-end contracts against live CDF:

| Test | Contract verified |
|------|-------------------|
| `test_target_metadata_matches_expected_transform_from_source` | RAW transform matches `process_metadata()` |
| `test_target_file_bytes_equal_source_file_bytes` | Binary fidelity |
| `test_target_file_metadata_preserved_from_source` | MIME type, name prefix, `sourceContext`, `sourceId` |
| `test_target_raw_and_file_are_linked` | RAW external ID points to a downloadable file |
| `test_source_rows_with_files_have_target_rows` | No silent skips |

## Typical training workflow

1. Review requirements and the stub in `tddextractexercise/extractor.py`.
2. Write unit tests for `process_metadata`, then implement until green.
3. Add mocked unit tests for `process_row` (skip missing source, MIME type, `sourceContext`, external IDs).
4. Wire `run_extractor` with extractor-utils and run against CDF.
5. Run integration tests to validate contracts across RAW and Data Modeling layers.
6. Compare your solution with `dmsextractor/` when finished.

## Commands cheat sheet

```bash
# Unit tests (no CDF)
pytest dmsextractor/tests/unit -v
pytest tddextractexercise/tests/unit -v

# Run reference extractor
python -m dmsextractor --config dmsextractor/config.yaml

# Integration tests (needs .env + pre-run extractor)
pytest dmsextractor/tests/integration/ \
  --config dmsextractor/tests/integration/config.yaml \
  -v
```
