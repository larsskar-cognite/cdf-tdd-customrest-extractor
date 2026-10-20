# Planning: "Test driving your custom extractor for scale" (Devcon, 25 min)

## Goal

Show that TDD (mocked unit tests + one real-system integration test) gives
confidence and speed for custom Cognite extractors, especially when AI agents
generate code faster than we can read it.

## Repo context

- Exercise package: `tddextractexercise/` (stub in `extractor.py`)
- Unit tests: `tddextractexercise/tests/unit` (MagicMock Cognite client, no CDF)
- Integration tests: `tddextractexercise/tests/integration` (live CDF, needs .env
and a prior extractor run)
- Final solution came from another repo (`dmsextractor`), so imports differ.



## Session timeline (estimates, rehearse them)


| Time        | Segment           | Content                                                                                                                                                                         |
| ----------- | ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 0:00-4:00   | Hook, why TDD now | Extractors break, leak memory or stall at volume. AI agents produce code faster than we can read it. Promise: "I'll show you tests that prove scale behaviour in under a second." |
| 4:00-7:00   | Non-TDD attempt   | Quick-and-dirty `dmsextractor/extractor_quiet_lie.py`. Runs without errors, yet: Word file stored as PDF (CDF viewer can't open it), and only 10 of 20 rows copied (`limit=10`).    |
| 7:00-15:00  | TDD demo          | Metadata (1 min), scale: stream every row (3 min), MIME (2.5 min), retry on version conflict (1.5 min). Script below.                                                           |
| 15:00-18:00 | Integration test  | File bytes parity, then the coverage test that used to agree with the `limit=10` bug. "Mocks prove my logic. The integration test proves the contract."                         |
| 18:00-23:00 | Takeaways         | What the tests prove about scale, SDK mocking (`CogniteClientMock`), CI gating, agent guidance (AGENTS.md, red/green TDD, commit the red test, avoid over-mocking).             |
| 23:00-25:00 | Q&A               |                                                                                                                                                                                 |


Interactive: ask "will it pass?" before each run.

## Demo script

Start on the `devcon-demo` branch head (stub). Before every run, ask "will it pass?".
If live coding goes wrong, check out the fallback ref and carry on. `<tag>~1` is the
red commit before a green tag; `demo-2-chunks~2` is the demo 2 red commit.

### Non-TDD attempt (4:00-7:00)

1. Show `dmsextractor/extractor_quiet_lie.py` briefly (or the sped-up clip). It looks reasonable.
2. In the CDF UI, open space `isp_Lars` and the file
   `AO-CLV-ALL-1235-000365_CL-INER-TOP-M125-INST-1Y.docx`. The viewer fails: it's a
   Word file labelled `application/pdf`.
3. Say: "No errors, no warnings. And there's a second bug you can't see in the UI:
   it only read 10 of the 20 source rows. Hold that thought."

### Step 1: metadata (7:00-8:00)

- Test: `test_maps_all_fields` and the external ID helpers.
- Run `pytest tddextractexercise/tests/unit -v`: red, 4 failed. Implement
  `process_metadata`: green, 6 passed.
- Say: "Pure function, no mocks. Keep the logic away from I/O and testing is trivial."
- Fallback: `git checkout demo-1-metadata~1` (red), `git checkout demo-1-metadata` (green).

### Step 2: scale, stream every row (8:00-11:00)

- Test: `TestScale::test_processes_all_rows_streamed_in_chunks`. It feeds 5,000 rows
  in 5 chunks through the SDK's `CogniteClientMock`, with `process_row` patched out.
- Run: red, `NotImplementedError`.
- Say: "The quick version used `raw.rows.list(limit=10)`. Against that, this test
  says `assert 0 == 5000`."
- Implement: loop over `cognite.raw.rows(chunk_size=RAW_ROW_CHUNK_SIZE, limit=None)`
  and then over each chunk. Run: green, 7 passed in about 0.06 s.
- Say: "5,000 rows in a fraction of a second. This proves we read everything, in
  bounded chunks, so memory stays flat whether the table has 20 rows or 20 million.
  Try proving that against a live system in a 25-minute talk."
- Fallback: `git checkout demo-2-chunks~2` (red), `git checkout demo-2-chunks~1` (green).

### Step 3: MIME type (11:00-13:30)

- Show the step 3 red tests: skip when the source node is missing, MIME type,
  upload target, filename prefix. Don't dwell on the skip test.
- Check out `demo-3-mime-red`: `process_row` written quickly, without TDD, with a
  hard-coded PDF. Run: 1 failed, `test_uses_source_mimetype_not_pdf`, with
  `'application/pdf' == 'application/...wordprocessingml.document'`.
- Say: "That's the Word file the CDF viewer couldn't open. Found in milliseconds,
  not by a user."
- Fix: `mime_type=source_node.mime_type`. Run: green, 11 passed.
- Say: "The source node fixture is a real `CogniteFile`, not a MagicMock. A wrong
  attribute name like `mimeType` fails instead of passing silently."
- Fallback: `git checkout demo-4-mime-green`.

### Step 4: retry on version conflict (13:30-15:00)

- Check out `demo-5-full~1` and show `test_retries_apply_on_version_conflict`. The
  first `apply` raises a 409 version conflict and the second succeeds; `time.sleep`
  is patched.
- Run `pytest tddextractexercise/tests/unit -v -k retr`: red,
  `CogniteAPIError: Version conflict | code: 409`.
- Check out `demo-5-full`: green, with `apply_with_retry` and exponential backoff.
- Say: "At volume, concurrent writers hit version conflicts. You'll never reproduce
  that reliably against CDF; with a mock it's one line. And
  `test_does_not_retry_other_api_errors` makes sure we don't retry a 403."
- Mention the other demo 5 tests without running them: failed rows are counted, not
  only logged, and no RAW row is written for a file that failed to upload.

### Integration (15:00-18:00)

`.env` is loaded and the target was populated by the `demo-5-full` extractor (20 rows).

1. Run `test_target_file_bytes_equal_source_file_bytes` (about 2 s): green.
   Say: "Same bytes in source and target. A mock can't tell you that."
2. Show `test_source_rows_with_files_have_target_rows`. Say: "This test used to read
   `limit=10  # same limit as run_extractor`. It agreed with the bug, so it could
   never catch it."
3. Show `rehearsal/integration_coverage_red.txt`: against the old extractor's data,
   10 of 20 rows were missing. Then run it live (about 3 s): green.
4. Say: "Mocks prove my logic. The integration test proves the contract. An
   integration test that copies production logic proves nothing."

### Takeaways: what the tests prove about scale (18:00-23:00)

- Reads every row, in bounded chunks: demo 2 test.
- Survives version conflicts without retrying real errors: demo 5 retry tests.
- One bad row doesn't stop the run, and failures are reported: partial-failure test.
- No dangling RAW rows when an upload fails: ordering test.
- Re-runs are safe, with no duplicates and no double prefix: integration idempotency test.
- Honest framing: unit tests don't measure throughput. They pin down the behaviours
  that decide whether an extractor survives volume, and they're fast enough (15 tests
  in about 0.3 s) to refactor towards batching without fear.



