import os
from datetime import datetime

import pykingenie

from .mcp import mcp
from .paths import get_example_data_root, get_user_data_root

SKIP_USER_DATA_INIT = os.environ.get("MCP_PYKINGENIE_SKIP_USER_DATA_INIT") == "1"

PY_KINETICS = pykingenie.KineticsAnalyzer()

# Define the paths to the project data directories.
DATA_DIR = str(get_user_data_root())
EXAMPLE_DATA_DIR = str(get_example_data_root())

# Create the data directory if it doesn't exist.
if not SKIP_USER_DATA_INIT and not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

DATA_DIR_NO_DATE = DATA_DIR

# Create a folder with the current date, inside data.
today = datetime.today().strftime('%Y-%m-%d')
DATA_DIR = os.path.join(DATA_DIR, today)

if not SKIP_USER_DATA_INIT and not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)


def build_server_instructions(data_dir: str) -> str:
    """Return MCP server instructions including the active output folder."""
    return f"""This server provides tools for analysing binding kinetics data.
You can import Octet and Gator experiments, align sensorgrams, subtract reference sensors,
prepare fitting datasets, run kinetic fits, and plot results.
Plots and generated files for this session are saved in: {data_dir}"""


SERVER_INSTRUCTIONS = build_server_instructions(DATA_DIR)

mcp.instructions = SERVER_INSTRUCTIONS
