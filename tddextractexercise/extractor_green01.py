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

from datetime import datetime
import logging
from threading import Event

from cognite.client import CogniteClient
from cognite.extractorutils.statestore import AbstractStateStore

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

def run_extractor(cognite: CogniteClient, states: AbstractStateStore, config: Config, stop_event: Event) -> None:
    logging.info("Hello, world!")

