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
from dataclasses import dataclass, field
from typing import Any

from cognite.client import CogniteClient
from cognite.client.data_classes import Row
from cognite.client.data_classes.data_modeling import NodeId
from cognite.client.data_classes.data_modeling.cdm.v1 import CogniteFile
from cognite.extractorutils.statestore import AbstractStateStore
from cognite.extractorutils.threading import CancellationToken

from tddextractexercise.config import Config


def build_source_external_id(document_id: str) -> str:
    return f"NewProdom_CLOV_{document_id}"


def build_target_external_id(document_id: str) -> str:
    return f"Target_{document_id}"


def build_target_filename(source_name: str) -> str:
    return f"Target_{source_name}"


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
    logging.info("Hello, world!")


def process_rows(cognite: CogniteClient, config: Config) -> RunSummary:
    raise NotImplementedError("Implement process_rows — see tests/unit/test_extractor.py")
