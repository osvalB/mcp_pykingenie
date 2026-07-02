import os

import pytest
import pykingenie

os.environ.setdefault("MCP_PYKINGENIE_SKIP_USER_DATA_INIT", "1")

import mcp_pykingenie.server as server
import mcp_pykingenie.tools._pykingenie as pykingenie_tools

pytest_plugins = ("pytest_asyncio",)


@pytest.fixture(autouse=True)
def reset_kinetics_analyzer(tmp_path):
    analyzer = pykingenie.KineticsAnalyzer()
    data_dir_path = tmp_path / "user_data"
    data_dir_path.mkdir()
    data_dir = str(data_dir_path)
    server.PY_KINETICS = analyzer
    server.DATA_DIR = data_dir
    server.SERVER_INSTRUCTIONS = server.build_server_instructions(data_dir)
    server.mcp.instructions = server.SERVER_INSTRUCTIONS
    pykingenie_tools.PY_KINETICS = analyzer
    pykingenie_tools.DATA_DIR = data_dir
    yield
