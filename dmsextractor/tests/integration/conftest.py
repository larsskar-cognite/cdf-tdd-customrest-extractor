import pytest
from cognite.client import CogniteClient
from cognite.extractorutils.configtools import load_yaml
from dmsextractor.config import Config
# Add after imports in conftest.py
from cognite.client.data_classes.data_modeling import NodeId

SOURCE_SPACE = "isp_CLOV"
TARGET_SPACE = "isp_Target"
SOURCE_FILE_PREFIX = "NewProdom_CLOV_"
TARGET_FILE_PREFIX = "Target_"

# Row key known to have been processed end-to-end
KNOWN_TEST_KEY = "cb091563-1433-4a3f-b44f-2a83f6225f15"

def build_source_external_id(document_id: str) -> str:
    return f"{SOURCE_FILE_PREFIX}{document_id}"


def build_target_external_id(document_id: str) -> str:
    return f"{TARGET_FILE_PREFIX}{document_id}"


@pytest.fixture(scope="session")
def known_test_key() -> str:
    return KNOWN_TEST_KEY

def pytest_addoption(parser):
    parser.addoption(
        "--config",
        action="store",
        default="dmsextractor/config.yaml",
        help="Path to extractor config YAML",
    )

def get_source_target_pair(cdf_client, config, row_key: str):
    source_row = cdf_client.raw.rows.retrieve(
        db_name=config.source.database,
        table_name=config.source.table,
        key=row_key,
    )
    target_row = cdf_client.raw.rows.retrieve(
        db_name=config.target.database,
        table_name=config.target.table,
        key=row_key,
    )
    document_id = source_row.columns["DocumentID"]
    return source_row, target_row, document_id


@pytest.fixture(scope="session")
def config_path(request) -> str:
    return request.config.getoption("--config")


@pytest.fixture(scope="session")
def config(config_path: str) -> Config:
    with open(config_path, encoding="utf-8") as config_file:
        return load_yaml(config_file, Config)

@pytest.fixture(scope="session")
def cdf_client(config: Config) -> CogniteClient:
    return config.cognite.get_cognite_client("twin-auditor-service")

