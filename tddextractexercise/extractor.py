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
    raise NotImplementedError("Implement process_row — see tests/unit/test_extractor.py")


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
