"""
Custom REST Extractor - Core extraction logic.
Extracts document metadata and files from REST API and uploads to CDF.
The REST API is mocked through csv files and document downloaded files that provides the data for the API.
"""
import logging
import mimetypes
from threading import Event
import io

import pandas as pd
import requests
from dateutil import parser
from requests.auth import HTTPBasicAuth

from cognite.client import CogniteClient
from cognite.client.data_classes.data_modeling import NodeId, SpaceApply
from cognite.client.data_classes.data_modeling.cdm.v1 import CogniteFile, CogniteFileApply
from cognite.client.data_classes.raw import Row
from cognite.extractorutils.statestore import AbstractStateStore
from cognite.extractorutils.uploader import RawUploadQueue

from customrestextractor.config import Config, SiteConfig

# Suppress verbose Azure SDK and HTTP client logging
logging.getLogger("azure").setLevel(logging.WARNING)
logging.getLogger("azure.identity").setLevel(logging.WARNING)
logging.getLogger("azure.core.pipeline.policies.http_logging_policy").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("msal").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


def get_filedetails_by_documentID(site: SiteConfig, DocumentID):
    """
    Fetches the complete response JSON for a given DocumentPrimKey from the API.
    Returns the first item as a JSON object if found, else None.
    """
    url = (
        f"{site.api_url}/helicopter-view/document-downloads/"
        f'?filter={{"equals":{{"left":{{"field":"DocumentID"}},"right":"{DocumentID}"}}}}'
        f'&order=[{{"asc":"LastUpdated"}}]'
        f'&take=1'
    )
    response = requests.get(
        url,
        auth=HTTPBasicAuth(site.api_user, site.api_password),
        headers={"Accept": "application/json"},
        verify=True
    )
    response.raise_for_status()
    listItems = response.json()["_items"]
    if listItems:
        return listItems[0]  # Return first item as dict
    return None



def download_document_to_buffer(site: SiteConfig, file_key):
    """
    Download a document by its ID and return the content as a BytesIO buffer.
    """
    logger.info(f"Downloading document to buffer: {file_key}")
    logger.debug(f"URL: {site.api_url + f'/helicopter-view/document-downloads/{file_key}/download/'}")
    url = site.api_url + f"/helicopter-view/document-downloads/{file_key}/download/"
    response = requests.get(
        url,
        auth=HTTPBasicAuth(site.api_user, site.api_password),
        headers={"Accept": "application/octet-stream"},
        verify=True
    )
    response.raise_for_status()
    return io.BytesIO(response.content)



def get_operation_documents_metadata(site: SiteConfig):
    """
    Fetch operation documents for a given domain, site, and LastUpdated interval.
    Returns the response as a pandas DataFrame with only the selected fields.
    """
    selected_fields = [
        "DocumentPrimKey", "DocumentID", "CurrentRevision", "RevisionDate", "ReviewStatus", 
        "LastUpdated", "ReceivedDate", "Title", "Confidential", "Country", "Site", "Class", 
        "PlantNo", "Sector", "Discipline", "System", "SubSystem", "DocumentType", 
        "OriginatorCompany", "Phase", "Step", "ReviewClass",
        # Not currently available, but requested from Omega - uncomment when available:
        # "SM", "RMLU", 
        "ContractorDocumentID", "URL"
    ]
    
    url = (
        f"{site.api_url}/helicopter-view/operation-documents"
        f'?filter={{"and":[{{"equals":{{"left":{{"field":"Domain"}},"right":"{site.domain}"}}}},'
        f'{{"equals":{{"left":{{"field":"Site"}},"right":"{site.site_name}"}}}},'
        f'{{"greaterthanorequal":{{"left":{{"field":"LastUpdated"}},"right":"{site.fromTime}"}}}},'
        f'{{"lessthanorequal":{{"left":{{"field":"LastUpdated"}},"right":"{site.toTime}"}}}}'
        f']}}&count=false&take=-1'
    )
    
    logger.info(f"Requesting API: site={site.site_name}, domain={site.domain}, from={site.fromTime}, to={site.toTime}")
    logger.debug(f"URL: {url[:100]}...")
    
    response = requests.get(
        url,
        auth=HTTPBasicAuth(site.api_user, site.api_password),
        headers={"Accept": "application/json"},
        verify=True
    )
    response.raise_for_status()
    json_data = response.json()
    
    logger.info(f"API response: status={response.status_code}, keys={list(json_data.keys())}")
    listItems = json_data.get("_items", [])
    logger.info(f"Found {len(listItems)} items in response")
    
    df = pd.DataFrame(listItems)
    df_selected = df[selected_fields] if not df.empty else pd.DataFrame(columns=selected_fields)
    return df_selected


