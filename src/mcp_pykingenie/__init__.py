from importlib.metadata import version

from mcp_pykingenie.main import run_app
from mcp_pykingenie.mcp import mcp

__version__ = version("mcp_pykingenie")

__all__ = [
    "mcp",
    "run_app",
    "__version__"
]


if __name__ == "__main__":
    run_app()
