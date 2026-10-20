from pathlib import Path
from unittest.mock import patch

from cognite.client.data_classes import Row
from cognite.extractorutils.configtools import load_yaml

from tddextractexercise.config import Config
from tddextractexercise.extractor import (
    build_source_external_id,
    build_target_external_id,
    build_target_filename,
    process_metadata,
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