# ============ EXTRACTION FUNCTIONS ============

def extract_file_from_document(
    document: dict, 
    site: SiteConfig, 
    cdf_client: CogniteClient, 
    cognite_file_space: str
) -> tuple[bool, int]:
    """
    Extract a single file from a document and upload to CDF.
    
    Args:
        document: Document metadata dict containing DocumentID, Title, etc.
        site: Site configuration
        cdf_client: CDF client instance
        cognite_file_space: Target space for CogniteFile instances
    
    Returns:
        Tuple of (is_valid: bool, file_size: int)
    """
    externalid = f"CustomRest_{site.site_name}_{document['DocumentID']}"
    description = document['Title']
    aliases = [document['DocumentID']]
    
    file_details = get_filedetails_by_documentID(site, document['DocumentID'])
    if file_details is None:
        logger.warning(f"No file details found for DocumentID: {document['DocumentID']}, skipping")
        return False, 0
    
    filename = file_details['FileName']
    file_prim_key = file_details['FilePrimKey']
    source_created_time = parser.parse(file_details['Created']).isoformat(timespec='milliseconds') if file_details['Created'] else None
    source_updated_time = parser.parse(file_details['LastUpdated']).isoformat(timespec='milliseconds') if file_details['LastUpdated'] else None
    source_id = document['DocumentID']
    source_context = f"Operation_{site.site_name}"
    
    mimetype, _ = mimetypes.guess_type(filename)
    buffer = download_document_to_buffer(site, file_prim_key)
    buffer.seek(0, 2)
    size = buffer.tell()
    buffer.seek(0)  # Rewind before reading
    
    if size > 0:  # We have a valid file
        # Create CogniteFile instance
        cdf_client.data_modeling.instances.apply(
            CogniteFileApply(name=filename, space=cognite_file_space, external_id=externalid)
        )
        
        # Upload file content
        cdf_client.files.upload_content_bytes(
            content=buffer.getvalue(), 
            instance_id=NodeId(space=cognite_file_space, external_id=externalid)
        )
        
        # Retrieve the CogniteFile node, update its fields, and apply changes
        file_metadata = cdf_client.data_modeling.instances.retrieve_nodes(
            nodes=NodeId(space=cognite_file_space, external_id=externalid), 
            node_cls=CogniteFile
        )
        file_metadata.sourceCreatedTime = source_created_time
        file_metadata.sourceUpdatedTime = source_updated_time
        file_metadata.mimeType = mimetype
        file_metadata.description = description
        file_metadata.aliases = aliases
        file_metadata.sourceId = source_id
        file_metadata.sourceContext = source_context
        # Note: 'source' is a direct relation field, not a text field
        cdf_client.data_modeling.instances.apply(file_metadata)
        
        return True, size
    else:
        logger.info(f"Invalid file (zero size): {file_prim_key}, {filename}")
        return False, 0



