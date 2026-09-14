
import logging
from threading import Event
from datetime import datetime
import mimetypes

import time
from cognite.client.exceptions import CogniteAPIError
from cognite.client import CogniteClient
from cognite.extractorutils.statestore import AbstractStateStore
from cognite.client.data_classes.data_modeling import NodeId
from cognite.client.data_classes.data_modeling.cdm.v1 import CogniteFile, CogniteFileApply
from cognite.client.data_classes.raw import Row
from cognite.client.data_classes.data_modeling import SpaceApply


from dmsextractor.config import Config

def process_metadata(payload: dict) -> dict:
    # Minimal logic to pass the unit test
    raw_date = payload["RevisionDate"]
    parsed_date = datetime.strptime(raw_date, "%Y-%m-%d")
    
    return {
        "DocumentId": f"dms_{payload['DocumentID'].lower()}",
        "Title": payload["Title"],
        "RevisionDate": parsed_date.strftime("%Y-%m-%d"),
        "TargetFileExternalId": f"Target_{payload['DocumentID']}"
    }

def is_version_conflict(exc: CogniteAPIError) -> bool:
    return exc.code == 400 and "version conflict" in str(exc).lower()


def apply_with_retry(
    cognite: CogniteClient, file_apply: CogniteFileApply, max_attempts: int = 3
) -> None:
    for attempt in range(max_attempts):
        try:
            cognite.data_modeling.instances.apply(file_apply)
            return
        except CogniteAPIError as e:
            if is_version_conflict(e) and attempt < max_attempts - 1:
                time.sleep(0.5 * (2 ** attempt))
                continue
            raise

def process_row(cognite: CogniteClient, row, config: Config) -> None:
    source_document_id = row.columns.get("DocumentID")
    source_file_external_id = f"NewProdom_CLOV_{source_document_id}"
    source_space = "isp_CLOV"
    target_space = config.target_space.space
    target_external_id = f"Target_{source_document_id}"

    source_file_bytes = cognite.files.download_bytes(
        instance_id=NodeId(space=source_space, external_id=source_file_external_id)
    )

    source_node = cognite.data_modeling.instances.retrieve_nodes(
        nodes=NodeId(space=source_space, external_id=source_file_external_id),
        node_cls=CogniteFile,
    )
    if source_node is None:
        logging.warning(f"No source node for {source_file_external_id}, skipping")
        return

    filename = "Target_" + source_node.name
#    filename = source_node.name
    mimetype = source_node.mimeType
    processed_metadata = process_metadata(row.columns)

    cognite.raw.rows.insert(
        db_name=config.target.database,
        table_name=config.target.table,
        row=Row(key=row.key, columns=processed_metadata),
        ensure_parent=True,
    )

    file_apply = CogniteFileApply(
            name=filename,
            space=target_space,
            external_id=target_external_id,
            mime_type=mimetype,
            description=processed_metadata["Title"],
            source_id=row.columns.get("DocumentID"),
            source_context="fromDMS",
    )
    apply_with_retry(cognite, file_apply)

    cognite.files.upload_content_bytes(
        content=source_file_bytes,
        instance_id=NodeId(space=target_space, external_id=target_external_id),
    )

def ensure_target_space(cognite: CogniteClient, config: Config) -> None:
    target = config.target_space
    cognite.data_modeling.spaces.apply(
        SpaceApply(
            space=target.space,
            name=target.name,
            description=target.description,
        )
    )
    logging.info(f"Ensured target space exists: {target.space}")


def run_extractor(cognite: CogniteClient, states: AbstractStateStore, config: Config, stop_event: Event) -> None:
    logging.info("Starting CDF-to-CDF Extraction Handshake...!")
    ensure_target_space(cognite, config)
        # 1. Fetch metadata rows from the source RAW system
    raw_rows = cognite.raw.rows.list(
        db_name=config.source.database, 
        table_name=config.source.table, 
        limit=10
    )

    for row in raw_rows:
        try:
            process_row(cognite, row, config)
        except Exception as e:
            logging.error(f"Failed to process row: {row.key} with error: {e}")
            continue
        logging.info(f"Successfully processed row: {row.key} with name: {row.columns.get('Title')}")

    logging.info("Finished extracting data from source system")