"""
This is the main entry point for the extractor.
Exercise:
Extract documents with metadata from one cognite space to another.
Mark the extracted documents in the target system as follows:
* Source metadata and documents are defined in the config file
* Target metadata and documents are defined in the config file
* Prefix name and externalID with Target_
* Mark sourceContext as fromDMS
* Create a new target space based on what config says if it doesn't exist
* Move the extracted documents to the new space
"""

import logging
from typing import Any

from cognite.client import CogniteClient
from cognite.client.data_classes import Row
from cognite.client.data_classes.data_modeling import NodeId
from cognite.client.data_classes.data_modeling.cdm.v1 import CogniteFile, CogniteFileApply
from cognite.extractorutils.statestore import AbstractStateStore
from cognite.extractorutils.threading import CancellationToken

from tddextractexercise.config import Config


def process_row(cognite: CogniteClient, row: Row, config: Config) -> None:
    columns: dict[str, Any] = row.columns or {}
    source_space = "isp_CLOV"
    source_external_id = "NewProdom_CLOV_" + columns.get("DocumentID", "")
    source_node = cognite.data_modeling.instances.retrieve_nodes(
        nodes=NodeId(space=source_space, external_id=source_external_id),
        node_cls=CogniteFile,
    )
    if source_node is None:
        logging.warning(f"Source node not found for {columns.get('DocumentID')}")
        return

    processed_metadata = process_metadata(columns)
    cognite.raw.rows.insert(
        db_name=config.target.database,
        table_name=config.target.table,
        row=Row(key=row.key, columns=processed_metadata),
        ensure_parent=True,
    )

    target_file_external_id = processed_metadata["TargetFileExternalId"]
    file_apply = CogniteFileApply(
        external_id=target_file_external_id,
        name=f"Target_{source_node.name}",
        mime_type=source_node.mime_type,
        description=columns.get("Title"),
        source_id=columns.get("DocumentID"),
        source_context="fromDMS",
        space=config.target_space.space,
    )
    cognite.data_modeling.instances.apply(file_apply)
    source_file_bytes = cognite.files.download_bytes(
        instance_id=NodeId(space=source_space, external_id=source_external_id)
    )
    cognite.files.upload_content_bytes(
        instance_id=NodeId(space=config.target_space.space, external_id=target_file_external_id),
        content=source_file_bytes,
    )


def process_metadata(payload: dict[str, Any]) -> dict[str, str]:
    return {
        "DocumentId": f"dms_{payload['DocumentID'].lower()}",
        "Title": payload["Title"],
        "RevisionDate": payload["RevisionDate"],
        "TargetFileExternalId": f"Target_{payload['DocumentID']}",
    }


def run_extractor(
    cognite: CogniteClient, states: AbstractStateStore, config: Config, stop_event: CancellationToken
) -> None:
    logging.info("Starting extractor")
    source_rows = cognite.raw.rows.list(
        db_name=config.source.database,
        table_name=config.source.table,
        limit=10,
    )
    for row in source_rows:
        process_row(cognite, row, config)
        columns: dict[str, Any] = row.columns or {}
        logging.info(f"Processed row: {row.key} with name: {columns.get('Title')}")
    logging.info("Finished processing rows")
