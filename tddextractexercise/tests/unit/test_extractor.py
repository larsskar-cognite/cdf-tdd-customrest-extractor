from pathlib import Path
from unittest.mock import patch

import pytest
from cognite.client.data_classes import Row
from cognite.client.exceptions import CogniteAPIError
from cognite.extractorutils.configtools import load_yaml

from tddextractexercise.config import Config
from tddextractexercise.extractor import (
    build_source_external_id,
    build_target_external_id,
    build_target_filename,
    process_metadata,
    process_row,
    process_rows,
)

UNIT_TEST_CONFIG = Path(__file__).parent / "config.yaml"


class TestConfigLoading:
    def test_loads_source_and_target_from_yaml(self):
        with open(UNIT_TEST_CONFIG, encoding="utf-8") as f:
            config = load_yaml(f, Config)

        assert config.source.database == "TEST_RAW_DATABASE"
        assert config.source.table == "TEST_METADATA_TABLE"
        assert config.target.database == "TEST_RAW_TARGET"
        assert config.target.table == "TEST_METADATA_TABLE"
        assert config.target_space.space == "isp_Target"

    def test_cognite_section_parsed(self):
        with open(UNIT_TEST_CONFIG, encoding="utf-8") as f:
            config = load_yaml(f, Config)

        assert config.cognite.project == "test-project"
        assert config.cognite.host == "https://example.cognitedata.com"


def test_maps_all_fields():
    result = process_metadata(
        {
            "DocumentID": "AO-CLV-ALL-1235-000365",
            "Title": "My Word Doc",
            "RevisionDate": "2025-04-30",
        }
    )
    assert result["DocumentId"] == "dms_ao-clv-all-1235-000365"
    assert result["Title"] == "My Word Doc"
    assert result["RevisionDate"] == "2025-04-30"
    assert result["TargetFileExternalId"] == "Target_AO-CLV-ALL-1235-000365"


class TestExternalIds:
    def test_source_external_id(self):
        assert build_source_external_id("AO-CLV-ALL-1235-000365") == "NewProdom_CLOV_AO-CLV-ALL-1235-000365"

    def test_target_external_id(self):
        assert build_target_external_id("AO-CLV-ALL-1235-000365") == "Target_AO-CLV-ALL-1235-000365"

    def test_target_filename_preserves_extension(self):
        assert build_target_filename("Report.docx") == "Target_Report.docx"


class TestProcessRow:
    def test_skips_when_source_node_missing(self, mock_cognite, sample_row, config):
        mock_cognite.data_modeling.instances.retrieve_nodes.return_value = None
        process_row(mock_cognite, sample_row, config)
        mock_cognite.raw.rows.insert.assert_not_called()
        mock_cognite.files.upload_content_bytes.assert_not_called()
        mock_cognite.data_modeling.instances.apply.assert_not_called()

    def test_uses_source_mimetype_not_pdf(self, mock_cognite, sample_row, config, source_node):
        word_mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        source_node.mime_type = word_mime
        mock_cognite.files.download_bytes.return_value = b"PK\x03\x04fake"
        mock_cognite.data_modeling.instances.retrieve_nodes.return_value = source_node
        process_row(mock_cognite, sample_row, config)
        file_apply = mock_cognite.data_modeling.instances.apply.call_args_list[0][0][0]
        assert file_apply.mime_type == word_mime
        assert file_apply.description == "My Word Doc"

    def test_uploads_with_correct_instance_id(self, mock_cognite, sample_row, config, source_node):
        mock_cognite.files.download_bytes.return_value = b"content"
        mock_cognite.data_modeling.instances.retrieve_nodes.return_value = source_node
        process_row(mock_cognite, sample_row, config)
        file_apply = mock_cognite.data_modeling.instances.apply.call_args_list[0][0][0]
        assert file_apply.source_context == "fromDMS"
        assert file_apply.source_id == "AO-CLV-ALL-1235-000365"
        upload_call = mock_cognite.files.upload_content_bytes.call_args
        instance_id = upload_call.kwargs["instance_id"]
        assert instance_id.space == "isp_Target"
        assert instance_id.external_id == "Target_AO-CLV-ALL-1235-000365"
        assert instance_id.external_id.startswith("Target_")
        assert "NewProdom" not in instance_id.external_id

    def test_applies_target_prefix_to_filename(self, mock_cognite, sample_row, config, source_node):
        mock_cognite.files.download_bytes.return_value = b"content"
        mock_cognite.data_modeling.instances.retrieve_nodes.return_value = source_node
        process_row(mock_cognite, sample_row, config)
        file_apply = mock_cognite.data_modeling.instances.apply.call_args_list[0][0][0]
        assert file_apply.name == "Target_Report.docx"


