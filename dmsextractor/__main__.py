from cognite.client.config import global_config
global_config.silence_feature_preview_warnings = True

from cognite.extractorutils import Extractor

from dmsextractor import __version__
from dmsextractor.config import Config
from dmsextractor.extractor import run_extractor


def main() -> None:
    with Extractor(
        name="dmsextractor",
        description="A training extractor on document extraction and TDD",
        config_class=Config,
        run_handle=run_extractor,
        version=__version__,
    ) as extractor:
        extractor.run()


if __name__ == "__main__":
    main()
