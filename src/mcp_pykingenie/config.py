import os
from datetime import datetime

from .paths import get_example_data_root, get_user_data_root


SKIP_USER_DATA_INIT = os.environ.get("MCP_PYKINGENIE_SKIP_USER_DATA_INIT") == "1"

# Define the paths to the project data directories.
DATA_DIR_NO_DATE = str(get_user_data_root())
EXAMPLE_DATA_DIR = str(get_example_data_root())

# Create the base data directory if it doesn't exist.
if not SKIP_USER_DATA_INIT:
    os.makedirs(DATA_DIR_NO_DATE, exist_ok=True)

# Create a dated output directory.
today = datetime.today().strftime("%Y-%m-%d")
DATA_DIR = os.path.join(DATA_DIR_NO_DATE, today)

if not SKIP_USER_DATA_INIT:
    os.makedirs(DATA_DIR, exist_ok=True)


def build_server_instructions(data_dir: str) -> str:
    """Return MCP server instructions including the active output folder."""
    return (
        "This server provides tools for analysing surface-based binding kinetics "
        "data only.\n"
        "You can import Octet and Gator experiments, align sensorgrams, subtract "
        "reference sensors, prepare fitting datasets, run either steady-state or "
        "kinetic fits, and plot results.\n"
        f"Plots and generated files for this session are saved in: {data_dir}"
    )


SERVER_INSTRUCTIONS = build_server_instructions(DATA_DIR)