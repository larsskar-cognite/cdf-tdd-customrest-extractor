# TDD Training Session — Facilitator Script

**Duration:** 50 minutes  
**Audience:** Developers building CDF extractors with [extractor-utils](https://github.com/cognitedata/python-extractor-utils)  
**Repository:** [`cdf-tdd-customrest-extractor`](README.md)

---

## Learning outcomes (show on slide 1)

By the end of this session, participants will:

- Understand why manual/ad-hoc testing feels fine but misses real bugs
- Write focused unit tests (fast, mocked) before or alongside implementation
- Add integration tests that validate contracts against live CDF
- Recognize bug classes that TDD catches: prefix mismatches, API naming (`source_id` vs `sourceId`), metadata drift

---

## Session arc

| Act | Topic | Duration |
|-----|-------|----------|
| 1 | Motivation — building without TDD | 15 min |
| 2 | Unit TDD — red → green with mocks | 20 min |
| 3 | Integration tests against CDF | 12 min |
| 4 | Bug gallery and wrap-up | 3 min |

---

## Instructor prep checklist

Complete these **the day before** the session:

- [ ] CDF credentials working; load `.env` and verify connectivity
- [ ] Source data exists in CDF (`TEST_RAW_DATABASE`, files in `isp_CLOV`) — run `customrestextractor` if needed
- [ ] Run reference extractor once to populate target:

  ```bash
  set -a && source .env && set +a
  python -m dmsextractor --config dmsextractor/config.yaml
  ```

- [ ] Integration tests all green:

  ```bash
  pytest dmsextractor/tests/integration/ \
    --config dmsextractor/tests/integration/config.yaml \
    -v
  ```

- [ ] Unit tests all green (no `.env` required):

  ```bash
  pytest dmsextractor/tests/unit -v
  ```

- [ ] Prepare a git stash or branch with **bug-injected** `process_metadata` for Act 3 (see [Act 3.3 bug injection](#33-headline-bug-demo--prefix-mismatch-4-min))
- [ ] Terminal font size readable; `pytest -v` output visible on screen
- [ ] Do **not** show [`dmsextractor/extractor.py`](dmsextractor/extractor.py) until Act 3 (or the optional hands-on debrief)

---

## Commands cheat sheet (keep on screen)

```bash
# Unit tests (no CDF, no .env)
pytest dmsextractor/tests/unit -v
pytest tddextractexercise/tests/unit -v

# Run reference extractor (needs .env)
python -m dmsextractor --config dmsextractor/config.yaml

# Integration tests (needs .env + pre-run extractor)
pytest dmsextractor/tests/integration/ \
  --config dmsextractor/tests/integration/config.yaml \
  -v
```

---

## Act 1 — Motivation: building without TDD (15 min)

### 1.1 Frame the problem (3 min)

**Show:** [`tddextractexercise/extractor.py`](tddextractexercise/extractor.py) — the trainee starting point (`logging.info("Hello, world!")`).

**Talking points:**

- This is a CDF-to-CDF extractor exercise: copy document metadata and files from `isp_CLOV` → `isp_Target`.
- In production, the source would be an external REST system. Here, `customrestextractor` has already seeded source data in CDF so we can focus on extraction logic and tests.
- The extractor-utils pattern: `Config` + `run_extractor()` + `Extractor` wrapper in [`dmsextractor/__main__.py`](dmsextractor/__main__.py).
- One CDF project, two spaces: source pre-populated, target empty (until you run the extractor).

**Show requirements table** (slide 2 or README):

| Requirement | Expected behavior |
|-------------|-------------------|
| Read source | RAW metadata + DM files from config-defined source |
| Write target | RAW metadata + DM files to config-defined target space |
| Naming | Prefix target `name` and `external_id` with `Target_` |
| Marking | Set `sourceContext` to `fromDMS` |
| Space | Create target space from config if missing |
| Fidelity | File bytes and metadata mapping preserved |

---

### 1.2 "How we'd build it without TDD" (7 min)

**Use slides — do not live-code yet.** Walk through the ad-hoc mental model:

1. Read requirements → implement `process_metadata`, `process_row`, `run_extractor` in one sitting
2. Run extractor:

   ```bash
   python -m dmsextractor --config dmsextractor/config.yaml
   ```

3. Manual validation checklist:
   - Open CDF UI → Files in `isp_Target` — files exist, open/download works
   - RAW table `TEST_RAW_TARGET` — rows exist
   - Spot-check one document title and date

**Punchline:** *"Everything looks green. Ship it?"*

---

### 1.3 Pain points to name explicitly (5 min)

**Show table (slide 4):**

| What manual testing sees | What it misses |
|--------------------------|----------------|
| Files uploaded | RAW `TargetFileExternalId` points to wrong external ID |
| Logs say "Successfully processed" | `sourceContext` wrong or missing |
| PDF opens fine | Word doc stored with `application/pdf` mime |
| Re-run succeeds mostly | Occasional version conflict on one row |
| UI shows a filename | `Target_` prefix missing on name |

**Punchline:** *"The extractor didn't crash — it lied quietly."*

**Transition to Act 2:** *"Tests encode the contract in executable form. Let's write one that fails first."*

---

## Act 2 — TDD with unit tests (20 min)

### 2.1 Red → Green on pure logic (8 min)

**Live demo:** Work in `tddextractexercise/` (or `dmsextractor/` if you prefer the reference tree). Start from the stub; add a test **before** the implementation.

**Open:** [`tddextractexercise/tests/unit/test_extractor.py`](tddextractexercise/tests/unit/test_extractor.py) (or mirror from [`dmsextractor/tests/unit/test_extractor.py`](dmsextractor/tests/unit/test_extractor.py) `TestProcessMetadata`).

**Step 1 — Red:** Show or write the failing test:

```python
def test_maps_all_fields(self):
    result = process_metadata({
        "DocumentID": "AO-CLV-ALL-1235-000365",
        "Title": "My Word Doc",
        "RevisionDate": "2025-04-30",
    })
    assert result["DocumentId"] == "dms_ao-clv-all-1235-000365"
    assert result["Title"] == "My Word Doc"
    assert result["RevisionDate"] == "2025-04-30"
    assert result["TargetFileExternalId"] == "Target_AO-CLV-ALL-1235-000365"
```

**Run (expect FAIL):**

```bash
pytest tddextractexercise/tests/unit -v
```

**Step 2 — Green:** Implement `process_metadata` in [`tddextractexercise/extractor.py`](tddextractexercise/extractor.py). Key details to mention while coding:

Start typing def process_metadata (cursor will define the signature)
Then type parsed_date - and cursor will fill out the rest - do look into what is coming and think if it will pass the test

- `DocumentId` uses `.lower()` on `DocumentID`
- `TargetFileExternalId` is `Target_{DocumentID}` (not `Target_CLOV_`)
- `RevisionDate` parsed with `strptime(..., "%Y-%m-%d")`

**Run (expect PASS):**

```bash
pytest tddextractexercise/tests/unit -v
```

---

### 2.2 Config loading test — cheap integration of config (3 min)

**Show (do not necessarily live-code):** [`dmsextractor/tests/unit/config.yaml`](dmsextractor/tests/unit/config.yaml) and `TestConfigLoading` in [`dmsextractor/tests/unit/test_extractor.py`](dmsextractor/tests/unit/test_extractor.py).

**Talking points:**

- Static fixture YAML — no secrets, no network
- Validates `source`, `target`, `target_space` from config
- Catches config drift before you ever hit CDF

**Run:**

```bash
pytest dmsextractor/tests/unit/test_extractor.py::TestConfigLoading -v
```

---

### 2.3 Mock `process_row` — test behavior without CDF (9 min)

**Show fixtures:** [`dmsextractor/tests/unit/conftest.py`](dmsextractor/tests/unit/conftest.py) (`mock_cognite`, `sample_row`, `config`, `source_node`).

**Demo three high-value unit tests in order** from `TestProcessRow`:

#### Test 1: `test_skips_when_source_node_missing` (~2 min)

- Source file node absent → no RAW insert, no upload, no DM apply
- **Talking point:** Prevents silent partial writes

```bash
pytest dmsextractor/tests/unit/test_extractor.py::TestProcessRow::test_skips_when_source_node_missing -v
```

#### Test 2: `test_uses_source_mimetype_not_pdf` (~3 min)

- Source is a Word doc (`application/vnd.openxmlformats-officedocument.wordprocessingml.document`)
- Assert `file_apply.mime_type` matches source — **not** hardcoded `application/pdf`
- **Talking point:** Manual test with PDFs passes; Word fails silently in UI

```bash
pytest dmsextractor/tests/unit/test_extractor.py::TestProcessRow::test_uses_source_mimetype_not_pdf -v
```

#### Test 3: `test_uploads_with_correct_instance_id` (~3 min)

- Assert `file_apply.source_context == "fromDMS"`
- Assert `file_apply.source_id == "AO-CLV-ALL-1235-000365"`
- Assert upload `instance_id.external_id == "Target_AO-CLV-ALL-1235-000365"`

```bash
pytest dmsextractor/tests/unit/test_extractor.py::TestProcessRow::test_uploads_with_correct_instance_id -v
```

**Key teaching moment — read vs write API naming (slide 8):**

```python
# CogniteFileApply (write) — snake_case
source_id=..., source_context="fromDMS"

# CogniteFile (read) — camelCase
target_node.sourceId, target_node.sourceContext
```

**Show the real error trainees hit:** `unexpected keyword argument 'sourceId'`.

**Optional if time (~1 min):** `test_retries_on_version_conflict` — unit test for resilience without flaking CDF ([`apply_with_retry`](dmsextractor/extractor.py)).

**Run full unit suite:**

```bash
pytest dmsextractor/tests/unit -v
```

**Transition to Act 3:** *"Unit tests verify components. Integration tests verify contracts between components."*

---

## Act 3 — Integration tests against CDF (12 min)

### 3.1 Setup (2 min)

**Confirm `.env` is loaded:**

```bash
set -a && source .env && set +a
```

**Run integration tests (expect green if prep checklist done):**

```bash
pytest dmsextractor/tests/integration/ \
  --config dmsextractor/tests/integration/config.yaml \
  -v
```

**Talking points:**

- Requires live CDF credentials (`COGNITE_BASE_URL`, `COGNITE_PROJECT`, `COGNITE_TOKEN_URL`, `COGNITE_CLIENT_ID`, `COGNITE_CLIENT_SECRET`)
- Prerequisite: run extractor once before the session so target data exists
- These tests read back what the extractor wrote — they are the contract enforcers

---

### 3.2 The five parity tests (6 min)

**Walk through** [`dmsextractor/tests/integration/test_extractor.py`](dmsextractor/tests/integration/test_extractor.py):

| Test | Contract verified |
|------|-------------------|
| `test_target_metadata_matches_expected_transform_from_source` | RAW transform matches `process_metadata()` |
| `test_target_file_bytes_equal_source_file_bytes` | Binary fidelity |
| `test_target_file_metadata_preserved_from_source` | MIME type, name prefix, `sourceContext`, `sourceId` |
| `test_target_raw_and_file_are_linked` | RAW external ID → real downloadable file |
| `test_source_rows_with_files_have_target_rows` | No silent skips |

**Run one test at a time for narrative (optional):**

```bash
pytest dmsextractor/tests/integration/test_extractor.py::test_target_raw_and_file_are_linked \
  --config dmsextractor/tests/integration/config.yaml -v
```

**Talking points:**

- Integration tests cross RAW and Data Modeling layers — bugs that pass unit tests can still fail here
- `test_target_raw_and_file_are_linked` is the headline link test: RAW row must point to a file that actually exists

---

### 3.3 Headline bug demo — prefix mismatch (4 min)

**This is the emotional peak of the session.**

#### Inject the bug

In `process_metadata`, temporarily revert to the wrong prefix while `process_row` still uses `Target_{document_id}`:

```python
# BUG — wrong prefix in RAW metadata
"TargetFileExternalId": f"Target_CLOV_{payload['DocumentID']}"
```

`process_row` continues to use:

```python
target_external_id = f"Target_{source_document_id}"
```

**Re-run extractor:**

```bash
python -m dmsextractor --config dmsextractor/config.yaml
```

**Show the contrast:**

| Layer | Manual check | Integration test |
|-------|--------------|------------------|
| Extractor logs | Success | — |
| Files in UI | Visible | `test_target_raw_and_file_are_linked` **FAILS** |
| RAW row | Looks plausible | `test_target_metadata_matches_expected_transform_from_source` **FAILS** |

**Run integration tests (expect FAIL):**

```bash
pytest dmsextractor/tests/integration/ \
  --config dmsextractor/tests/integration/config.yaml -v
```

**Quote for trainees:** *"Unit tests verify components. Integration tests verify contracts between components."*

#### Fix and recover

Revert `process_metadata` to the correct prefix:

```python
"TargetFileExternalId": f"Target_{payload['DocumentID']}"
```

**Re-run extractor, then integration tests (expect green):**

```bash
python -m dmsextractor --config dmsextractor/config.yaml

pytest dmsextractor/tests/integration/ \
  --config dmsextractor/tests/integration/config.yaml \
  -v
```

**Prep tip:** Keep a git stash named `bug-prefix-mismatch` so you can apply/revert the bug in seconds during the demo:

```bash
# Before session
git stash push -m "bug-prefix-mismatch" -- dmsextractor/extractor.py

# During demo: apply bug from stash or dedicated branch
# After demo: git checkout dmsextractor/extractor.py
```

---

## Act 4 — Bug gallery and wrap-up (3 min)

**Quick-fire slide of bugs from the real build:**

| Bug | Caught by |
|-----|-----------|
| `Target_CLOV_` vs `Target_` in RAW vs file | Integration |
| `sourceId` vs `source_id` on `CogniteFileApply` | Runtime error / unit test |
| `sourceContext` typo (`DMS_Target` vs `fromDMS`) | Integration `test_target_file_metadata_preserved_from_source` |
| Hardcoded `application/pdf` | Unit `test_uses_source_mimetype_not_pdf` |
| Forgot `.lower()` on DocumentId | Unit `test_maps_all_fields` |
| Version conflict on re-run | Unit retry test; integration idempotency |

**TDD mantra:** Red → Green → Refactor. Tests are documentation that never goes stale.

**Point to optional hands-on:** [`tddextractexercise/`](tddextractexercise/) — participants implement the full extractor themselves. Reference solution in [`dmsextractor/`](dmsextractor/) only after they attempt the prefix-bug stretch goal.

**Q&A** if time remains.

---

## Suggested slide outline (10–12 slides)

1. Title + learning outcomes
2. Requirements + architecture diagram (source RAW/DM → target RAW/DM)
3. "Without TDD" workflow + manual checklist
4. What manual testing misses (table)
5. Unit test pyramid for extractors
6. Live: `process_metadata` red → green
7. Live: mocked `process_row` tests
8. snake_case vs camelCase trap
9. Integration tests: five contracts
10. Demo: prefix bug — green manual, red tests
11. Bug gallery
12. Optional hands-on + Q&A

---

## Optional hands-on extension (post-session, 60–90 min)

Participants start from [`tddextractexercise/`](tddextractexercise/) and follow the same path:

1. Implement `process_metadata` + unit tests
2. Implement `process_row` with mocked Cognite client + unit tests
3. Wire `run_extractor` using extractor-utils
4. Run against CDF; add one integration test (metadata parity)
5. **Stretch:** inject the `Target_CLOV_` bug themselves and observe which test catches it

Provide solution reference in [`dmsextractor/`](dmsextractor/) only after they attempt step 5.

**Suggested commands for participants:**

```bash
# 1. Unit tests as you go
pytest tddextractexercise/tests/unit -v

# 2. Run your extractor against CDF
set -a && source .env && set +a
python -m tddextractexercise --config dmsextractor/config.yaml

# 3. Compare with reference integration tests
pytest dmsextractor/tests/integration/ \
  --config dmsextractor/tests/integration/config.yaml \
  -v
```

**Facilitator debrief prompts:**

- Which test failed first when you injected the prefix bug?
- What would you add to unit tests after seeing the integration failures?
- Where would you draw the line between unit and integration coverage for your own extractor?

---

## Timing recovery guide

If running behind:

| Cut | Save |
|-----|------|
| Skip `test_revision_date_invalid_format_raises` live demo | ~2 min |
| Show config loading test instead of live-coding | ~2 min |
| Run only 2 of 3 `process_row` unit tests | ~3 min |
| Pre-record Act 3.3 bug demo; show terminal output | ~4 min |
| Shorten bug gallery to top 3 rows | ~1 min |

If running ahead:

- Live-code `test_retries_on_version_conflict`
- Run integration tests one-by-one with commentary
- Start optional hands-on step 1 in the room
