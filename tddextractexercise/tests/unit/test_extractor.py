from pathlib import Path

from cognite.extractorutils.configtools import load_yaml

from tddextractexercise.config import Config

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
