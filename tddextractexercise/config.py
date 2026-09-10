from dataclasses import dataclass, field

from cognite.extractorutils.configtools import BaseConfig, StateStoreConfig


@dataclass
class ExtractorConfig:
    state_store: StateStoreConfig = field(default_factory=StateStoreConfig)


@dataclass
class Config(BaseConfig):
    extractor: ExtractorConfig = field(default_factory=ExtractorConfig)
