from cognite.extractorutils import Extractor

from customrestextractor import __version__
from customrestextractor.config import Config
from customrestextractor.extractor import run_extractor


def main() -> None:
    with Extractor(
        name="customrestextractor",
        description="Custom REST API extractor",
        config_class=Config,
        run_handle=run_extractor,
        version=__version__,
    ) as extractor:
        extractor.run()


if __name__ == "__main__":
    main()