## TODO: fix the repo before the session

- [ ] Use `mime_type=mimetype` (keep hard-coded PDF version as the red checkpoint)
- [ ] Resolve attribute mismatches: fixtures use `mimeType`; unit tests use
  ```
  `mime_type`, `source_id`, `source_context`. Prefer specced mocks
  (`create_autospec` or SDK `CogniteClientMock`) so mismatches fail.
  ```
- [ ] Import `build_source_external_id`, `build_target_external_id`,
  ```
  `build_target_filename` from the extractor instead of defining them in the test file
  ```
- [ ] Check mocks in skip test (`download_bytes`) and prefix test (`retrieve_nodes` side_effect) match real calls
- [ ] Fix README paths (`dmsextractor/` vs `tddextractexercise/`)
- [ ] Remove dead code (commented `filename` line, "minimal logic" comment)
- [ ] Decide on `test_reprocessing_same_document_is_idempotent`: it doesn't re-run
  ```
  the extractor. Make it real or drop it.
  ```
- [x] Verify hard-coded `KNOWN_TEST_KEY` and client name `"twin-auditor-service"` work in the demo project



## Optional: scale-oriented tests (link back to the hook)

- [x] Retry test: `side_effect` raises `CogniteAPIError` (version conflict) once, then
  ```
  succeeds; patch `time.sleep`
  ```
