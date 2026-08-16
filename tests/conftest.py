import os

import pykingenie
import pytest

os.environ.setdefault("MCP_PYKINGENIE_SKIP_USER_DATA_INIT", "1")

import mcp_pykingenie.config as config
import mcp_pykingenie.server as server
import mcp_pykingenie.tools._pykingenie as pykingenie_tools


pytest_plugins = ("pytest_asyncio",)


@pytest.fixture(autouse=True)
def reset_kinetics_analyzer(tmp_path):
    """Reset shared server/tool analyzer state before each test."""
    analyzer = pykingenie.KineticsAnalyzer()

    data_dir_path = tmp_path / "user_data"
    data_dir_path.mkdir()
    data_dir = str(data_dir_path)

    # Reset analyzer state.
    server.PY_KINETICS = analyzer
    pykingenie_tools.PY_KINETICS = analyzer

    # Redirect generated files to the temporary test directory.
    server.DATA_DIR = data_dir
    pykingenie_tools.DATA_DIR = data_dir

    yield