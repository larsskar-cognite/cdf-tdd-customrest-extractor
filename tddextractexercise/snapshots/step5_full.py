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
import time
from dataclasses import dataclass, field
from typing import Any

from cognite.client import CogniteClient
from cognite.client.data_classes import Row
from cognite.client.data_classes.data_modeling import NodeId
from cognite.client.data_classes.data_modeling.cdm.v1 import CogniteFile, CogniteFileApply
from cognite.client.exceptions import CogniteAPIError
from cognite.extractorutils.statestore import AbstractStateStore
from cognite.extractorutils.threading import CancellationToken

from tddextractexercise.config import Config

RAW_ROW_CHUNK_SIZE = 1000


def build_source_external_id(document_id: str) -> str:
    return f"NewProdom_CLOV_{document_id}"


def build_target_external_id(document_id: str) -> str:
    return f"Target_{document_id}"


def build_target_filename(source_name: str) -> str:
    return f"Target_{source_name}"


def is_version_conflict(exc: CogniteAPIError) -> bool:
    return exc.code in (400, 409) and "version conflict" in str(exc).lower()


def apply_with_retry(cognite: CogniteClient, file_apply: CogniteFileApply, max_attempts: int = 3) -> None:
    for attempt in range(max_attempts):
        try:
            cognite.data_modeling.instances.apply(file_apply)
            return
        except CogniteAPIError as e:
            if is_version_conflict(e) and attempt < max_attempts - 1:
                time.sleep(0.5 * (2**attempt))
                continue
            raise


def process_row(cognite: CogniteClient, row: Row, config: Config) -> None:
    columns: dict[str, Any] = row.columns or {}
    source_space = "isp_CLOV"
    source_external_id = build_source_external_id(columns.get("DocumentID", ""))
    source_node = cognite.data_modeling.instances.retrieve_nodes(
        nodes=NodeId(space=source_space, external_id=source_external_id),
        node_cls=CogniteFile,
    )
    if source_node is None:
        logging.warning(f"Source node not found for {columns.get('DocumentID')}")
        return

    processed_metadata = process_metadata(columns)
    target_file_external_id = processed_metadata["TargetFileExternalId"]
    file_apply = CogniteFileApply(
        external_id=target_file_external_id,
        name=build_target_filename(source_node.name or ""),
        mime_type=source_node.mime_type,
        description=columns.get("Title"),
        source_id=columns.get("DocumentID"),
        source_context="fromDMS",
        space=config.target_space.space,
    )
    apply_with_retry(cognite, file_apply)
    source_file_bytes = cognite.files.download_bytes(
        instance_id=NodeId(space=source_space, external_id=source_external_id)
    )
    cognite.files.upload_content_bytes(
        instance_id=NodeId(space=config.target_space.space, external_id=target_file_external_id),
        content=source_file_bytes,
    )
    cognite.raw.rows.insert(
        db_name=config.target.database,
        table_name=config.target.table,
        row=Row(key=row.key, columns=processed_metadata),
        ensure_parent=True,
    )


def process_metadata(payload: dict[str, Any]) -> dict[str, str]:
    return {
        "DocumentId": f"dms_{payload['DocumentID'].lower()}",
        "Title": payload["Title"],
        "RevisionDate": payload["RevisionDate"],
        "TargetFileExternalId": build_target_external_id(payload["DocumentID"]),
    }


@dataclass
class RunSummary:
    processed: int = 0
    failed: list[str] = field(default_factory=list)


def run_extractor(
    cognite: CogniteClient, states: AbstractStateStore, config: Config, stop_event: CancellationToken
) -> None:
    logging.info("Starting extractor")
    process_rows(cognite, config)


def process_rows(cognite: CogniteClient, config: Config) -> RunSummary:
    summary = RunSummary()
    for chunk in cognite.raw.rows(
        db_name=config.source.database,
        table_name=config.source.table,
        chunk_size=RAW_ROW_CHUNK_SIZE,
        limit=None,
    ):
        for row in chunk:
            try:
                process_row(cognite, row, config)
            except Exception:
                logging.exception(f"Failed to process row: {row.key}")
                summary.failed.append(str(row.key))
                continue
            summary.processed += 1
            columns: dict[str, Any] = row.columns or {}
            logging.info(f"Processed row: {row.key} with name: {columns.get('Title')}")
    logging.info(f"Finished processing rows: {summary.processed} processed, {len(summary.failed)} failed")
    return summary
