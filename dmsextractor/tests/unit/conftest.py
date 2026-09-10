import pytest
from unittest.mock import MagicMock
from dmsextractor.config import DataLocation

@pytest.fixture
def sample_row():
    row = MagicMock()
    row.key = "test-row-key"
    row.columns = {
        "DocumentID": "AO-CLV-ALL-1235-000365",
        "Title": "My Word Doc",
        "RevisionDate": "2025-04-30",
    }
    return row

@pytest.fixture
def config():
    config = MagicMock()
    config.source = DataLocation(database="SRC_DB", table="SRC_TABLE")
    config.target = DataLocation(database="TGT_DB", table="TGT_TABLE")
    return config

    
@pytest.fixture
def mock_cognite():
    return MagicMock()

@pytest.fixture
def source_node():
    node = MagicMock()
    node.name = "Report.docx"
    node.mimeType = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    return node

@pytest.fixture
def target_node():
    return MagicMock()
