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


| Time        | Segment           | Content                                                                                                           |
| ----------- | ----------------- | ----------------------------------------------------------------------------------------------------------------- |
| 0:00-4:00   | Hook, why TDD now | Extractors break, leak memory or stall at volume. AI agents produce code faster than we can read it.              |
| 4:00-7:00   | Non-TDD attempt   | Pre-recorded or staged quick-and-dirty build. Shows uncertainty. Hard-coded PDF MIME type = "bug nobody noticed". |
| 7:00-15:00  | TDD demo          | 3 red -> green steps (below).                                                                                     |
| 15:00-18:00 | Integration test  | One test, e.g. file bytes parity. "Mocks prove my logic. The integration test proves the contract."               |
| 18:00-23:00 | Takeaways         | SDK mocking, CI gating, agent guidance (AGENTS.md, red/green TDD, commit the red test, avoid over-mocking).       |
| 23:00-25:00 | Q&A               |                                                                                                                   |


Interactive: ask "will it pass?" before each run.

## TDD demo steps

1. `test_maps_all_fields` -> implement `process_metadata` (instant green)
2. Scale: `test_processes_all_rows_streamed_in_chunks` -> 5,000 mocked rows, red
   (`NotImplementedError`; the old `raw.rows.list(limit=10)` version gives
   `assert 0 == 5000`), green by streaming `raw.rows(chunk_size=1000, limit=None)`.
   The whole unit suite still runs in well under a second.
   "This proves we read everything, in bounded chunks, so memory stays flat."
3. MIME type test -> red against hard-coded `application/pdf`, fix with `mime_type=source_node.mime_type`
4. Point at `test_retries_apply_on_version_conflict` (demo 5): red shows
   `CogniteAPIError: Version conflict | code: 409`; green retries with backoff.
   `test_does_not_retry_other_api_errors` guards against swallowing real errors.
5. Integration: `test_target_file_bytes_equal_source_file_bytes`, then
   `test_source_rows_with_files_have_target_rows`. It used to copy the
   extractor's `limit=10` and so agreed with the bug. Against data from the old
   extractor it is red with 10 of 20 rows missing (`rehearsal/integration_coverage_red.txt`).

The skip test (`test_skips_when_source_node_missing`) is in the demo 3 red
commit and is not shown live.



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

