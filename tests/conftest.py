import pytest
import pykingenie

import mcp_pykingenie.server as server
import mcp_pykingenie.tools._pykingenie as pykingenie_tools

pytest_plugins = ("pytest_asyncio",)


@pytest.fixture(autouse=True)
def reset_kinetics_analyzer():
    analyzer = pykingenie.KineticsAnalyzer()
    server.PY_KINETICS = analyzer
    pykingenie_tools.PY_KINETICS = analyzer
    yield