def extract_operation_documents_from_site(site: SiteConfig, cdf_client: CogniteClient, queue: RawUploadQueue) -> None:
    """Extract document metadata from a site and add to RAW upload queue."""
    logger.info(f"Extracting operation documents from {site.site_name} to {site.operation_documents_destination.database}/{site.operation_documents_destination.table}")
    logger.info(f"Extracting files from {site.site_name} to CDF CogniteFile space {site.cdf_space}")

    df = get_operation_documents_metadata(site)
    operation_documents = df.to_dict(orient="records")
    row_count = 0
    valid_files = 0
    invalid_files = 0
    total_size = 0

    for doc in operation_documents:
        queue.add_to_upload_queue(
            database=site.operation_documents_destination.database,
            table=site.operation_documents_destination.table,
            raw_row=Row(key=doc["DocumentPrimKey"], columns=doc)
        )
        is_valid, size = extract_file_from_document(doc, site, cdf_client, site.cdf_space)
        if is_valid:
            valid_files += 1
            total_size += size
        else:
            invalid_files += 1

        row_count += 1

    logger.info(f"Added {row_count} rows from {site.site_name} to upload queue")
    logger.info(f"Number of valid files: {valid_files}, Invalid files: {invalid_files}")
    logger.info(f"Total size: {total_size} bytes")


def get_rfm_documents_metadata(site: SiteConfig):
    """Get RFM documents metadata from a site."""
    logger.info(f"Getting RFM documents metadata from {site.site_name}")

    selected_fields = [
        "Site",
        "Sector",
        "RequestNo",
        "Revision",
        "Title",
        "Created",
        "DateSubmitted",
        "Updated",
        "Status",
        "Step",
        "PJCLeader",
        "FOLeader",
        "MainSystemImpacted",
        "PriorityLevelConfirmedDescription",
        "ClassConfirmedDescription",
        "Start-Up Date Constraint",
        "ImplementationType",
        "IsBasicEngineeringRequired",
        "NecessaryShutdown",
        "DateOfStartUp",
        "DateClosed"
    ]


    url = (
        f"{site.api_url}/helicopter-view/rfm/request-for-modifications"
        f'?filter={{"and":[{{"equals":{{"left":{{"field":"Domain"}},"right":"{site.domain}"}}}},'
        f'{{"equals":{{"left":{{"field":"Site"}},"right":"{site.site_name}"}}}},'
        f'{{"greaterthanorequal":{{"left":{{"field":"Created"}},"right":"{site.fromTime}"}}}},'
        f'{{"lessthanorequal":{{"left":{{"field":"Created"}},"right":"{site.toTime}"}}}}'
        f']}}&count=false&take=-1'
    )
    response = requests.get(
        url,
        auth=HTTPBasicAuth(site.api_user, site.api_password),   
        headers={"Accept": "application/json"},
        verify=True
    )
    response.raise_for_status()
    json_data = response.json()
    listItems = json_data["_items"]
    df = pd.DataFrame(listItems)
    df_selected = df[selected_fields] if not df.empty else pd.DataFrame(columns=selected_fields)
    return df_selected  



def extract_rfm_documents_from_site(site: SiteConfig, queue: RawUploadQueue) -> None:
    """Extract RFM documents from a site and add to RAW upload queue."""
    logger.info(f"Extracting RFM documents from {site.site_name} to {site.rfm_documents_destination.database}/{site.rfm_documents_destination.table}")

    df = get_rfm_documents_metadata(site)
    rfm_documents = df.to_dict(orient="records")
    row_count = 0
    for doc in rfm_documents:
        queue.add_to_upload_queue(
            database=site.rfm_documents_destination.database,
            table=site.rfm_documents_destination.table,
            raw_row=Row(key=doc["RequestNo"], columns=doc)
        )
        row_count += 1
    logger.info(f"Added {row_count} rows from {site.site_name} to upload queue")



def run_extractor(cognite: CogniteClient, states: AbstractStateStore, config: Config, stop_event: Event) -> None:
    """Main extractor entry point - extracts metadata and files from all configured sites."""
    with RawUploadQueue(cdf_client=cognite, max_queue_size=100_000) as queue:
        for site in config.sites:
            if stop_event.is_set():
                break
            space = SpaceApply(space=site.cdf_space, name=site.cdf_space, description=f"Space for {site.site_name} files")
            cognite.data_modeling.spaces.apply(space)
            extract_operation_documents_from_site(site, cdf_client=cognite, queue=queue)
            extract_rfm_documents_from_site(site, queue=queue)
        
        logger.info("Flushing upload queue...")
    # Queue flushes automatically when exiting the 'with' block
    logger.info("Upload complete!")
