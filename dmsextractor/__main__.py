from cognite.client.config import global_config
from cognite.extractorutils import Extractor  # noqa: E402

from dmsextractor import __version__  # noqa: E402
from dmsextractor.config import Config  # noqa: E402
from dmsextractor.extractor_quiet_lie import run_extractor  # noqa: E402

global_config.silence_feature_preview_warnings = True


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
