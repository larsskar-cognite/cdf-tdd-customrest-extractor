from dataclasses import dataclass, field
from typing import List, Optional

from cognite.extractorutils.configtools import BaseConfig, RawDestinationConfig, StateStoreConfig, LoggingConfig


@dataclass
class SiteConfig:
    cdf_space: str
    site_name: str
    domain: str
    api_url: str
    api_user: str
    api_password: str
    fromTime: str
    toTime: str
    operation_documents_destination: RawDestinationConfig
    rfm_documents_destination: RawDestinationConfig



@dataclass
class FileConfig:
    path: str
    key_column: str
    destination: RawDestinationConfig


@dataclass
class ExtractorConfig:
    state_store: StateStoreConfig = field(default_factory=StateStoreConfig)


@dataclass
class Config(BaseConfig):
    files: List[FileConfig] = field(default_factory=list)
    sites: List[SiteConfig] = field(default_factory=list)
    extractor: ExtractorConfig = field(default_factory=ExtractorConfig)
    logger: Optional[LoggingConfig] = None