- [x] Partial-failure test: many rows, some raise; assert failures are counted or
  ```
  reported, not only logged
  ```
- [x] Consider: RAW row is inserted before file apply/upload. Test that a failed
  ```
  upload doesn't leave a dangling RAW row
  ```
- [x] Replace `limit=10` with chunked streaming (demo 2) and fix the coverage test



## Staging checklist

- [x] Git tags/commits: stub, metadata green, chunks green, MIME red, MIME green, full solution
- [ ] Record sped-up non-TDD clip
- [x] Run extractor beforehand so target data exists
- [x] Record or screenshot a passing integration run (fallback, text output in `rehearsal/`)
- [ ] Optional slide: CI runs unit tests on every commit, integration tests as a gate (use your own CI setup)
- [ ] Large fonts, pre-configured terminal commands, `.env` out of sight, env vars loaded



## Commands

```bash
pytest tddextractexercise/tests/unit -v
set -a && source .env && set +a
python -m tddextractexercise tddextractexercise/config.yaml
pytest tddextractexercise/tests/integration/ \
  --config tddextractexercise/tests/integration/config.yaml -v
```



## Key messages

- Unit tests with mocks are fast; the integration test validates the real contract.
- Over-mocking can make tests that test nothing, so design code to need few mocks.
- Small steps, run tests immediately, commit the red test.
- Fairness note: prepared tests take time to write. The payoff is in iteration,
refactoring, scale and AI-generated code.



## Rehearsal results (2026-10-20, project `larsdog-test` on bluefield)

- The source table has 20 rows. `KNOWN_TEST_KEY` (`cb091563-...`) exists and has a source file (`AO-CLV-ALL-1235-000352.pdf`). Client name
`twin-auditor-service` works with the `.env` credentials. Target space `isp_Target` exists.
- MIME types in the first 10 source files: 9 PDF, 1 Word (`1bc2e0c0-...`). The
integration MIME check uses `KNOWN_TEST_KEY`, which is a PDF, so it would not
catch the hard-coded PDF bug. Only the unit test catches it. Say this on stage,
or point `KNOWN_TEST_KEY` at the Word row.
- The extractor takes the config path as a positional argument; `--config` fails
with "unrecognized arguments".

| Step | Wall time |
| ---- | --------- |
| Extractor run at `demo-5-full` (20 rows, 0 failed) | 30 s |
| Integration suite (6 tests) | 8.7 s |
| Integration `test_target_file_bytes_equal_source_file_bytes` alone | 1.9 s |
| Integration coverage test alone | 3.2 s |
| Unit tests at any demo tag, including 5,000-row test | < 0.5 s |

Red/green results per commit on `devcon-demo`: demo 1 red (4 fail), demo 2 red
(1 fail), demo 3 red (4 fail), demo 3 hard-coded PDF (1 fail:
`test_uses_source_mimetype_not_pdf`), demo 5 red (3 fail), every green commit passes.

Fallback output is saved in `rehearsal/` (gitignored): `integration_run_full.txt`,
`integration_bytes_parity.txt`, `integration_coverage_red.txt` (10 of 20 rows
missing), `integration_coverage_green.txt` and `unit_<commit>_<step>.txt` for each demo commit.

## Open gaps (not covered by my sources)

- extractor-utils' own testing helpers
- Recommended CI setup for integration tests

