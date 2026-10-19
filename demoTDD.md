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
2. `test_skips_when_source_node_missing` -> early return, assert_not_called on side effects
3. MIME type test -> red against hard-coded `application/pdf`, fix with `mime_type=mimetype`
4. Integration: `test_target_file_bytes_equal_source_file_bytes`



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
- [ ] Verify hard-coded `KNOWN_TEST_KEY` and client name `"twin-auditor-service"` work in the demo project



## Optional: scale-oriented tests (link back to the hook)

- [ ] Retry test: `side_effect` raises `CogniteAPIError` (version conflict) once, then
  ```
  succeeds; patch `time.sleep`
  ```
- [ ] Partial-failure test: many rows, some raise; assert failures are counted or
  ```
  reported, not only logged
  ```
- [ ] Consider: RAW row is inserted before file apply/upload. Test that a failed
  ```
  upload doesn't leave a dangling RAW row
  ```
- [ ] Note `limit=10` in `run_extractor` and the coverage test



## Staging checklist

- [ ] Git tags/commits: stub, metadata green, skip green, MIME red, MIME green, full solution
- [ ] Record sped-up non-TDD clip
- [ ] Run extractor beforehand so target data exists
- [ ] Record or screenshot a passing integration run (fallback)
- [ ] Optional slide: CI runs unit tests on every commit, integration tests as a gate (use your own CI setup)
- [ ] Large fonts, pre-configured terminal commands, `.env` out of sight, env vars loaded



## Commands

```bash
pytest tddextractexercise/tests/unit -v
set -a && source .env && set +a
python -m tddextractexercise --config tddextractexercise/config.yaml
pytest tddextractexercise/tests/integration/ \
  --config tddextractexercise/tests/integration/config.yaml -v
```



## Key messages

- Unit tests with mocks are fast; the integration test validates the real contract.
- Over-mocking can make tests that test nothing, so design code to need few mocks.
- Small steps, run tests immediately, commit the red test.
- Fairness note: prepared tests take time to write. The payoff is in iteration,
refactoring, scale and AI-generated code.



## Open gaps (not covered by my sources)

- extractor-utils' own testing helpers
- Recommended CI setup for integration tests
- Actual timings of live runs against CDF

