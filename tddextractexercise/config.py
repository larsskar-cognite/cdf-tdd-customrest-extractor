from dataclasses import dataclass, field

from cognite.extractorutils.configtools import BaseConfig, StateStoreConfig


@dataclass
class DataLocation:
    database: str
    table: str


@dataclass
class TargetSpace:
    space: str
    name: str
    description: str


@dataclass
class ExtractorConfig:
    state_store: StateStoreConfig = field(default_factory=StateStoreConfig)


@dataclass
class Config(BaseConfig):
    extractor: ExtractorConfig = field(default_factory=ExtractorConfig)
    source: DataLocation = field(default_factory=DataLocation)
    target: DataLocation = field(default_factory=DataLocation)
    target_space: TargetSpace = field(default_factory=TargetSpace)
