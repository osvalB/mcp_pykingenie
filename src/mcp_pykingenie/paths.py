import os
from importlib import resources
from pathlib import Path


PACKAGE_NAME = "mcp_pykingenie"
USER_DATA_DIR_NAME = "user_data_mcp_pykingenie"
RESULTS_DIR_ENV_VAR = "RESULTS_DIR"


def get_user_data_root() -> Path:
    """Return the root folder for user-visible MCP output files."""
    results_dir = os.environ.get(RESULTS_DIR_ENV_VAR)
    if results_dir:
        return Path(results_dir).expanduser().resolve()
    return Path.home() / USER_DATA_DIR_NAME


def get_example_data_root() -> Path:
    """Return the packaged example-data folder."""
    return Path(str(resources.files(PACKAGE_NAME).joinpath("example_data")))
