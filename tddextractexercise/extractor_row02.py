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

from tddextractexercise.config import Config

def process_metadata(payload: dict) -> dict:
    parsed_date = datetime.strptime(payload["RevisionDate"], "%Y-%m-%d")
    return {
        "DocumentId": f"dms_{payload['DocumentID'].lower()}",
        "Title": payload["Title"],
        "RevisionDate": parsed_date.strftime("%Y-%m-%d"),
        "TargetFileExternalId": f"Target_{payload['DocumentID']}",
    }

from cognite.client.data_classes.data_modeling.cdm.v1 import CogniteFile, CogniteFileApply
"""
Start fixing the process_row function
Work on the test_skips_when_source_node_missing test first and then implement the function
"""
def process_row(cognite: CogniteClient, row, config: Config) -> None:
    source_node = cognite.data_modeling.instances.retrieve_nodes(
        external_id="NewProdom_CLOV_" + row.columns.get("DocumentID"),  
    )   
    if source_node is None:
        logging.info(f"Source node not found for row: {row.key}")
        return

    file_apply=CogniteFileApply(
        external_id="Target_" + row.columns.get("DocumentID"),
#        mime_type="application/pdf",
        mime_type=source_node.mimeType,
        description=row.columns.get("Title"),
        source_id=row.columns.get("DocumentID"),
        source_context="fromDMS",
        space=config.target_space.space,
    )
    cognite.data_modeling.instances.apply(file_apply)

def run_extractor(cognite: CogniteClient, states: AbstractStateStore, config: Config, stop_event: Event) -> None:
    logging.info("Hello, world!")
    source_rows = cognite.raw.rows.list(
        db_name=config.source.database, 
        table_name=config.source.table, 
        limit=10
    )
    for row in source_rows:
        process_row(cognite, row, config)
        logging.info(f"Successfully processed row: {row.key} with name: {row.columns.get('Title')}")
    logging.info("Finished processing rows")

