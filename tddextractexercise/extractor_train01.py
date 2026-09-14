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
from threading import Event

from cognite.client import CogniteClient
from cognite.extractorutils.statestore import AbstractStateStore
from cognite.client.data_classes.data_modeling.cdm.v1 import CogniteFile, CogniteFileApply
from cognite.client.data_classes.data_modeling import NodeId
from cognite.client.exceptions import CogniteAPIError
import time
from tddextractexercise.config import Config

from datetime import datetime

def process_metadata(payload: dict) -> dict:
    parsed_date = datetime.strptime(payload["RevisionDate"], "%Y-%m-%d")
    return {
        "DocumentId": f"dms_{payload['DocumentID'].lower()}",
        "Title": payload["Title"],
        "RevisionDate": parsed_date.strftime("%Y-%m-%d"),
        "TargetFileExternalId": f"Target_{payload['DocumentID']}",
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
    metadata = process_metadata(row.columns)
    source_node = cognite.data_modeling.instances.retrieve_nodes(
        external_id="NewProdom_CLOV_" + row.columns.get("DocumentID"),  
    )   
    if source_node is None:
        logging.info(f"Source node not found for row: {row.key}")
        return
    download_bytes = cognite.files.download_bytes(source_node.instanceId)
    file_apply=CogniteFileApply(
        external_id=metadata["TargetFileExternalId"],
        name="Target_" + row.columns.get("DocumentID"),
#        mime_type="application/pdf",
        mime_type=source_node.mimeType,
        description=row.columns.get("Title"),
        source_id=row.columns.get("DocumentID"),
        source_context="fromDMS",
        space=config.target_space.space,
    )
    apply_with_retry(cognite, file_apply)
    cognite.files.upload_content_bytes(content=download_bytes,
        instance_id=NodeId(
            space=config.target_space.space,
            external_id=file_apply.external_id,), 
    )

def run_extractor(cognite: CogniteClient, states: AbstractStateStore, config: Config, stop_event: Event) -> None:
    logging.info("Hello, world!")

