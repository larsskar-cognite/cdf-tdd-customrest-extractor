from unittest.mock import MagicMock

import pytest
from cognite.client.data_classes.data_modeling.cdm.v1 import CogniteFile
from cognite.client.testing import CogniteClientMock

from tddextractexercise.config import DataLocation, TargetSpace


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
    config.target_space = TargetSpace(
        space="isp_Target",
        name="isp_Target",
        description="Target space for DMS extractor files",
    )
    return config


@pytest.fixture
def mock_cognite():
    return CogniteClientMock()


@pytest.fixture
def source_node():
    return CogniteFile(
        space="isp_CLOV",
        external_id="NewProdom_CLOV_AO-CLV-ALL-1235-000365",
        version=1,
        last_updated_time=0,
        created_time=0,
        name="Report.docx",
        mime_type="text/plain",
    )


@pytest.fixture
def target_node():
    return CogniteFile(
        space="isp_Target",
        external_id="Target_AO-CLV-ALL-1235-000365",
        version=1,
        last_updated_time=0,
        created_time=0,
        name="Target_Report.docx",
        mime_type="text/plain",
    )
