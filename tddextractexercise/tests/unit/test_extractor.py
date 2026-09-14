from pathlib import Path

import pytest
from cognite.client.exceptions import CogniteAPIError
from cognite.extractorutils.configtools import load_yaml

from tddextractexercise.config import Config
from tddextractexercise.extractor_train01 import process_metadata, process_row

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


class TestProcessMetadata:
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


def build_source_external_id(document_id: str) -> str:
    return f"NewProdom_CLOV_{document_id}"


def build_target_external_id(document_id: str) -> str:
    return f"Target_{document_id}"


def build_target_filename(source_name: str) -> str:
    return f"Target_{source_name}"


class TestExternalIds:
    def test_source_external_id(self):
        assert build_source_external_id("AO-CLV-ALL-1235-000365") == "NewProdom_CLOV_AO-CLV-ALL-1235-000365"

    def test_target_external_id(self):
        assert build_target_external_id("AO-CLV-ALL-1235-000365") == "Target_AO-CLV-ALL-1235-000365"

    def test_target_filename_preserves_extension(self):
        assert build_target_filename("Report.docx") == "Target_Report.docx"


class TestProcessRow:
    def test_skips_when_source_node_missing(self, mock_cognite, sample_row, config):
        mock_cognite.files.download_bytes.return_value = b"fake-content"
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

    def test_applies_target_prefix_to_filename(self, mock_cognite, sample_row, config, source_node, target_node):
        mock_cognite.files.download_bytes.return_value = b"content"
        mock_cognite.data_modeling.instances.retrieve_nodes.side_effect = [
            source_node,
            target_node,
        ]
        process_row(mock_cognite, sample_row, config)
        file_apply = mock_cognite.data_modeling.instances.apply.call_args_list[0][0][0]
        assert file_apply.name == "Target_AO-CLV-ALL-1235-000365"

    def test_retries_on_version_conflict(self, mock_cognite, sample_row, config, source_node):
        conflict = CogniteAPIError("A version conflict caused the ingest to fail.", 400)
        mock_cognite.files.download_bytes.return_value = b"content"
        mock_cognite.data_modeling.instances.retrieve_nodes.return_value = source_node
        mock_cognite.data_modeling.instances.apply.side_effect = [conflict, None]

        process_row(mock_cognite, sample_row, config)

        assert mock_cognite.data_modeling.instances.apply.call_count == 2