class TestScale:
    def test_processes_all_rows_streamed_in_chunks(self, mock_cognite, config):
        chunks = [
            [Row(key=f"row-{i}", columns={"DocumentID": f"DOC-{i}"}) for i in range(start, start + 1000)]
            for start in range(0, 5000, 1000)
        ]
        mock_cognite.raw.rows.return_value = iter(chunks)

        with patch("tddextractexercise.extractor.process_row", autospec=True) as process_row:
            summary = process_rows(mock_cognite, config)

        assert summary.processed == 5000
        assert process_row.call_count == 5000
        kwargs = mock_cognite.raw.rows.call_args.kwargs
        assert kwargs["db_name"] == "SRC_DB"
        assert kwargs["table_name"] == "SRC_TABLE"
        assert kwargs["limit"] is None
        assert kwargs["chunk_size"] is not None

    def test_retries_apply_on_version_conflict(self, mock_cognite, sample_row, config, source_node):
        mock_cognite.data_modeling.instances.retrieve_nodes.return_value = source_node
        mock_cognite.data_modeling.instances.apply.side_effect = [
            CogniteAPIError(message="Version conflict", code=409),
            None,
        ]
        with patch("time.sleep") as sleep:
            process_row(mock_cognite, sample_row, config)
        assert mock_cognite.data_modeling.instances.apply.call_count == 2
        sleep.assert_called_once()
        mock_cognite.files.upload_content_bytes.assert_called_once()

    def test_does_not_retry_other_api_errors(self, mock_cognite, sample_row, config, source_node):
        mock_cognite.data_modeling.instances.retrieve_nodes.return_value = source_node
        mock_cognite.data_modeling.instances.apply.side_effect = CogniteAPIError(message="Forbidden", code=403)
        with patch("time.sleep") as sleep, pytest.raises(CogniteAPIError):
            process_row(mock_cognite, sample_row, config)
        assert mock_cognite.data_modeling.instances.apply.call_count == 1
        sleep.assert_not_called()

    def test_run_continues_past_failing_rows_and_reports_them(self, mock_cognite, config, source_node):
        rows = [
            Row(key=f"row-{i}", columns={"DocumentID": f"DOC-{i}", "Title": f"Doc {i}", "RevisionDate": "2025-04-30"})
            for i in range(5)
        ]
        mock_cognite.raw.rows.return_value = iter([rows])
        boom = CogniteAPIError(message="Internal error", code=500)
        mock_cognite.data_modeling.instances.retrieve_nodes.side_effect = [
            source_node,
            boom,
            source_node,
            boom,
            source_node,
        ]

        summary = process_rows(mock_cognite, config)

        assert summary.processed == 3
        assert summary.failed == ["row-1", "row-3"]
        assert mock_cognite.files.upload_content_bytes.call_count == 3

    def test_no_raw_row_when_upload_fails(self, mock_cognite, sample_row, config, source_node):
        mock_cognite.data_modeling.instances.retrieve_nodes.return_value = source_node
        mock_cognite.files.upload_content_bytes.side_effect = CogniteAPIError(message="Upload failed", code=500)
        with pytest.raises(CogniteAPIError):
            process_row(mock_cognite, sample_row, config)
        mock_cognite.raw.rows.insert.assert_not_called()
