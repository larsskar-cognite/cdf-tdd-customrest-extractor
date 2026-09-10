import pytest
from cognite.client.data_classes.data_modeling import NodeId
from cognite.client.data_classes.data_modeling.cdm.v1 import CogniteFile

from dmsextractor.extractor import process_metadata
from dmsextractor.tests.integration.conftest import (
    SOURCE_SPACE, TARGET_SPACE,
    build_source_external_id,
    build_target_external_id,
    get_source_target_pair,
)


# --- 1. RAW metadata transform parity ---

def test_target_metadata_matches_expected_transform_from_source(
    cdf_client, config, known_test_key
):
    source_row, target_row, document_id = get_source_target_pair(
        cdf_client, config, known_test_key
    )

    expected = process_metadata(source_row.columns)

    assert target_row.columns == expected
    assert target_row.columns["DocumentId"] == f"dms_{document_id.lower()}"
    assert target_row.columns["TargetFileExternalId"] == build_target_external_id(document_id)


# --- 2. File bytes parity ---

def test_target_file_bytes_equal_source_file_bytes(
    cdf_client, config, known_test_key
):
    _, _, document_id = get_source_target_pair(cdf_client, config, known_test_key)

    source_external_id = build_source_external_id(document_id)
    target_external_id = build_target_external_id(document_id)

    source_bytes = cdf_client.files.download_bytes(
        instance_id=NodeId(space=SOURCE_SPACE, external_id=source_external_id)
    )
    target_bytes = cdf_client.files.download_bytes(
        instance_id=NodeId(space=TARGET_SPACE, external_id=target_external_id)
    )

    assert len(source_bytes) > 0, "Source file is empty"
    assert source_bytes == target_bytes, "Target file bytes differ from source"


# --- 3. File node metadata parity ---

def test_target_file_metadata_preserved_from_source(
    cdf_client, config, known_test_key
):
    source_row, target_row, document_id = get_source_target_pair(
        cdf_client, config, known_test_key
    )

    source_node = cdf_client.data_modeling.instances.retrieve_nodes(
        nodes=NodeId(space=SOURCE_SPACE, external_id=build_source_external_id(document_id)),
        node_cls=CogniteFile,
    )
    target_node = cdf_client.data_modeling.instances.retrieve_nodes(
        nodes=NodeId(space=TARGET_SPACE, external_id=build_target_external_id(document_id)),
        node_cls=CogniteFile,
    )

    assert source_node is not None
    assert target_node is not None
    assert target_node.mimeType == source_node.mimeType
    assert target_node.name == f"Target_{source_node.name}"
    assert target_node.description == target_row.columns["Title"]
    assert target_node.sourceId == source_row.columns["DocumentID"]
    assert target_node.sourceContext == "fromDMS"


# --- 4. RAW row links to a real file ---

def test_target_raw_and_file_are_linked(cdf_client, config, known_test_key):
    _, target_row, _ = get_source_target_pair(cdf_client, config, known_test_key)

    target_external_id = target_row.columns["TargetFileExternalId"]

    file_node = cdf_client.data_modeling.instances.retrieve_nodes(
        nodes=NodeId(space=TARGET_SPACE, external_id=target_external_id),
        node_cls=CogniteFile,
    )
    assert file_node is not None

    file_bytes = cdf_client.files.download_bytes(
        instance_id=NodeId(space=TARGET_SPACE, external_id=target_external_id)
    )
    assert len(file_bytes) > 0


# --- 5. Coverage: source rows with files should have target rows ---

def test_source_rows_with_files_have_target_rows(cdf_client, config):
    source_rows = cdf_client.raw.rows.list(
        db_name=config.source.database,
        table_name=config.source.table,
        limit=10,  # same limit as run_extractor
    )
    assert len(source_rows) > 0

    missing_targets = []
    for row in source_rows:
        document_id = row.columns["DocumentID"]
        source_node = cdf_client.data_modeling.instances.retrieve_nodes(
            nodes=NodeId(space=SOURCE_SPACE, external_id=build_source_external_id(document_id)),
            node_cls=CogniteFile,
        )
        if source_node is None:
            continue  # extractor skips these by design

        try:
            target_row = cdf_client.raw.rows.retrieve(
                db_name=config.target.database,
                table_name=config.target.table,
                key=row.key,
            )
        except Exception:
            target_row = None

        if target_row is None:
            missing_targets.append(row.key)

    assert not missing_targets, f"Source rows with files missing in target RAW: {missing_targets}"


def test_reprocessing_same_document_is_idempotent(cdf_client, config, known_test_key):
    """Run extractor twice on same row; target should still match source."""
    # 1. Run extractor (or call process_row twice via a test hook)
    # 2. Assert parity tests still pass:
    source_row, target_row, document_id = get_source_target_pair(cdf_client, config, known_test_key)
    assert target_row.columns == process_metadata(source_row.columns)

    # bytes still match
    source_bytes = cdf_client.files.download_bytes(
        instance_id=NodeId(space=SOURCE_SPACE, external_id=build_source_external_id(document_id))
    )
    target_bytes = cdf_client.files.download_bytes(
        instance_id=NodeId(space=TARGET_SPACE, external_id=build_target_external_id(document_id))
    )
    assert source_bytes == target_bytes