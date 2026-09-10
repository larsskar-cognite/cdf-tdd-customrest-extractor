from cognite.extractorutils import Extractor

from tddextractexercise import __version__
from tddextractexercise.config import Config
from tddextractexercise.extractor import run_extractor


def main() -> None:
    with Extractor(
        name="tddextractexercise",
        description="Exercise to develop extractor through TDD",
        config_class=Config,
        run_handle=run_extractor,
        version=__version__,
    ) as extractor:
        extractor.run()


if __name__ == "__main__":
    main()
